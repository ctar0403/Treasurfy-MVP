from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from treasurfy.models import (
    AuditEvent,
    BalanceSnapshot,
    BankAccount,
    BankTransaction,
    ImportIssue,
    ImportRun,
    MembershipRole,
)
from treasurfy.schemas import ImportIssueResponse, ImportRunResponse
from treasurfy.services.access import require_workspace_access

PROFILE_ID = "treasurfy-bank-csv"
PROFILE_VERSION = "1.0.0"
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 10_000
REQUIRED_COLUMNS = {
    "record_type",
    "account_id",
    "occurred_at",
    "amount",
    "currency",
    "transaction_id",
    "description",
}
IMPORT_ROLES = {MembershipRole.ADMIN, MembershipRole.PREPARER}


class ImportFileError(Exception):
    pass


class RowValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _parse_timestamp(raw_value: str) -> datetime:
    value = raw_value.strip()
    if not value:
        raise RowValidationError("missing_timestamp", "occurred_at is required.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RowValidationError(
            "invalid_timestamp", "occurred_at must be an ISO 8601 timestamp."
        ) from error
    if parsed.tzinfo is None:
        raise RowValidationError(
            "timestamp_timezone_required",
            "occurred_at must include a timezone or Z suffix.",
        )
    return parsed.astimezone(UTC)


def _parse_amount(raw_value: str) -> Decimal:
    try:
        amount = Decimal(raw_value.strip())
    except (InvalidOperation, AttributeError) as error:
        raise RowValidationError("invalid_amount", "amount must be a decimal.") from error
    if not amount.is_finite():
        raise RowValidationError("invalid_amount", "amount must be finite.")
    if amount.as_tuple().exponent < -2:
        raise RowValidationError(
            "invalid_amount_precision", "amount may have at most two decimal places."
        )
    if len(amount.as_tuple().digits) > 18:
        raise RowValidationError("amount_too_large", "amount is too large.")
    return amount.quantize(Decimal("0.01"))


def _response(
    session: Session,
    import_run: ImportRun,
    *,
    duplicate_file: bool,
) -> ImportRunResponse:
    issues = session.scalars(
        select(ImportIssue)
        .where(ImportIssue.import_run_id == import_run.id)
        .order_by(ImportIssue.row_number, ImportIssue.id)
    ).all()
    return ImportRunResponse(
        import_run_id=import_run.id,
        profile_id=import_run.profile_id,
        profile_version=import_run.profile_version,
        file_name=import_run.file_name,
        file_sha256=import_run.file_sha256,
        status=import_run.status,
        total_rows=import_run.total_rows,
        accepted_rows=import_run.accepted_rows,
        rejected_rows=import_run.rejected_rows,
        skipped_duplicate_rows=import_run.skipped_duplicate_rows,
        duplicate_file=duplicate_file,
        created_at=_iso_utc(import_run.created_at) or "",
        completed_at=_iso_utc(import_run.completed_at),
        issues=[
            ImportIssueResponse(
                row_number=issue.row_number,
                code=issue.code,
                message=issue.message,
            )
            for issue in issues
        ],
    )


def import_bank_csv(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    file_name: str,
    content: bytes,
) -> ImportRunResponse:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=IMPORT_ROLES,
    )
    if not content:
        raise ImportFileError("The CSV file is empty.")
    if len(content) > MAX_FILE_BYTES:
        raise ImportFileError("The CSV file exceeds the 2 MB MVP limit.")

    digest = hashlib.sha256(content).hexdigest()
    existing_run = session.scalar(
        select(ImportRun).where(
            ImportRun.workspace_id == workspace_id,
            ImportRun.profile_id == PROFILE_ID,
            ImportRun.file_sha256 == digest,
        )
    )
    if existing_run is not None:
        return _response(session, existing_run, duplicate_file=True)

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ImportFileError("The CSV file must use UTF-8 encoding.") from error

    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    raw_fieldnames = reader.fieldnames or []
    fieldnames = set(raw_fieldnames)
    if len(raw_fieldnames) != len(fieldnames):
        raise ImportFileError("The CSV header contains duplicate column names.")
    missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
    if missing_columns:
        raise ImportFileError(
            "Missing required CSV columns: " + ", ".join(missing_columns) + "."
        )

    accounts = {
        account.id: account
        for account in session.scalars(
            select(BankAccount).where(BankAccount.workspace_id == workspace_id)
        )
    }
    transaction_keys = set(
        session.execute(
            select(BankTransaction.account_id, BankTransaction.external_id).where(
                BankTransaction.workspace_id == workspace_id
            )
        ).all()
    )
    balance_keys: set[tuple[str, datetime, Decimal]] = set()
    now = datetime.now(UTC).replace(microsecond=0)
    import_run = ImportRun(
        id=str(uuid4()),
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        file_name=(file_name or "bank-data.csv")[:255],
        file_sha256=digest,
        status="processing",
        created_at=now,
    )
    session.add(import_run)
    session.flush()

    for row_number, row in enumerate(reader, start=2):
        scalar_values = [value for value in row.values() if isinstance(value, str)]
        if not any(value.strip() for value in scalar_values):
            continue
        import_run.total_rows += 1
        if import_run.total_rows > MAX_ROWS:
            session.rollback()
            raise ImportFileError("The CSV file exceeds the 10,000 row MVP limit.")

        try:
            if None in row:
                raise RowValidationError(
                    "unexpected_columns",
                    "The row contains more values than the CSV header.",
                )
            record_type = (row.get("record_type") or "").strip().upper()
            if record_type not in {"BALANCE", "TRANSACTION"}:
                raise RowValidationError(
                    "invalid_record_type",
                    "record_type must be BALANCE or TRANSACTION.",
                )

            account_id = (row.get("account_id") or "").strip()
            account = accounts.get(account_id)
            if account is None:
                raise RowValidationError(
                    "unknown_account",
                    "account_id does not belong to this workspace.",
                )

            currency = (row.get("currency") or "").strip().upper()
            if currency != account.currency:
                raise RowValidationError(
                    "currency_mismatch",
                    f"currency must match the account currency {account.currency}.",
                )

            occurred_at = _parse_timestamp(row.get("occurred_at") or "")
            amount = _parse_amount(row.get("amount") or "")

            if record_type == "BALANCE":
                balance_key = (account.id, occurred_at, amount)
                if balance_key in balance_keys:
                    import_run.skipped_duplicate_rows += 1
                    continue
                balance_keys.add(balance_key)
                session.add(
                    BalanceSnapshot(
                        id=str(uuid4()),
                        workspace_id=workspace_id,
                        account_id=account.id,
                        import_run_id=import_run.id,
                        source_row_number=row_number,
                        amount=amount,
                        currency=currency,
                        balance_as_of=occurred_at,
                        created_at=now,
                    )
                )
                if occurred_at >= _as_utc(account.balance_as_of):
                    account.balance = amount
                    account.balance_as_of = occurred_at
            else:
                transaction_id = (row.get("transaction_id") or "").strip()
                if not transaction_id:
                    raise RowValidationError(
                        "missing_transaction_id",
                        "transaction_id is required for TRANSACTION rows.",
                    )
                if len(transaction_id) > 140:
                    raise RowValidationError(
                        "transaction_id_too_long",
                        "transaction_id must not exceed 140 characters.",
                    )
                transaction_key = (account.id, transaction_id)
                if transaction_key in transaction_keys:
                    import_run.skipped_duplicate_rows += 1
                    continue
                transaction_keys.add(transaction_key)
                description = (row.get("description") or "").strip()
                if len(description) > 500:
                    raise RowValidationError(
                        "description_too_long",
                        "description must not exceed 500 characters.",
                    )
                session.add(
                    BankTransaction(
                        id=str(uuid4()),
                        workspace_id=workspace_id,
                        account_id=account.id,
                        import_run_id=import_run.id,
                        external_id=transaction_id,
                        booked_at=occurred_at,
                        amount=amount,
                        currency=currency,
                        description=description,
                        created_at=now,
                    )
                )

            import_run.accepted_rows += 1
        except RowValidationError as error:
            import_run.rejected_rows += 1
            session.add(
                ImportIssue(
                    id=str(uuid4()),
                    import_run_id=import_run.id,
                    row_number=row_number,
                    code=error.code,
                    message=error.message,
                )
            )

    if import_run.total_rows == 0:
        session.rollback()
        raise ImportFileError("The CSV file contains no data rows.")

    if import_run.rejected_rows == 0:
        import_run.status = "completed"
    elif import_run.accepted_rows == 0:
        import_run.status = "rejected"
    else:
        import_run.status = "partial"
    import_run.completed_at = datetime.now(UTC).replace(microsecond=0)
    session.add(
        AuditEvent(
            id=str(uuid4()),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="bank_csv.imported",
            target_type="import_run",
            target_id=import_run.id,
            detail=json.dumps(
                {
                    "status": import_run.status,
                    "accepted_rows": import_run.accepted_rows,
                    "rejected_rows": import_run.rejected_rows,
                    "skipped_duplicate_rows": import_run.skipped_duplicate_rows,
                },
                separators=(",", ":"),
            ),
            created_at=import_run.completed_at,
        )
    )
    session.commit()
    return _response(session, import_run, duplicate_file=False)


def list_import_runs(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
) -> list[ImportRunResponse]:
    require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
    )
    import_runs = session.scalars(
        select(ImportRun)
        .where(ImportRun.workspace_id == workspace_id)
        .order_by(ImportRun.created_at.desc())
    ).all()
    return [
        _response(session, import_run, duplicate_file=False)
        for import_run in import_runs
    ]
