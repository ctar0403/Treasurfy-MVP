from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountCash(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    account_name: str
    masked_account_number: str
    bank_name: str
    entity_id: str
    entity_name: str
    currency: str
    native_balance: str
    fx_rate_to_base: str
    base_currency_balance: str
    balance_as_of: str
    freshness: str


class EntityCash(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    entity_name: str
    country_code: str
    base_currency_balance: str
    account_count: int


class CashPositionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    workspace_name: str
    base_currency: str
    total_cash: str
    account_count: int
    entity_count: int
    stale_account_count: int
    oldest_balance_as_of: str | None
    fx_rate_as_of: str | None
    accounts: list[AccountCash]
    entities: list[EntityCash]


class HealthResponse(BaseModel):
    status: str
    database: str


class ImportIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_number: int
    code: str
    message: str


class ImportRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    import_run_id: str
    profile_id: str
    profile_version: str
    file_name: str
    file_sha256: str
    status: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    skipped_duplicate_rows: int
    duplicate_file: bool
    created_at: str
    completed_at: str | None
    issues: list[ImportIssueResponse]


class ExpectedCashFlowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    account_id: str
    name: str = Field(min_length=1, max_length=200)
    direction: Literal["inflow", "outflow"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    due_date: date


class ExpectedCashFlowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    entity_id: str
    entity_name: str
    account_id: str
    account_name: str
    name: str
    direction: str
    amount: str
    currency: str
    base_currency_amount: str
    due_date: date
    source: str
    status: str


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: date | None = None
    horizon_days: Literal[90] = 90


class ForecastPointResponse(BaseModel):
    date: date
    total_cash: str


class ForecastHorizonResponse(BaseModel):
    days: int
    date: date
    total_cash: str
    change_from_opening: str


class EntityForecastResponse(BaseModel):
    entity_id: str
    entity_name: str
    opening_cash: str
    projected_30_days: str
    projected_60_days: str
    projected_90_days: str
    minimum_balance: str | None
    status: str
    first_breach_date: date | None
    rank_at_30_days: int


class LiquidityAlertResponse(BaseModel):
    entity_id: str
    entity_name: str
    code: str
    severity: str
    breach_date: date
    projected_balance: str
    minimum_balance: str
    message: str


class ForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_run_id: str
    reused_run: bool
    as_of_date: date
    horizon_days: int
    base_currency: str
    opening_cash: str
    input_fingerprint: str
    created_at: str
    horizons: list[ForecastHorizonResponse]
    points: list[ForecastPointResponse]
    entities: list[EntityForecastResponse]
    alerts: list[LiquidityAlertResponse]
    expected_flows: list[ExpectedCashFlowResponse]


class PaymentProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    version: str
    message_type: str
    allowed_currencies: list[str]
    maximum_amount: str


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    source_account_id: str
    payment_profile_id: str
    beneficiary_name: str = Field(min_length=1, max_length=140)
    beneficiary_account: str = Field(min_length=5, max_length=80)
    beneficiary_country_code: str = Field(min_length=2, max_length=2)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    requested_execution_date: date
    reference: str = Field(min_length=1, max_length=140)


class PaymentDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str = Field(default="", max_length=500)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    entity_id: str
    entity_name: str
    source_account_id: str
    source_account_name: str
    payment_profile_id: str
    payment_profile_name: str
    profile_version: str
    beneficiary_name: str
    beneficiary_account: str
    beneficiary_country_code: str
    amount: str
    currency: str
    requested_execution_date: date
    reference: str
    status: str
    validation_status: str
    validation_errors: list[str]
    created_by_user_id: str
    created_by_name: str
    submitted_by_user_id: str | None
    decided_by_user_id: str | None
    created_at: str
    submitted_at: str | None
    decided_at: str | None
    can_export: bool


class PaymentAuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    action: str
    actor_user_id: str | None
    actor_name: str
    detail: dict[str, object]
    created_at: str


class DailyBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: date | None = None


class DailyBriefMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: str
    currency: str | None
    context: str
    tone: Literal["neutral", "positive", "warning", "critical"]


class DailyBriefHighlight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["info", "warning", "critical"]
    title: str
    detail: str
    evidence: list[str]


class DailyBriefAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Literal["low", "medium", "high", "critical"]
    title: str
    detail: str
    target_type: str
    target_id: str


class DailyBriefResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_brief_run_id: str
    reused_run: bool
    as_of_date: date
    generated_at: str
    base_currency: str
    headline: str
    summary: str
    metrics: list[DailyBriefMetric]
    highlights: list[DailyBriefHighlight]
    actions: list[DailyBriefAction]
    evidence: list[str]
    input_fingerprint: str
