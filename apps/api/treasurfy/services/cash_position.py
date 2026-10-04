from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from treasurfy.models import BankAccount, Entity, FxRate, Membership, Workspace
from treasurfy.schemas import AccountCash, CashPositionResponse, EntityCash

MONEY_QUANTUM = Decimal("0.01")
FRESHNESS_LIMIT = timedelta(hours=24)


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceAccessDeniedError(Exception):
    pass


class MissingFxRateError(Exception):
    def __init__(self, currency: str) -> None:
        super().__init__(f"No FX rate is configured for {currency}.")
        self.currency = currency


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))


def _rate(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.00000001"))
    return format(normalized, "f")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def get_cash_position(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    now: datetime | None = None,
) -> CashPositionResponse:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError

    membership = session.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == actor_user_id,
        )
    )
    if membership is None:
        raise WorkspaceAccessDeniedError

    account_rows = session.execute(
        select(BankAccount, Entity)
        .join(Entity, BankAccount.entity_id == Entity.id)
        .where(
            BankAccount.workspace_id == workspace_id,
            Entity.workspace_id == workspace_id,
        )
        .order_by(Entity.name, BankAccount.bank_name, BankAccount.account_name)
    ).all()

    fx_rates = {
        item.source_currency: item
        for item in session.scalars(
            select(FxRate).where(FxRate.workspace_id == workspace_id)
        )
    }

    clock = _as_utc(now or datetime.now(UTC))
    total_cash = Decimal("0")
    stale_account_count = 0
    oldest_balance: datetime | None = None
    latest_common_fx_time: datetime | None = None
    account_results: list[AccountCash] = []
    entity_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    entity_counts: dict[str, int] = defaultdict(int)
    entity_metadata: dict[str, Entity] = {}

    for account, entity in account_rows:
        fx_rate = fx_rates.get(account.currency)
        if fx_rate is None or fx_rate.target_currency != workspace.base_currency:
            raise MissingFxRateError(account.currency)

        native_balance = Decimal(account.balance)
        rate = Decimal(fx_rate.rate)
        base_balance = (native_balance * rate).quantize(
            MONEY_QUANTUM, rounding=ROUND_HALF_UP
        )
        balance_time = _as_utc(account.balance_as_of)
        rate_time = _as_utc(fx_rate.rate_as_of)
        is_stale = clock - balance_time > FRESHNESS_LIMIT

        total_cash += base_balance
        entity_totals[entity.id] += base_balance
        entity_counts[entity.id] += 1
        entity_metadata[entity.id] = entity
        stale_account_count += int(is_stale)
        oldest_balance = (
            balance_time
            if oldest_balance is None
            else min(oldest_balance, balance_time)
        )
        latest_common_fx_time = (
            rate_time
            if latest_common_fx_time is None
            else min(latest_common_fx_time, rate_time)
        )

        account_results.append(
            AccountCash(
                account_id=account.id,
                account_name=account.account_name,
                masked_account_number=account.masked_account_number,
                bank_name=account.bank_name,
                entity_id=entity.id,
                entity_name=entity.name,
                currency=account.currency,
                native_balance=_money(native_balance),
                fx_rate_to_base=_rate(rate),
                base_currency_balance=_money(base_balance),
                balance_as_of=_iso_utc(balance_time) or "",
                freshness="stale" if is_stale else "fresh",
            )
        )

    entity_results = [
        EntityCash(
            entity_id=entity_id,
            entity_name=entity_metadata[entity_id].name,
            country_code=entity_metadata[entity_id].country_code,
            base_currency_balance=_money(entity_totals[entity_id]),
            account_count=entity_counts[entity_id],
        )
        for entity_id in sorted(
            entity_metadata, key=lambda item: entity_metadata[item].name
        )
    ]

    return CashPositionResponse(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        base_currency=workspace.base_currency,
        total_cash=_money(total_cash),
        account_count=len(account_results),
        entity_count=len(entity_results),
        stale_account_count=stale_account_count,
        oldest_balance_as_of=_iso_utc(oldest_balance),
        fx_rate_as_of=_iso_utc(latest_common_fx_time),
        accounts=account_results,
        entities=entity_results,
    )
