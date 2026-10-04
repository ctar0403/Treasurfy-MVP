from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from treasurfy.seed import (
    APPROVER_USER_ID,
    DEMO_USER_ID,
    OUTSIDER_USER_ID,
    VIEWER_USER_ID,
)


WORKSPACE_ID = "workspace-demo"


def headers(user_id: str) -> dict[str, str]:
    return {"X-User-ID": user_id}


def generate(client: TestClient, user_id: str = DEMO_USER_ID):
    return client.post(
        f"/api/workspaces/{WORKSPACE_ID}/daily-briefs",
        headers=headers(user_id),
        json={"as_of_date": date.today().isoformat()},
    )


def test_generates_grounded_daily_brief(client: TestClient) -> None:
    response = generate(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["reused_run"] is False
    assert payload["base_currency"] == "GBP"
    assert payload["headline"] == (
        "1 liquidity risk and 1 payment approval need attention"
    )
    assert payload["metrics"] == [
        {
            "key": "total_cash",
            "label": "Cash available",
            "value": "2191800.00",
            "currency": "GBP",
            "context": "Across 3 entities and 6 accounts",
            "tone": "neutral",
        },
        {
            "key": "cash_30_days",
            "label": "30-day forecast",
            "value": "2118200.00",
            "currency": "GBP",
            "context": "Down 73600.00 from today's position",
            "tone": "warning",
        },
        {
            "key": "cash_90_days",
            "label": "90-day forecast",
            "value": "2013000.00",
            "currency": "GBP",
            "context": "Down 178800.00 from today's position",
            "tone": "warning",
        },
        {
            "key": "pending_approvals",
            "label": "Pending approvals",
            "value": "1",
            "currency": None,
            "context": "Payments requiring a separate checker",
            "tone": "warning",
        },
    ]
    assert [item["severity"] for item in payload["highlights"]] == [
        "critical",
        "warning",
        "warning",
    ]
    assert [item["priority"] for item in payload["actions"]] == [
        "critical",
        "high",
        "medium",
    ]
    assert any(item.startswith("forecast:") for item in payload["evidence"])
    assert "current balances, explicit FX rates" in payload["summary"]


def test_unchanged_inputs_reuse_immutable_brief(client: TestClient) -> None:
    first = generate(client).json()
    second = generate(client).json()

    assert second["reused_run"] is True
    assert second["daily_brief_run_id"] == first["daily_brief_run_id"]
    assert second["input_fingerprint"] == first["input_fingerprint"]
    assert second["generated_at"] == first["generated_at"]


def test_payment_decision_invalidates_brief(client: TestClient) -> None:
    first = generate(client).json()
    approval = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/payments/payment-demo-cloud/approve",
        headers=headers(APPROVER_USER_ID),
        json={"comment": "Verified for daily brief test."},
    )
    assert approval.status_code == 200

    second = generate(client).json()
    assert second["reused_run"] is False
    assert second["daily_brief_run_id"] != first["daily_brief_run_id"]
    pending_metric = next(
        item for item in second["metrics"] if item["key"] == "pending_approvals"
    )
    assert pending_metric["value"] == "0"
    assert any(
        item["title"].startswith("Export approved payment")
        for item in second["actions"]
    )


def test_viewer_can_read_brief_but_outsider_cannot(client: TestClient) -> None:
    viewer = generate(client, VIEWER_USER_ID)
    outsider = generate(client, OUTSIDER_USER_ID)

    assert viewer.status_code == 200
    assert outsider.status_code == 403


def test_daily_brief_requires_identity(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/daily-briefs",
        json={},
    )
    assert response.status_code == 401
