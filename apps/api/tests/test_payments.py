from __future__ import annotations

from datetime import date, timedelta
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from treasurfy.seed import (
    APPROVER_USER_ID,
    DEMO_USER_ID,
    OUTSIDER_USER_ID,
    PREPARER_USER_ID,
    VIEWER_USER_ID,
)


WORKSPACE_ID = "workspace-demo"
PROFILE_ID = "payment-profile-pain001-demo"


def headers(user_id: str) -> dict[str, str]:
    return {"X-User-ID": user_id}


def valid_payment() -> dict[str, object]:
    return {
        "entity_id": "entity-eu",
        "source_account_id": "account-deutsche-eur",
        "payment_profile_id": PROFILE_ID,
        "beneficiary_name": "Example Supplier GmbH",
        "beneficiary_account": "DE75512108001245126199",
        "beneficiary_country_code": "DE",
        "amount": "12500.00",
        "currency": "EUR",
        "requested_execution_date": (date.today() + timedelta(days=3)).isoformat(),
        "reference": "INV-TEST-100",
    }


def test_lists_versioned_profile_and_seeded_payment(client: TestClient) -> None:
    profiles = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payment-profiles",
        headers=headers(VIEWER_USER_ID),
    )
    payments = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payments",
        headers=headers(VIEWER_USER_ID),
    )

    assert profiles.status_code == 200
    assert profiles.json() == [
        {
            "id": PROFILE_ID,
            "name": "Illustrative ISO 20022 credit transfer",
            "version": "1.0.0",
            "message_type": "pain.001.001.03-demo",
            "allowed_currencies": ["GBP", "USD", "EUR"],
            "maximum_amount": "1000000.00",
        }
    ]
    assert payments.status_code == 200
    assert payments.json()[0]["status"] == "pending_approval"
    assert payments.json()[0]["validation_status"] == "passed"


def test_full_maker_checker_and_export_workflow(client: TestClient) -> None:
    prepared = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments",
        headers=headers(PREPARER_USER_ID),
        json=valid_payment(),
    )
    assert prepared.status_code == 201
    assert prepared.json()["status"] == "draft"
    assert prepared.json()["validation_errors"] == []
    payment_id = prepared.json()["id"]

    submitted = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/submit",
        headers=headers(PREPARER_USER_ID),
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_approval"

    approved = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/approve",
        headers=headers(APPROVER_USER_ID),
        json={"comment": "Invoice and beneficiary verified."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["can_export"] is True

    exported = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/iso20022",
        headers=headers(PREPARER_USER_ID),
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/xml")
    assert len(exported.headers["x-content-sha256"]) == 64
    root = ET.fromstring(exported.content)
    namespace = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}
    assert root.find(".//p:InstdAmt", namespace).text == "12500.00"
    assert root.find(".//p:InstdAmt", namespace).attrib["Ccy"] == "EUR"
    assert root.find(".//p:Ustrd", namespace).text == "INV-TEST-100"

    repeated = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/iso20022",
        headers=headers(APPROVER_USER_ID),
    )
    assert repeated.content == exported.content
    assert repeated.headers["x-content-sha256"] == exported.headers["x-content-sha256"]

    audit = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/audit-events",
        headers=headers(VIEWER_USER_ID),
    )
    assert audit.status_code == 200
    assert [event["action"] for event in audit.json()] == [
        "payment.created",
        "payment.submitted",
        "payment.approved",
        "payment.exported",
    ]


def test_profile_validation_blocks_submission(client: TestClient) -> None:
    payload = valid_payment()
    payload["currency"] = "GBP"

    prepared = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments",
        headers=headers(PREPARER_USER_ID),
        json=payload,
    )
    assert prepared.status_code == 201
    assert prepared.json()["validation_status"] == "failed"
    assert prepared.json()["validation_errors"] == [
        "Payment currency must match the source account currency."
    ]

    submitted = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{prepared.json()['id']}/submit",
        headers=headers(PREPARER_USER_ID),
    )
    assert submitted.status_code == 409
    assert "Payment validation failed" in submitted.json()["detail"]


def test_maker_cannot_approve_own_payment(client: TestClient) -> None:
    prepared = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments",
        headers=headers(DEMO_USER_ID),
        json=valid_payment(),
    )
    payment_id = prepared.json()["id"]
    client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/submit",
        headers=headers(DEMO_USER_ID),
    )

    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/{payment_id}/approve",
        headers=headers(DEMO_USER_ID),
        json={"comment": "Self approval attempt"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Maker/checker requires a different approver."


def test_approver_can_reject_pending_payment(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/payment-demo-cloud/reject",
        headers=headers(APPROVER_USER_ID),
        json={"comment": "Supporting invoice is missing."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["can_export"] is False

    resubmitted = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/payment-demo-cloud/submit",
        headers=headers(PREPARER_USER_ID),
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == "pending_approval"
    assert resubmitted.json()["decided_by_user_id"] is None
    assert resubmitted.json()["decided_at"] is None


def test_payment_role_and_workspace_boundaries(client: TestClient) -> None:
    viewer_create = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments",
        headers=headers(VIEWER_USER_ID),
        json=valid_payment(),
    )
    outsider_list = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payments",
        headers=headers(OUTSIDER_USER_ID),
    )
    maker_approve = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/payment-demo-cloud/approve",
        headers=headers(PREPARER_USER_ID),
        json={"comment": "Not permitted"},
    )

    assert viewer_create.status_code == 403
    assert outsider_list.status_code == 403
    assert maker_approve.status_code == 403


def test_unapproved_payment_cannot_be_exported(client: TestClient) -> None:
    response = client.get(
        f"/api/workspaces/{WORKSPACE_ID}/payments/payment-demo-cloud/iso20022",
        headers=headers(APPROVER_USER_ID),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Only approved payments can be exported."
