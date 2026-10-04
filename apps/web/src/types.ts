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
