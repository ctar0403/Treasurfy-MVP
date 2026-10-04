from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from treasurfy.models import (
    AuditEvent,
    BankAccount,
    Entity,
    FxRate,
    Membership,
    MembershipRole,
    User,
    Workspace,
)

DEMO_WORKSPACE_ID = "workspace-demo"
SECONDARY_WORKSPACE_ID = "workspace-secondary"
DEMO_USER_ID = "user-demo-admin"
OUTSIDER_USER_ID = "user-outsider"


def seed_demo_data(session: Session) -> None:
    if session.get(Workspace, DEMO_WORKSPACE_ID) is not None:
        return

    now = datetime.now(UTC).replace(microsecond=0)

    session.add_all(
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
        ]
    )

    entities = [
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
    ]
    session.add_all(entities)

    session.add_all(
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

    session.add_all(
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

    session.add(
        AuditEvent(
            id="audit-demo-seeded",
            workspace_id=DEMO_WORKSPACE_ID,
            actor_user_id=DEMO_USER_ID,
            action="workspace.demo_seeded",
            target_type="workspace",
            target_id=DEMO_WORKSPACE_ID,
            detail='{"source":"synthetic"}',
            created_at=now,
        )
    )
    session.commit()
