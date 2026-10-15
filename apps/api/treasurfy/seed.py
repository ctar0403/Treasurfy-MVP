from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from treasurfy.models import (
    AuditEvent,
    BankAccount,
    Base,
    Entity,
    ExpectedCashFlow,
    FxRate,
    LiquidityRule,
    Membership,
    MembershipRole,
    Payment,
    PaymentProfile,
    User,
    Workspace,
)

DEMO_WORKSPACE_ID = "workspace-demo"
SECONDARY_WORKSPACE_ID = "workspace-secondary"
DEMO_USER_ID = "user-demo-admin"
OUTSIDER_USER_ID = "user-outsider"
VIEWER_USER_ID = "user-demo-viewer"
PREPARER_USER_ID = "user-demo-preparer"
APPROVER_USER_ID = "user-demo-approver"


def _add_missing(session: Session, records: list[Base]) -> None:
    """Insert seed records by dependency layer and make retries safe."""
    for record in records:
        if session.get(type(record), getattr(record, "id")) is None:
            session.add(record)
    session.commit()


def _seed_base_data(session: Session) -> None:
    now = datetime.now(UTC).replace(microsecond=0)

    _add_missing(
        session,
        [
            Workspace(
                id=DEMO_WORKSPACE_ID,
                name="Northstar Software Group",
                base_currency="GBP",
            ),
            Workspace(
                id=SECONDARY_WORKSPACE_ID,
                name="Separate Demo Company",
                base_currency="USD",
            ),
            User(
                id=DEMO_USER_ID,
                email="treasury.admin@example.test",
                display_name="Treasury Admin",
            ),
            User(
                id=OUTSIDER_USER_ID,
                email="outsider@example.test",
                display_name="Other Workspace User",
            ),
            User(
                id=VIEWER_USER_ID,
                email="treasury.viewer@example.test",
                display_name="Treasury Viewer",
            ),
        ]
    )

    _add_missing(
        session,
        [
            Membership(
                id="membership-demo-admin",
                workspace_id=DEMO_WORKSPACE_ID,
                user_id=DEMO_USER_ID,
                role=MembershipRole.ADMIN,
            ),
            Membership(
                id="membership-secondary-admin",
                workspace_id=SECONDARY_WORKSPACE_ID,
                user_id=OUTSIDER_USER_ID,
                role=MembershipRole.ADMIN,
            ),
            Membership(
                id="membership-demo-viewer",
                workspace_id=DEMO_WORKSPACE_ID,
                user_id=VIEWER_USER_ID,
                role=MembershipRole.VIEWER,
            ),
            Entity(
                id="entity-uk",
                workspace_id=DEMO_WORKSPACE_ID,
                name="Northstar UK Ltd",
                country_code="GB",
            ),
            Entity(
                id="entity-us",
                workspace_id=DEMO_WORKSPACE_ID,
                name="Northstar US Inc",
                country_code="US",
            ),
            Entity(
                id="entity-eu",
                workspace_id=DEMO_WORKSPACE_ID,
                name="Northstar Europe GmbH",
                country_code="DE",
            ),
        ],
    )

    _add_missing(
        session,
        [
            BankAccount(
                id="account-hsbc-gbp",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-uk",
                bank_name="HSBC",
                account_name="UK Operating",
                masked_account_number="****5432",
                currency="GBP",
                balance=Decimal("850000.00"),
                balance_as_of=now - timedelta(hours=2),
            ),
            BankAccount(
                id="account-barclays-eur",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-uk",
                bank_name="Barclays",
                account_name="UK EUR Collections",
                masked_account_number="****1144",
                currency="EUR",
                balance=Decimal("420000.00"),
                balance_as_of=now - timedelta(hours=3),
            ),
            BankAccount(
                id="account-jpm-usd",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-us",
                bank_name="JPMorgan",
                account_name="US Operating",
                masked_account_number="****9021",
                currency="USD",
                balance=Decimal("680000.00"),
                balance_as_of=now - timedelta(hours=1),
            ),
            BankAccount(
                id="account-citi-gbp",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-us",
                bank_name="Citi",
                account_name="US GBP Reserve",
                masked_account_number="****7710",
                currency="GBP",
                balance=Decimal("125000.00"),
                balance_as_of=now - timedelta(hours=4),
            ),
            BankAccount(
                id="account-deutsche-eur",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-eu",
                bank_name="Deutsche Bank",
                account_name="EU Operating",
                masked_account_number="****6638",
                currency="EUR",
                balance=Decimal("310000.00"),
                balance_as_of=now - timedelta(hours=30),
            ),
            BankAccount(
                id="account-wise-usd",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-eu",
                bank_name="Wise",
                account_name="EU USD Collections",
                masked_account_number="****2205",
                currency="USD",
                balance=Decimal("95000.00"),
                balance_as_of=now - timedelta(hours=5),
            ),
        ]
    )

    _add_missing(
        session,
        [
            FxRate(
                id="fx-gbp-gbp",
                workspace_id=DEMO_WORKSPACE_ID,
                source_currency="GBP",
                target_currency="GBP",
                rate=Decimal("1.00000000"),
                rate_as_of=now,
                source="demo",
            ),
            FxRate(
                id="fx-usd-gbp",
                workspace_id=DEMO_WORKSPACE_ID,
                source_currency="USD",
                target_currency="GBP",
                rate=Decimal("0.76000000"),
                rate_as_of=now,
                source="demo",
            ),
            FxRate(
                id="fx-eur-gbp",
                workspace_id=DEMO_WORKSPACE_ID,
                source_currency="EUR",
                target_currency="GBP",
                rate=Decimal("0.86000000"),
                rate_as_of=now,
                source="demo",
            ),
        ]
    )

    _add_missing(
        session,
        [
            AuditEvent(
                id="audit-demo-seeded",
                workspace_id=DEMO_WORKSPACE_ID,
                actor_user_id=DEMO_USER_ID,
                action="workspace.demo_seeded",
                target_type="workspace",
                target_id=DEMO_WORKSPACE_ID,
                detail='{"source":"synthetic"}',
                created_at=now,
            ),
        ],
    )


def _seed_forecast_data(session: Session) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    today = now.date()
    _add_missing(
        session,
        [
            ExpectedCashFlow(
                id="flow-uk-renewal",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-uk",
                account_id="account-hsbc-gbp",
                name="Annual customer renewal",
                direction="inflow",
                amount=Decimal("180000.00"),
                currency="GBP",
                due_date=today + timedelta(days=12),
                source="demo",
                status="planned",
                created_at=now,
            ),
            ExpectedCashFlow(
                id="flow-uk-payroll",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-uk",
                account_id="account-hsbc-gbp",
                name="UK payroll",
                direction="outflow",
                amount=Decimal("220000.00"),
                currency="GBP",
                due_date=today + timedelta(days=25),
                source="demo",
                status="planned",
                created_at=now,
            ),
            ExpectedCashFlow(
                id="flow-us-receipt",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-us",
                account_id="account-jpm-usd",
                name="Enterprise customer receipt",
                direction="inflow",
                amount=Decimal("250000.00"),
                currency="USD",
                due_date=today + timedelta(days=18),
                source="demo",
                status="planned",
                created_at=now,
            ),
            ExpectedCashFlow(
                id="flow-us-cloud",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-us",
                account_id="account-jpm-usd",
                name="Cloud infrastructure",
                direction="outflow",
                amount=Decimal("90000.00"),
                currency="USD",
                due_date=today + timedelta(days=33),
                source="demo",
                status="planned",
                created_at=now,
            ),
            ExpectedCashFlow(
                id="flow-eu-payroll",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-eu",
                account_id="account-deutsche-eur",
                name="EU payroll and taxes",
                direction="outflow",
                amount=Decimal("260000.00"),
                currency="EUR",
                due_date=today + timedelta(days=20),
                source="demo",
                status="planned",
                created_at=now,
            ),
            ExpectedCashFlow(
                id="flow-eu-receipt",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-eu",
                account_id="account-deutsche-eur",
                name="EU customer receivable",
                direction="inflow",
                amount=Decimal("120000.00"),
                currency="EUR",
                due_date=today + timedelta(days=50),
                source="demo",
                status="planned",
                created_at=now,
            ),
            ExpectedCashFlow(
                id="flow-uk-tax",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-uk",
                account_id="account-hsbc-gbp",
                name="Quarterly tax payment",
                direction="outflow",
                amount=Decimal("140000.00"),
                currency="GBP",
                due_date=today + timedelta(days=75),
                source="demo",
                status="planned",
                created_at=now,
            ),
        ],
    )
    _add_missing(
        session,
        [
            LiquidityRule(
                id="liquidity-rule-uk",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-uk",
                minimum_balance_base=Decimal("600000.00"),
                created_at=now,
            ),
            LiquidityRule(
                id="liquidity-rule-us",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-us",
                minimum_balance_base=Decimal("350000.00"),
                created_at=now,
            ),
            LiquidityRule(
                id="liquidity-rule-eu",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-eu",
                minimum_balance_base=Decimal("150000.00"),
                created_at=now,
            ),
        ],
    )


def _seed_payment_data(session: Session) -> None:
    now = datetime.now(UTC).replace(microsecond=0)

    _add_missing(
        session,
        [
            User(
                id=PREPARER_USER_ID,
                email="treasury.preparer@example.test",
                display_name="Priya Payment Maker",
            ),
            User(
                id=APPROVER_USER_ID,
                email="treasury.approver@example.test",
                display_name="Alex Payment Checker",
            ),
        ],
    )
    _add_missing(
        session,
        [
            Membership(
                id="membership-demo-preparer",
                workspace_id=DEMO_WORKSPACE_ID,
                user_id=PREPARER_USER_ID,
                role=MembershipRole.PREPARER,
            ),
            Membership(
                id="membership-demo-approver",
                workspace_id=DEMO_WORKSPACE_ID,
                user_id=APPROVER_USER_ID,
                role=MembershipRole.APPROVER,
            ),
            PaymentProfile(
                id="payment-profile-pain001-demo",
                workspace_id=DEMO_WORKSPACE_ID,
                name="Illustrative ISO 20022 credit transfer",
                version="1.0.0",
                message_type="pain.001.001.03-demo",
                allowed_currencies="GBP,USD,EUR",
                maximum_amount=Decimal("1000000.00"),
                created_at=now,
            ),
        ],
    )

    _add_missing(
        session,
        [
            Payment(
                id="payment-demo-cloud",
                workspace_id=DEMO_WORKSPACE_ID,
                entity_id="entity-eu",
                source_account_id="account-deutsche-eur",
                payment_profile_id="payment-profile-pain001-demo",
                profile_version="1.0.0",
                beneficiary_name="Atlas Cloud Services GmbH",
                beneficiary_account="DE89370400440532013000",
                beneficiary_country_code="DE",
                amount=Decimal("48000.00"),
                currency="EUR",
                requested_execution_date=now.date() + timedelta(days=4),
                reference="INV-2026-1042",
                status="pending_approval",
                validation_status="passed",
                validation_detail="[]",
                created_by_user_id=PREPARER_USER_ID,
                submitted_by_user_id=PREPARER_USER_ID,
                decided_by_user_id=None,
                created_at=now,
                submitted_at=now,
                decided_at=None,
            ),
        ],
    )
    _add_missing(
        session,
        [
            AuditEvent(
                id="audit-payment-demo-created",
                workspace_id=DEMO_WORKSPACE_ID,
                actor_user_id=PREPARER_USER_ID,
                action="payment.created",
                target_type="payment",
                target_id="payment-demo-cloud",
                detail='{"profile_version":"1.0.0","status":"draft","validation_status":"passed"}',
                created_at=now,
            ),
            AuditEvent(
                id="audit-payment-demo-submitted",
                workspace_id=DEMO_WORKSPACE_ID,
                actor_user_id=PREPARER_USER_ID,
                action="payment.submitted",
                target_type="payment",
                target_id="payment-demo-cloud",
                detail='{"status":"pending_approval"}',
                created_at=now,
            ),
        ],
    )


def seed_demo_data(session: Session) -> None:
    _seed_base_data(session)
    _seed_forecast_data(session)
    _seed_payment_data(session)
