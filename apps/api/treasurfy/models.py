from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MembershipRole(str, Enum):
    ADMIN = "admin"
    PREPARER = "preparer"
    APPROVER = "approver"
    VIEWER = "viewer"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(140), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_membership"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        SqlEnum(MembershipRole, native_enum=False), nullable=False
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    accounts: Mapped[list["BankAccount"]] = relationship(back_populates="entity")


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "masked_account_number", name="uq_workspace_account"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_name: Mapped[str] = mapped_column(String(140), nullable=False)
    account_name: Mapped[str] = mapped_column(String(140), nullable=False)
    masked_account_number: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    balance_as_of: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    entity: Mapped[Entity] = relationship(back_populates="accounts")


class FxRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "source_currency", name="uq_workspace_fx_currency"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rate_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)


class ImportRun(Base):
    __tablename__ = "import_runs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "profile_id",
            "file_sha256",
            name="uq_workspace_import_file",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_duplicate_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ImportIssue(Base):
    __tablename__ = "import_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "import_run_id", "source_row_number", name="uq_import_balance_row"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_as_of: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "account_id",
            "external_id",
            name="uq_workspace_account_transaction",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("import_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(140), nullable=False)
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExpectedCashFlow(Base):
    __tablename__ = "expected_cash_flows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiquidityRule(Base):
    __tablename__ = "liquidity_rules"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "entity_id", name="uq_workspace_entity_liquidity_rule"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    minimum_balance_base: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "input_fingerprint", name="uq_workspace_forecast_input"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    opening_cash: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ForecastPoint(Base):
    __tablename__ = "forecast_points"
    __table_args__ = (
        UniqueConstraint(
            "forecast_run_id",
            "scope",
            "entity_key",
            "forecast_date",
            name="uq_forecast_scope_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    forecast_run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
