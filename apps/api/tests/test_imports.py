from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from treasurfy.models import BalanceSnapshot, BankTransaction, ImportRun
from treasurfy.seed import DEMO_USER_ID, DEMO_WORKSPACE_ID, VIEWER_USER_ID

CSV_HEADER = (
    "record_type,account_id,occurred_at,amount,currency,"
    "transaction_id,description\n"
)


def _headers(user_id: str = DEMO_USER_ID) -> dict[str, str]:
    return {"X-User-ID": user_id}


def _upload(
    client: TestClient,
    csv_text: str,
    *,
    file_name: str = "bank-data.csv",
    user_id: str = DEMO_USER_ID,
):
    return client.post(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/imports/bank-csv",
        headers=_headers(user_id),
        files={"file": (file_name, csv_text.encode("utf-8"), "text/csv")},
    )


def _future_timestamp() -> str:
    return (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0).isoformat()


def test_import_accepts_balances_and_transactions(client: TestClient) -> None:
    csv_text = CSV_HEADER + "\n".join(
        [
            f"BALANCE,account-hsbc-gbp,{_future_timestamp()},900000.00,GBP,,",
            "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
            "-12500.00,GBP,TX-001,Supplier payment",
        ]
    )

    response = _upload(client, csv_text)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["total_rows"] == 2
    assert payload["accepted_rows"] == 2
    assert payload["rejected_rows"] == 0
    assert payload["skipped_duplicate_rows"] == 0
    assert payload["duplicate_file"] is False

    cash_response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/cash-position",
        headers=_headers(),
    )
    assert cash_response.json()["total_cash"] == "2241800.00"

    database = client.app.state.database
    with database.session_factory() as session:
        assert session.scalar(select(func.count(BalanceSnapshot.id))) == 1
        assert session.scalar(select(func.count(BankTransaction.id))) == 1


def test_partial_import_keeps_valid_rows_and_reports_invalid_rows(
    client: TestClient,
) -> None:
    csv_text = CSV_HEADER + "\n".join(
        [
            "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
            "-10.00,GBP,TX-GOOD,Valid row",
            "TRANSACTION,account-missing,2026-10-04T08:20:00Z,"
            "-20.00,GBP,TX-BAD,Unknown account",
            "BALANCE,account-hsbc-gbp,2026-10-04T08:20:00Z,"
            "900000.00,USD,,Wrong currency",
        ]
    )

    response = _upload(client, csv_text)

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "partial"
    assert payload["accepted_rows"] == 1
    assert payload["rejected_rows"] == 2
    assert [issue["code"] for issue in payload["issues"]] == [
        "unknown_account",
        "currency_mismatch",
    ]


def test_uploading_the_same_file_is_idempotent(client: TestClient) -> None:
    csv_text = (
        CSV_HEADER
        + "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
        "-10.00,GBP,TX-IDEMPOTENT,Only once\n"
    )

    first = _upload(client, csv_text)
    second = _upload(client, csv_text)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate_file"] is True
    assert second.json()["import_run_id"] == first.json()["import_run_id"]

    database = client.app.state.database
    with database.session_factory() as session:
        assert session.scalar(select(func.count(ImportRun.id))) == 1
        assert session.scalar(select(func.count(BankTransaction.id))) == 1


def test_transaction_id_is_not_duplicated_across_different_files(
    client: TestClient,
) -> None:
    first_csv = (
        CSV_HEADER
        + "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
        "-10.00,GBP,TX-SAME,First file\n"
    )
    second_csv = (
        CSV_HEADER
        + "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
        "-10.00,GBP,TX-SAME,Second file\n"
    )

    assert _upload(client, first_csv, file_name="first.csv").status_code == 200
    second = _upload(client, second_csv, file_name="second.csv")

    assert second.status_code == 200
    assert second.json()["accepted_rows"] == 0
    assert second.json()["skipped_duplicate_rows"] == 1


def test_viewer_cannot_import_but_can_read_history(client: TestClient) -> None:
    csv_text = (
        CSV_HEADER
        + "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
        "-10.00,GBP,TX-VIEWER,Blocked\n"
    )

    upload_response = _upload(client, csv_text, user_id=VIEWER_USER_ID)
    history_response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/imports",
        headers=_headers(VIEWER_USER_ID),
    )

    assert upload_response.status_code == 403
    assert history_response.status_code == 200
    assert history_response.json() == []


def test_import_history_returns_completed_runs(client: TestClient) -> None:
    csv_text = (
        CSV_HEADER
        + "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
        "-10.00,GBP,TX-HISTORY,History row\n"
    )
    imported = _upload(client, csv_text)

    response = client.get(
        f"/api/workspaces/{DEMO_WORKSPACE_ID}/imports",
        headers=_headers(),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["import_run_id"] == imported.json()["import_run_id"]


def test_missing_columns_are_rejected_before_an_import_run_is_created(
    client: TestClient,
) -> None:
    response = _upload(client, "account_id,amount\naccount-hsbc-gbp,10.00\n")

    assert response.status_code == 400
    assert "Missing required CSV columns" in response.json()["detail"]

    database = client.app.state.database
    with database.session_factory() as session:
        assert session.scalar(select(func.count(ImportRun.id))) == 0


def test_extra_row_values_are_reported_instead_of_crashing(
    client: TestClient,
) -> None:
    csv_text = (
        CSV_HEADER
        + "TRANSACTION,account-hsbc-gbp,2026-10-04T08:20:00Z,"
        "-10.00,GBP,TX-EXTRA,Description,unexpected\n"
    )

    response = _upload(client, csv_text)

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["issues"][0]["code"] == "unexpected_columns"
