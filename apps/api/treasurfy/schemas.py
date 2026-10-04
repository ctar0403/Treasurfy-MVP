from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
