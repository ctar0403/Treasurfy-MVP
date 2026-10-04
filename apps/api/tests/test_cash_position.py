from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from treasurfy.seed import (
    DEMO_USER_ID,
    DEMO_WORKSPACE_ID,
    OUTSIDER_USER_ID,
    SECONDARY_WORKSPACE_ID,
)


def _headers(user_id: str = DEMO_USER_ID) -> dict[str, str]:
    return {"X-User-ID": user_id}


def test_health_checks_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_cash_position_consolidates_accounts_and_currencies(
    client: TestClient,
) -> None:
    response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/cash-position",
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_name"] == "Northstar Software Group"
    assert payload["base_currency"] == "GBP"
    assert payload["total_cash"] == "2191800.00"
    assert payload["account_count"] == 6
    assert payload["entity_count"] == 3
    assert payload["stale_account_count"] == 1
    assert {account["currency"] for account in payload["accounts"]} == {
        "GBP",
        "USD",
        "EUR",
    }


def test_entity_totals_reconcile_to_workspace_total(client: TestClient) -> None:
    response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/cash-position",
        headers=_headers(),
    )

    payload = response.json()
    entity_total = sum(
        Decimal(entity["base_currency_balance"]) for entity in payload["entities"]
    )
    assert entity_total == Decimal(payload["total_cash"])
    assert {
        entity["entity_name"]: entity["base_currency_balance"]
        for entity in payload["entities"]
    } == {
        "Northstar Europe GmbH": "338800.00",
        "Northstar UK Ltd": "1211200.00",
        "Northstar US Inc": "641800.00",
    }


def test_missing_identity_is_unauthorized(client: TestClient) -> None:
    response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/cash-position"
    )

    assert response.status_code == 401


def test_user_cannot_read_another_workspace(client: TestClient) -> None:
    response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/cash-position",
        headers=_headers(OUTSIDER_USER_ID),
    )

    assert response.status_code == 403


def test_demo_user_cannot_read_secondary_workspace(client: TestClient) -> None:
    response = client.get(
        f"/api/workspaces/{SECONDARY_WORKSPACE_ID}/cash-position",
        headers=_headers(),
    )

    assert response.status_code == 403


def test_unknown_workspace_returns_not_found(client: TestClient) -> None:
    response = client.get(
        "/api/workspaces/workspace-missing/cash-position",
        headers=_headers(),
    )

    assert response.status_code == 404
