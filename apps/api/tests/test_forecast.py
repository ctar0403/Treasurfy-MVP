from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from treasurfy.models import ForecastRun
from treasurfy.seed import DEMO_USER_ID, DEMO_WORKSPACE_ID, VIEWER_USER_ID


def _headers(user_id: str = DEMO_USER_ID) -> dict[str, str]:
    return {"X-User-ID": user_id}


def _run_forecast(client: TestClient, user_id: str = DEMO_USER_ID):
    return client.post(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/forecasts",
        headers=_headers(user_id),
        json={"horizon_days": 90},
    )


def test_forecast_calculates_reproducible_horizons(client: TestClient) -> None:
    response = _run_forecast(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["opening_cash"] == "2191800.00"
    assert [item["total_cash"] for item in payload["horizons"]] == [
        "2118200.00",
        "2153000.00",
        "2013000.00",
    ]
    assert [item["change_from_opening"] for item in payload["horizons"]] == [
        "-73600.00",
        "-38800.00",
        "-178800.00",
    ]
    assert len(payload["points"]) == 91
    assert len(payload["expected_flows"]) == 7


def test_forecast_identifies_entity_liquidity_breach(client: TestClient) -> None:
    payload = _run_forecast(client).json()

    assert len(payload["alerts"]) == 1
    alert = payload["alerts"][0]
    assert alert["entity_name"] == "Northstar Europe GmbH"
    assert alert["code"] == "ENTITY_BELOW_MINIMUM"
    assert alert["projected_balance"] == "115200.00"
    assert alert["minimum_balance"] == "150000.00"

    europe = next(
        item for item in payload["entities"] if item["entity_id"] == "entity-eu"
    )
    assert europe["status"] == "at_risk"
    assert europe["rank_at_30_days"] == 3


def test_unchanged_inputs_reuse_the_same_immutable_run(client: TestClient) -> None:
    first = _run_forecast(client).json()
    second = _run_forecast(client).json()

    assert first["reused_run"] is False
    assert second["reused_run"] is True
    assert second["forecast_run_id"] == first["forecast_run_id"]
    assert second["input_fingerprint"] == first["input_fingerprint"]

    database = client.app.state.database
    with database.session_factory() as session:
        assert session.scalar(select(func.count(ForecastRun.id))) == 1


def test_new_expected_flow_changes_the_next_forecast(client: TestClient) -> None:
    first = _run_forecast(client).json()
    due_date = (datetime.now(UTC).date() + timedelta(days=10)).isoformat()
    create_response = client.post(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/expected-cash-flows",
        headers=_headers(),
        json={
            "entity_id": "entity-uk",
            "account_id": "account-hsbc-gbp",
            "name": "New signed contract",
            "direction": "inflow",
            "amount": "50000.00",
            "currency": "GBP",
            "due_date": due_date,
        },
    )
    second = _run_forecast(client).json()

    assert create_response.status_code == 201
    assert create_response.json()["base_currency_amount"] == "50000.00"
    assert second["forecast_run_id"] != first["forecast_run_id"]
    assert second["horizons"][0]["total_cash"] == "2168200.00"


def test_viewer_can_run_forecast_but_cannot_create_cash_flow(
    client: TestClient,
) -> None:
    forecast_response = _run_forecast(client, VIEWER_USER_ID)
    create_response = client.post(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/expected-cash-flows",
        headers=_headers(VIEWER_USER_ID),
        json={
            "entity_id": "entity-uk",
            "account_id": "account-hsbc-gbp",
            "name": "Unauthorized flow",
            "direction": "outflow",
            "amount": "1.00",
            "currency": "GBP",
            "due_date": (datetime.now(UTC).date() + timedelta(days=1)).isoformat(),
        },
    )

    assert forecast_response.status_code == 200
    assert create_response.status_code == 403


def test_expected_cash_flow_totals_are_decimal_strings(client: TestClient) -> None:
    response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/expected-cash-flows",
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 7
    assert all(Decimal(item["amount"]) > 0 for item in payload)
    assert any(Decimal(item["base_currency_amount"]) < 0 for item in payload)


def test_planned_cash_flow_cannot_be_created_in_the_past(client: TestClient) -> None:
    response = client.post(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/expected-cash-flows",
        headers=_headers(),
        json={
            "entity_id": "entity-uk",
            "account_id": "account-hsbc-gbp",
            "name": "Outdated assumption",
            "direction": "outflow",
            "amount": "100.00",
            "currency": "GBP",
            "due_date": (datetime.now(UTC).date() - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 400
    assert "cannot be in the past" in response.json()["detail"]
