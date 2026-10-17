from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from treasurfy.models import AuditEvent, DailyBriefRun, Payment, PaymentExport
from treasurfy.schemas import (
    DailyBriefAction,
    DailyBriefHighlight,
    DailyBriefMetric,
    DailyBriefResponse,
)
from treasurfy.services.access import require_workspace_access
from treasurfy.services.cash_position import get_cash_position
from treasurfy.services.forecast import create_forecast


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _direction_context(change: Decimal, days: int) -> tuple[str, str]:
    if change < 0:
        return f"Down {abs(change):.2f} from today's position", "warning"
    if change > 0:
        return f"Up {change:.2f} from today's position", "positive"
    return f"Unchanged from today's position at day {days}", "neutral"


def _fingerprint_payload(
    *,
    as_of_date: date,
    forecast_fingerprint: str,
    stale_account_count: int,
    oldest_balance_as_of: str | None,
    payments: list[Payment],
    exported_payment_ids: set[str],
) -> str:
    payload = {
        "as_of_date": as_of_date.isoformat(),
        "forecast": forecast_fingerprint,
        "stale_account_count": stale_account_count,
        "oldest_balance_as_of": oldest_balance_as_of,
        "payments": [
            [
                payment.id,
                payment.status,
                payment.validation_status,
                str(payment.amount),
                payment.currency,
                payment.requested_execution_date.isoformat(),
                payment.submitted_at.isoformat() if payment.submitted_at else None,
                payment.decided_at.isoformat() if payment.decided_at else None,
                payment.id in exported_payment_ids,
            ]
            for payment in payments
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_daily_brief(
    session: Session,
    *,
    workspace_id: str,
    actor_user_id: str,
    as_of_date: date,
) -> DailyBriefResponse:
    workspace, _ = require_workspace_access(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
    )
    cash = get_cash_position(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
    )
    forecast = create_forecast(
        session,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        as_of_date=as_of_date,
        horizon_days=90,
    )
    payments = list(
        session.scalars(
            select(Payment)
            .where(Payment.workspace_id == workspace_id)
            .order_by(Payment.requested_execution_date, Payment.id)
        ).all()
    )
    exported_payment_ids = set(
        session.scalars(
            select(PaymentExport.payment_id)
            .join(Payment, PaymentExport.payment_id == Payment.id)
            .where(Payment.workspace_id == workspace_id)
        ).all()
    )

    input_fingerprint = _fingerprint_payload(
        as_of_date=as_of_date,
        forecast_fingerprint=forecast.input_fingerprint,
        stale_account_count=cash.stale_account_count,
        oldest_balance_as_of=cash.oldest_balance_as_of,
        payments=payments,
        exported_payment_ids=exported_payment_ids,
    )
    existing = session.scalar(
        select(DailyBriefRun).where(
            DailyBriefRun.workspace_id == workspace_id,
            DailyBriefRun.input_fingerprint == input_fingerprint,
        )
    )
    if existing is not None:
        stored = DailyBriefResponse.model_validate_json(existing.payload)
        return stored.model_copy(update={"reused_run": True})

    pending_payments = [
        payment for payment in payments if payment.status == "pending_approval"
    ]
    approved_unexported = [
        payment
        for payment in payments
        if payment.status == "approved" and payment.id not in exported_payment_ids
    ]
    failed_drafts = [
        payment
        for payment in payments
        if payment.status in {"draft", "rejected"}
        and payment.validation_status == "failed"
    ]

    horizon_30 = next(item for item in forecast.horizons if item.days == 30)
    horizon_90 = next(item for item in forecast.horizons if item.days == 90)
    change_30 = Decimal(horizon_30.change_from_opening)
    change_90 = Decimal(horizon_90.change_from_opening)
    context_30, tone_30 = _direction_context(change_30, 30)
    context_90, tone_90 = _direction_context(change_90, 90)

    metrics = [
        DailyBriefMetric(
            key="total_cash",
            label="Cash available",
            value=cash.total_cash,
            currency=cash.base_currency,
            context=f"Across {cash.entity_count} entities and {cash.account_count} accounts",
            tone="neutral",
        ),
        DailyBriefMetric(
            key="cash_30_days",
            label="30-day forecast",
            value=horizon_30.total_cash,
            currency=forecast.base_currency,
            context=context_30,
            tone=tone_30,
        ),
        DailyBriefMetric(
            key="cash_90_days",
            label="90-day forecast",
            value=horizon_90.total_cash,
            currency=forecast.base_currency,
            context=context_90,
            tone=tone_90,
        ),
        DailyBriefMetric(
            key="pending_approvals",
            label="Pending approvals",
            value=str(len(pending_payments)),
            currency=None,
            context="Payments requiring a separate checker",
            tone="warning" if pending_payments else "positive",
        ),
    ]

    highlights: list[DailyBriefHighlight] = []
    actions: list[DailyBriefAction] = []
    for alert in forecast.alerts:
        highlights.append(
            DailyBriefHighlight(
                severity="critical",
                title=f"Liquidity threshold at {alert.entity_name}",
                detail=(
                    f"Projected {forecast.base_currency} {alert.projected_balance} on "
                    f"{alert.breach_date.isoformat()}, below the configured "
                    f"{forecast.base_currency} {alert.minimum_balance} minimum."
                ),
                evidence=[
                    f"forecast:{forecast.forecast_run_id}",
                    f"entity:{alert.entity_id}",
                    f"liquidity-rule:{alert.entity_id}",
                ],
            )
        )
        actions.append(
            DailyBriefAction(
                priority="critical",
                title=f"Resolve projected shortfall at {alert.entity_name}",
                detail=(
                    f"Review the dated inflows and outflows before "
                    f"{alert.breach_date.isoformat()}."
                ),
                target_type="entity",
                target_id=alert.entity_id,
            )
        )

    if pending_payments:
        total_by_currency: dict[str, Decimal] = {}
        for payment in pending_payments:
            total_by_currency[payment.currency] = total_by_currency.get(
                payment.currency, Decimal("0")
            ) + Decimal(payment.amount)
            actions.append(
                DailyBriefAction(
                    priority="high",
                    title=f"Decide payment to {payment.beneficiary_name}",
                    detail=(
                        f"{payment.currency} {Decimal(payment.amount):.2f} is waiting "
                        f"for checker approval for {payment.requested_execution_date.isoformat()}."
                    ),
                    target_type="payment",
                    target_id=payment.id,
                )
            )
        totals = ", ".join(
            f"{currency} {amount:.2f}"
            for currency, amount in sorted(total_by_currency.items())
        )
        highlights.append(
            DailyBriefHighlight(
                severity="warning",
                title=f"{len(pending_payments)} payment awaiting approval",
                detail=f"The checker queue totals {totals}.",
                evidence=[f"payment:{payment.id}" for payment in pending_payments],
            )
        )

    if cash.stale_account_count:
        highlights.append(
            DailyBriefHighlight(
                severity="warning",
                title=f"{cash.stale_account_count} stale account balance",
                detail=(
                    "At least one balance is older than 24 hours; refresh bank data "
                    "before making funding decisions."
                ),
                evidence=[
                    f"account:{account.account_id}@{account.balance_as_of}"
                    for account in cash.accounts
                    if account.freshness == "stale"
                ],
            )
        )
        actions.append(
            DailyBriefAction(
                priority="medium",
                title="Refresh stale bank balances",
                detail="Import a current bank file and regenerate the brief.",
                target_type="import",
                target_id="bank-csv",
            )
        )

    for payment in failed_drafts:
        actions.append(
            DailyBriefAction(
                priority="high",
                title=f"Correct payment draft for {payment.beneficiary_name}",
                detail="The draft failed its versioned payment-profile validation.",
                target_type="payment",
                target_id=payment.id,
            )
        )
    for payment in approved_unexported:
        actions.append(
            DailyBriefAction(
                priority="low",
                title=f"Export approved payment for {payment.beneficiary_name}",
                detail="The approved illustrative pain.001 file has not been generated.",
                target_type="payment",
                target_id=payment.id,
            )
        )

    if not highlights:
        highlights.append(
            DailyBriefHighlight(
                severity="info",
                title="No immediate TreasurFy exceptions",
                detail="No liquidity breach, stale balance, or approval queue was detected.",
                evidence=[f"forecast:{forecast.forecast_run_id}"],
            )
        )
    if not actions:
        actions.append(
            DailyBriefAction(
                priority="low",
                title="Review the current cash position",
                detail="No exception requires action; confirm planned flows remain current.",
                target_type="workspace",
                target_id=workspace_id,
            )
        )

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda item: (priority_order[item.priority], item.title))
    issue_count = len(forecast.alerts)
    approval_count = len(pending_payments)
    if issue_count or approval_count:
        headline = (
            f"{issue_count} liquidity risk{'s' if issue_count != 1 else ''} and "
            f"{approval_count} payment approval{'s' if approval_count != 1 else ''} need attention"
        )
    else:
        headline = "Cash is within configured thresholds"
    summary = (
        f"Available cash is {cash.base_currency} {Decimal(cash.total_cash):.2f}. "
        f"The 30-day position is {forecast.base_currency} "
        f"{Decimal(horizon_30.total_cash):.2f}, and the 90-day position is "
        f"{forecast.base_currency} {Decimal(horizon_90.total_cash):.2f}. "
        f"This brief is derived from the current balances, explicit FX rates, "
        f"planned cash flows, liquidity rules, and payment workflow state."
    )

    now = datetime.now(UTC)
    run_id = str(uuid4())
    evidence = [
        f"cash-position:{workspace_id}:{as_of_date.isoformat()}",
        f"forecast:{forecast.forecast_run_id}",
        f"forecast-input:{forecast.input_fingerprint}",
        *[f"payment:{payment.id}:{payment.status}" for payment in payments],
    ]
    response = DailyBriefResponse(
        daily_brief_run_id=run_id,
        reused_run=False,
        as_of_date=as_of_date,
        generated_at=_iso_utc(now),
        base_currency=workspace.base_currency,
        headline=headline,
        summary=summary,
        metrics=metrics,
        highlights=highlights,
        actions=actions,
        evidence=evidence,
        input_fingerprint=input_fingerprint,
    )
    session.add(
        DailyBriefRun(
            id=run_id,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            brief_date=as_of_date,
            input_fingerprint=input_fingerprint,
            payload=response.model_dump_json(),
            created_at=now,
        )
    )
    session.add(
        AuditEvent(
            id=str(uuid4()),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            action="daily_brief.generated",
            target_type="daily_brief_run",
            target_id=run_id,
            detail=json.dumps(
                {
                    "actions": len(actions),
                    "highlights": len(highlights),
                    "forecast_run_id": forecast.forecast_run_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            created_at=now,
        )
    )
    session.commit()
    return response
