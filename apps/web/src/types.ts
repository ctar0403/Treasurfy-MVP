export type AccountCash = {
  account_id: string;
  account_name: string;
  masked_account_number: string;
  bank_name: string;
  entity_id: string;
  entity_name: string;
  currency: string;
  native_balance: string;
  fx_rate_to_base: string;
  base_currency_balance: string;
  balance_as_of: string;
  freshness: "fresh" | "stale";
};

export type EntityCash = {
  entity_id: string;
  entity_name: string;
  country_code: string;
  base_currency_balance: string;
  account_count: number;
};

export type CashPosition = {
  workspace_id: string;
  workspace_name: string;
  base_currency: string;
  total_cash: string;
  account_count: number;
  entity_count: number;
  stale_account_count: number;
  oldest_balance_as_of: string | null;
  fx_rate_as_of: string | null;
  accounts: AccountCash[];
  entities: EntityCash[];
};

export type ImportIssue = {
  row_number: number;
  code: string;
  message: string;
};

export type ImportRun = {
  import_run_id: string;
  profile_id: string;
  profile_version: string;
  file_name: string;
  file_sha256: string;
  status: "completed" | "partial" | "rejected" | "processing";
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  skipped_duplicate_rows: number;
  duplicate_file: boolean;
  created_at: string;
  completed_at: string | null;
  issues: ImportIssue[];
};

export type ExpectedCashFlow = {
  id: string;
  entity_id: string;
  entity_name: string;
  account_id: string;
  account_name: string;
  name: string;
  direction: "inflow" | "outflow";
  amount: string;
  currency: string;
  base_currency_amount: string;
  due_date: string;
  source: string;
  status: string;
};

export type ForecastPoint = {
  date: string;
  total_cash: string;
};

export type ForecastHorizon = {
  days: number;
  date: string;
  total_cash: string;
  change_from_opening: string;
};

export type EntityForecast = {
  entity_id: string;
  entity_name: string;
  opening_cash: string;
  projected_30_days: string;
  projected_60_days: string;
  projected_90_days: string;
  minimum_balance: string | null;
  status: "healthy" | "at_risk";
  first_breach_date: string | null;
  rank_at_30_days: number;
};

export type LiquidityAlert = {
  entity_id: string;
  entity_name: string;
  code: string;
  severity: string;
  breach_date: string;
  projected_balance: string;
  minimum_balance: string;
  message: string;
};

export type Forecast = {
  forecast_run_id: string;
  reused_run: boolean;
  as_of_date: string;
  horizon_days: number;
  base_currency: string;
  opening_cash: string;
  input_fingerprint: string;
  created_at: string;
  horizons: ForecastHorizon[];
  points: ForecastPoint[];
  entities: EntityForecast[];
  alerts: LiquidityAlert[];
  expected_flows: ExpectedCashFlow[];
};

export type PaymentProfile = {
  id: string;
  name: string;
  version: string;
  message_type: string;
  allowed_currencies: string[];
  maximum_amount: string;
};

export type Payment = {
  id: string;
  entity_id: string;
  entity_name: string;
  source_account_id: string;
  source_account_name: string;
  payment_profile_id: string;
  payment_profile_name: string;
  profile_version: string;
  beneficiary_name: string;
  beneficiary_account: string;
  beneficiary_country_code: string;
  amount: string;
  currency: string;
  requested_execution_date: string;
  reference: string;
  status: "draft" | "pending_approval" | "approved" | "rejected";
  validation_status: "pending" | "passed" | "failed";
  validation_errors: string[];
  created_by_user_id: string;
  created_by_name: string;
  submitted_by_user_id: string | null;
  decided_by_user_id: string | null;
  created_at: string;
  submitted_at: string | null;
  decided_at: string | null;
  can_export: boolean;
};

export type PaymentCreateInput = {
  entity_id: string;
  source_account_id: string;
  payment_profile_id: string;
  beneficiary_name: string;
  beneficiary_account: string;
  beneficiary_country_code: string;
  amount: string;
  currency: string;
  requested_execution_date: string;
  reference: string;
};

export type PaymentAuditEvent = {
  id: string;
  action: string;
  actor_user_id: string | null;
  actor_name: string;
  detail: Record<string, unknown>;
  created_at: string;
};
