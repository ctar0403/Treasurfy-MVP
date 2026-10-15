from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event, func, select, text
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
from treasurfy.seed import seed_demo_data


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite://")
    event.listen(
        engine,
        "connect",
        lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def _count(session: Session, model: type[Base]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_demo_seed_respects_foreign_keys_and_is_retryable(session: Session) -> None:
    # This mirrors D1's enforced foreign keys; the previous all-at-once seed
    # failed while inserting the first audit event before its parent rows.
    seed_demo_data(session)

    expected_counts = {
        Workspace: 2,
        User: 5,
        Membership: 5,
        Entity: 3,
        BankAccount: 6,
        FxRate: 3,
        AuditEvent: 3,
        ExpectedCashFlow: 7,
        LiquidityRule: 3,
        PaymentProfile: 1,
        Payment: 1,
    }
    assert {model: _count(session, model) for model in expected_counts} == expected_counts

    # A partial first attempt must be repaired, and a normal repeat must not
    # create duplicates or reset already-seeded demo records.
    missing_flow = session.get(ExpectedCashFlow, "flow-uk-renewal")
    assert missing_flow is not None
    session.delete(missing_flow)
    session.commit()

    seed_demo_data(session)

    assert session.get(ExpectedCashFlow, "flow-uk-renewal") is not None
    assert {model: _count(session, model) for model in expected_counts} == expected_counts


def test_membership_reads_existing_lowercase_role_values(session: Session) -> None:
    session.execute(
        text("INSERT INTO workspaces (id, name, base_currency) VALUES ('w1', 'Demo', 'GBP')")
    )
    session.execute(
        text("INSERT INTO users (id, email, display_name) VALUES ('u1', 'u@example.com', 'Demo User')")
    )
    session.execute(
        text(
            "INSERT INTO memberships (id, workspace_id, user_id, role) "
            "VALUES ('m1', 'w1', 'u1', 'admin')"
        )
    )
    session.commit()

    membership = session.get(Membership, "m1")

    assert membership is not None
    assert membership.role is MembershipRole.ADMIN
