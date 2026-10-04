from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from treasurfy.models import (
    AuditEvent,
    BankAccount,
    Entity,
    ExpectedCashFlow,
    ForecastPoint,
    ForecastRun,
    FxRate,
    LiquidityRule,
    MembershipRole,
)
from treasurfy.schemas import (
    EntityForecastResponse,
    ExpectedCashFlowCreate,
    ExpectedCashFlowResponse,
    ForecastHorizonResponse,
    ForecastPointResponse,
    ForecastResponse,
    LiquidityAlertResponse,
)
from treasurfy.services.access import require_workspace_access

MONEY_QUANTUM = Decimal("0.01")
WRITE_ROLES = {MembershipRole.ADMIN, MembershipRole.PREPARER}


class ForecastConfigurationError(Exception):
    pass


class CashFlowValidationError(Exception):
    pass


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _load_inputs(session: Session, workspace_id: str):
    account_rows = session.execute(
        select(BankAccount, Entity)
        .join(Entity, BankAccount.entity_id == Entity.id)
        .where(
            BankAccount.workspace_id == workspace_id,
            Entity.workspace_id == workspace_id,
        )
        .order_by(BankAccount.id)
    ).all()
    rates = {
        item.source_currency: item
        for item in session.scalars(
            select(FxRate).where(FxRate.workspace_id == workspace_id)
        )
    }
    flows = session.scalars(
        select(ExpectedCashFlow)
        .where(
            ExpectedCashFlow.workspace_id == workspace_id,
            ExpectedCashFlow.status == "planned",
        )
        .order_by(ExpectedCashFlow.due_date, ExpectedCashFlow.id)
    ).all()
    rules = {
        item.entity_id: item
        for item in session.scalars(
            select(LiquidityRule).where(LiquidityRule.workspace_id == workspace_id)
        )
    }
    return account_rows, rates, flows, rules


def _base_amount(
    amount: Decimal,
    currency: str,
    base_currency: str,
    rates: dict[str, FxRate],
) -> Decimal:
    rate = rates.get(currency)
    if rate is None or rate.target_currency != base_currency:
        raise ForecastConfigurationError(
            f"Missing {currency} to {base_currency} FX rate."
        )
    return (amount * Decimal(rate.rate)).quantize(
        MONEY_QUANTUM, rounding=ROUND_HALF_UP
    )


def _fingerprint(
    *,
    as_of_date: date,
    horizon_days: int,
    account_rows,
    rates: dict[str, FxRate],
    flows: list[ExpectedCashFlow],
    rules: dict[str, LiquidityRule],
) -> str:
    payload = {
        "as_of_date": as_of_date.isoformat(),
        "horizon_days": horizon_days,
        "accounts": [
            [
                account.id,
                str(account.balance),
                account.currency,
                account.balance_as_of.isoformat(),
            ]
            for account, _ in account_rows
        ],
        "rates": [
            [currency, str(rate.rate), rate.target_currency, rate.rate_as_of.isoformat()]
            for currency, rate in sorted(rates.items())
        ],
        "flows": [
            [
                flow.id,
                flow.entity_id,
                flow.account_id,
                flow.direction,
                str(flow.amount),
                flow.currency,
                flow.due_date.isoformat(),
                flow.status,
            ]
            for flow in flows
        ],
        "rules": [
            [entity_id, str(rule.minimum_balance_base)]
            for entity_id, rule in sorted(rules.items())
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_forecast(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    as_of_date: date,
    horizon_days: int = 90,
) -> ForecastResponse:
    workspace, _ = require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
    )
    account_rows, rates, all_flows, rules = _load_inputs(session, workspace_id)
    if not account_rows:
        raise ForecastConfigurationError("The workspace has no bank accounts.")

    final_date = as_of_date + timedelta(days=horizon_days)
    flows = [
        flow for flow in all_flows if as_of_date <= flow.due_date <= final_date
    ]
    fingerprint = _fingerprint(
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        account_rows=account_rows,
        rates=rates,
        flows=flows,
        rules=rules,
    )
    existing_run = session.scalar(
        select(ForecastRun).where(
            ForecastRun.workspace_id == workspace_id,
            ForecastRun.input_fingerprint == fingerprint,
        )
    )

    entities: dict[str, Entity] = {}
    entity_balances: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for account, entity in account_rows:
        entities[entity.id] = entity
        entity_balances[entity.id] += _base_amount(
            Decimal(account.balance),
            account.currency,
            workspace.base_currency,
            rates,
        )
    opening_entity_balances = dict(entity_balances)
    opening_cash = sum(entity_balances.values(), Decimal("0"))

    flows_by_date: dict[date, list[tuple[ExpectedCashFlow, Decimal]]] = defaultdict(list)
    flow_responses: list[ExpectedCashFlowResponse] = []
    account_lookup = {account.id: account for account, _ in account_rows}
    for flow in flows:
        signed_native = flow.amount if flow.direction == "inflow" else -flow.amount
        signed_base = _base_amount(
            Decimal(signed_native), flow.currency, workspace.base_currency, rates
        )
        flows_by_date[flow.due_date].append((flow, signed_base))
        flow_responses.append(
            ExpectedCashFlowResponse(
                id=flow.id,
                entity_id=flow.entity_id,
                entity_name=entities[flow.entity_id].name,
                account_id=flow.account_id,
                account_name=account_lookup[flow.account_id].account_name,
                name=flow.name,
                direction=flow.direction,
                amount=_money(Decimal(flow.amount)),
                currency=flow.currency,
                base_currency_amount=_money(signed_base),
                due_date=flow.due_date,
                source=flow.source,
                status=flow.status,
            )
        )

    workspace_points: list[ForecastPointResponse] = []
    entity_points: dict[str, list[tuple[date, Decimal]]] = defaultdict(list)
    for day_index in range(horizon_days + 1):
        forecast_date = as_of_date + timedelta(days=day_index)
        for flow, signed_base in flows_by_date.get(forecast_date, []):
            entity_balances[flow.entity_id] += signed_base
        total = sum(entity_balances.values(), Decimal("0"))
        workspace_points.append(
            ForecastPointResponse(date=forecast_date, total_cash=_money(total))
        )
        for entity_id in entities:
            entity_points[entity_id].append((forecast_date, entity_balances[entity_id]))

    horizons = [
        ForecastHorizonResponse(
            days=days,
            date=workspace_points[days].date,
            total_cash=workspace_points[days].total_cash,
            change_from_opening=_money(
                Decimal(workspace_points[days].total_cash) - opening_cash
            ),
        )
        for days in (30, 60, 90)
    ]

    balances_at_30 = {
        entity_id: entity_points[entity_id][30][1] for entity_id in entities
    }
    rankings = {
        entity_id: rank
        for rank, (entity_id, _) in enumerate(
            sorted(balances_at_30.items(), key=lambda item: item[1], reverse=True),
            start=1,
        )
    }
    alerts: list[LiquidityAlertResponse] = []
    entity_responses: list[EntityForecastResponse] = []
    for entity_id, entity in sorted(entities.items(), key=lambda item: item[1].name):
        rule = rules.get(entity_id)
        breach: tuple[date, Decimal] | None = None
        if rule is not None:
            threshold = Decimal(rule.minimum_balance_base)
            breach = next(
                (
                    (forecast_date, balance)
                    for forecast_date, balance in entity_points[entity_id]
                    if balance < threshold
                ),
                None,
            )
            if breach is not None:
                alerts.append(
                    LiquidityAlertResponse(
                        entity_id=entity_id,
                        entity_name=entity.name,
                        code="ENTITY_BELOW_MINIMUM",
                        severity="high",
                        breach_date=breach[0],
                        projected_balance=_money(breach[1]),
                        minimum_balance=_money(threshold),
                        message=(
                            f"{entity.name} is projected below its minimum cash "
                            f"threshold on {breach[0].isoformat()}."
                        ),
                    )
                )
        entity_responses.append(
            EntityForecastResponse(
                entity_id=entity_id,
                entity_name=entity.name,
                opening_cash=_money(opening_entity_balances[entity_id]),
                projected_30_days=_money(entity_points[entity_id][30][1]),
                projected_60_days=_money(entity_points[entity_id][60][1]),
                projected_90_days=_money(entity_points[entity_id][90][1]),
                minimum_balance=(
                    _money(Decimal(rule.minimum_balance_base)) if rule else None
                ),
                status="at_risk" if breach else "healthy",
                first_breach_date=breach[0] if breach else None,
                rank_at_30_days=rankings[entity_id],
            )
        )

    now = datetime.now(UTC).replace(microsecond=0)
    if existing_run is None:
        run = ForecastRun(
            id=str(uuid4()),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            as_of_date=as_of_date,
            horizon_days=horizon_days,
            base_currency=workspace.base_currency,
            opening_cash=opening_cash,
            input_fingerprint=fingerprint,
            created_at=now,
        )
        session.add(run)
        session.flush()
        for point in workspace_points:
            session.add(
                ForecastPoint(
                    id=str(uuid4()),
                    forecast_run_id=run.id,
                    scope="workspace",
                    entity_key="",
                    forecast_date=point.date,
                    balance=Decimal(point.total_cash),
                )
            )
        for entity_id, points in entity_points.items():
            for forecast_date, balance in points:
                session.add(
                    ForecastPoint(
                        id=str(uuid4()),
                        forecast_run_id=run.id,
                        scope="entity",
                        entity_key=entity_id,
                        forecast_date=forecast_date,
                        balance=balance,
                    )
                )
        session.add(
            AuditEvent(
                id=str(uuid4()),
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                action="forecast.generated",
                target_type="forecast_run",
                target_id=run.id,
                detail=json.dumps(
                    {"horizon_days": horizon_days, "alerts": len(alerts)},
                    separators=(",", ":"),
                ),
                created_at=now,
            )
        )
        session.commit()
        reused_run = False
    else:
        run = existing_run
        reused_run = True

    return ForecastResponse(
        forecast_run_id=run.id,
        reused_run=reused_run,
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        base_currency=workspace.base_currency,
        opening_cash=_money(opening_cash),
        input_fingerprint=fingerprint,
        created_at=_iso_utc(run.created_at),
        horizons=horizons,
        points=workspace_points,
        entities=entity_responses,
        alerts=alerts,
        expected_flows=flow_responses,
    )


def list_expected_cash_flows(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
) -> list[ExpectedCashFlowResponse]:
    workspace, _ = require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
    )
    account_rows, rates, flows, _ = _load_inputs(session, workspace_id)
    entities = {entity.id: entity for _, entity in account_rows}
    accounts = {account.id: account for account, _ in account_rows}
    responses: list[ExpectedCashFlowResponse] = []
    for flow in flows:
        signed = flow.amount if flow.direction == "inflow" else -flow.amount
        responses.append(
            ExpectedCashFlowResponse(
                id=flow.id,
                entity_id=flow.entity_id,
                entity_name=entities[flow.entity_id].name,
                account_id=flow.account_id,
                account_name=accounts[flow.account_id].account_name,
                name=flow.name,
                direction=flow.direction,
                amount=_money(Decimal(flow.amount)),
                currency=flow.currency,
                base_currency_amount=_money(
                    _base_amount(
                        Decimal(signed), flow.currency, workspace.base_currency, rates
                    )
                ),
                due_date=flow.due_date,
                source=flow.source,
                status=flow.status,
            )
        )
    return responses


def add_expected_cash_flow(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    request: ExpectedCashFlowCreate,
) -> ExpectedCashFlowResponse:
    workspace, _ = require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        allowed_roles=WRITE_ROLES,
    )
    entity = session.scalar(
        select(Entity).where(
            Entity.id == request.entity_id,
            Entity.workspace_id == workspace_id,
        )
    )
    account = session.scalar(
        select(BankAccount).where(
            BankAccount.id == request.account_id,
            BankAccount.workspace_id == workspace_id,
        )
    )
    if entity is None or account is None or account.entity_id != entity.id:
        raise CashFlowValidationError(
            "The selected entity and account do not match this workspace."
        )
    currency = request.currency.upper()
    if currency != account.currency:
        raise CashFlowValidationError(
            f"Currency must match the account currency {account.currency}."
        )
    if request.due_date < datetime.now(UTC).date():
        raise CashFlowValidationError(
            "The due date for a planned cash flow cannot be in the past."
        )

    rates = {
        item.source_currency: item
        for item in session.scalars(
            select(FxRate).where(FxRate.workspace_id == workspace_id)
        )
    }
    now = datetime.now(UTC).replace(microsecond=0)
    flow = ExpectedCashFlow(
        id=str(uuid4()),
        workspace_id=workspace_id,
        entity_id=entity.id,
        account_id=account.id,
        name=request.name.strip(),
        direction=request.direction,
        amount=request.amount,
        currency=currency,
        due_date=request.due_date,
        source="manual",
        status="planned",
        created_at=now,
    )
    session.add(flow)
    session.add(
        AuditEvent(
            id=str(uuid4()),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="expected_cash_flow.created",
            target_type="expected_cash_flow",
            target_id=flow.id,
            detail=json.dumps({"direction": flow.direction}, separators=(",", ":")),
            created_at=now,
        )
    )
    session.commit()

    signed = flow.amount if flow.direction == "inflow" else -flow.amount
    return ExpectedCashFlowResponse(
        id=flow.id,
        entity_id=entity.id,
        entity_name=entity.name,
        account_id=account.id,
        account_name=account.account_name,
        name=flow.name,
        direction=flow.direction,
        amount=_money(Decimal(flow.amount)),
        currency=flow.currency,
        base_currency_amount=_money(
            _base_amount(Decimal(signed), flow.currency, workspace.base_currency, rates)
        ),
        due_date=flow.due_date,
        source=flow.source,
        status=flow.status,
    )
