import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type {
  CashPosition,
  DailyBrief,
  Forecast,
  ImportRun,
  Payment,
  PaymentProfile,
} from "./types";

const cashPosition: CashPosition = {
  workspace_id: "workspace-demo",
  workspace_name: "Northstar Software Group",
  base_currency: "GBP",
  total_cash: "2191800.00",
  account_count: 2,
  entity_count: 2,
  stale_account_count: 1,
  oldest_balance_as_of: "2026-10-03T08:00:00Z",
  fx_rate_as_of: "2026-10-04T08:00:00Z",
  accounts: [
    {
      account_id: "account-hsbc-gbp",
      account_name: "UK Operating",
      masked_account_number: "****5432",
      bank_name: "HSBC",
      entity_id: "entity-uk",
      entity_name: "Northstar UK Ltd",
      currency: "GBP",
      native_balance: "850000.00",
      fx_rate_to_base: "1.00000000",
      base_currency_balance: "850000.00",
      balance_as_of: "2026-10-04T08:00:00Z",
      freshness: "fresh",
    },
  ],
  entities: [
    {
      entity_id: "entity-uk",
      entity_name: "Northstar UK Ltd",
      country_code: "GB",
      base_currency_balance: "1211200.00",
      account_count: 2,
    },
  ],
};

const importRun: ImportRun = {
  import_run_id: "run-1",
  profile_id: "treasurfy-bank-csv",
  profile_version: "1.0.0",
  file_name: "balances.csv",
  file_sha256: "abc",
  status: "completed",
  total_rows: 2,
  accepted_rows: 2,
  rejected_rows: 0,
  skipped_duplicate_rows: 0,
  duplicate_file: false,
  created_at: "2026-10-04T08:00:00Z",
  completed_at: "2026-10-04T08:00:01Z",
  issues: [],
};

const forecast: Forecast = {
  forecast_run_id: "forecast-1",
  reused_run: false,
  as_of_date: "2026-10-04",
  horizon_days: 90,
  base_currency: "GBP",
  opening_cash: "2191800.00",
  input_fingerprint: "fingerprint",
  created_at: "2026-10-04T08:00:00Z",
  horizons: [
    { days: 30, date: "2026-11-03", total_cash: "2118200.00", change_from_opening: "-73600.00" },
    { days: 60, date: "2026-12-03", total_cash: "2153000.00", change_from_opening: "-38800.00" },
    { days: 90, date: "2027-01-02", total_cash: "2013000.00", change_from_opening: "-178800.00" },
  ],
  points: Array.from({ length: 91 }, (_, index) => ({
    date: new Date(Date.UTC(2026, 9, 4 + index)).toISOString().slice(0, 10),
    total_cash: index < 30 ? "2191800.00" : "2118200.00",
  })),
  entities: [
    {
      entity_id: "entity-eu",
      entity_name: "Northstar Europe GmbH",
      opening_cash: "338800.00",
      projected_30_days: "115200.00",
      projected_60_days: "218400.00",
      projected_90_days: "218400.00",
      minimum_balance: "150000.00",
      status: "at_risk",
      first_breach_date: "2026-10-24",
      rank_at_30_days: 3,
    },
  ],
  alerts: [
    {
      entity_id: "entity-eu",
      entity_name: "Northstar Europe GmbH",
      code: "ENTITY_BELOW_MINIMUM",
      severity: "high",
      breach_date: "2026-10-24",
      projected_balance: "115200.00",
      minimum_balance: "150000.00",
      message: "Northstar Europe GmbH is projected below its minimum cash threshold.",
    },
  ],
  expected_flows: [
    {
      id: "flow-1",
      entity_id: "entity-eu",
      entity_name: "Northstar Europe GmbH",
      account_id: "account-eu",
      account_name: "EU Operating",
      name: "EU payroll and taxes",
      direction: "outflow",
      amount: "260000.00",
      currency: "EUR",
      base_currency_amount: "-223600.00",
      due_date: "2026-10-24",
      source: "demo",
      status: "planned",
    },
  ],
};

const paymentProfile: PaymentProfile = {
  id: "payment-profile-pain001-demo",
  name: "Illustrative ISO 20022 credit transfer",
  version: "1.0.0",
  message_type: "pain.001.001.03-demo",
  allowed_currencies: ["GBP", "USD", "EUR"],
  maximum_amount: "1000000.00",
};

const pendingPayment: Payment = {
  id: "payment-demo-cloud",
  entity_id: "entity-eu",
  entity_name: "Northstar Europe GmbH",
  source_account_id: "account-deutsche-eur",
  source_account_name: "EU Operating",
  payment_profile_id: paymentProfile.id,
  payment_profile_name: paymentProfile.name,
  profile_version: "1.0.0",
  beneficiary_name: "Atlas Cloud Services GmbH",
  beneficiary_account: "DE89370400440532013000",
  beneficiary_country_code: "DE",
  amount: "48000.00",
  currency: "EUR",
  requested_execution_date: "2026-10-08",
  reference: "INV-2026-1042",
  status: "pending_approval",
  validation_status: "passed",
  validation_errors: [],
  created_by_user_id: "user-demo-preparer",
  created_by_name: "Priya Payment Maker",
  submitted_by_user_id: "user-demo-preparer",
  decided_by_user_id: null,
  created_at: "2026-10-04T08:00:00Z",
  submitted_at: "2026-10-04T08:00:00Z",
  decided_at: null,
  can_export: false,
};

const dailyBrief: DailyBrief = {
  daily_brief_run_id: "brief-1",
  reused_run: false,
  as_of_date: "2026-10-04",
  generated_at: "2026-10-04T08:00:00Z",
  base_currency: "GBP",
  headline: "1 liquidity risk and 1 payment approval need attention",
  summary: "Available cash and forecasts are derived from current treasury inputs.",
  metrics: [
    {
      key: "total_cash",
      label: "Cash available",
      value: "2191800.00",
      currency: "GBP",
      context: "Across 3 entities and 6 accounts",
      tone: "neutral",
    },
    {
      key: "cash_30_days",
      label: "30-day forecast",
      value: "2118200.00",
      currency: "GBP",
      context: "Down 73600.00 from today's position",
      tone: "warning",
    },
    {
      key: "pending_approvals",
      label: "Pending approvals",
      value: "1",
      currency: null,
      context: "Payments requiring a separate checker",
      tone: "warning",
    },
  ],
  highlights: [
    {
      severity: "critical",
      title: "Liquidity threshold at Northstar Europe GmbH",
      detail: "Projected GBP 115200.00 below its configured minimum.",
      evidence: ["forecast:forecast-1", "entity:entity-eu"],
    },
  ],
  actions: [
    {
      priority: "critical",
      title: "Resolve projected shortfall at Northstar Europe GmbH",
      detail: "Review dated inflows and outflows.",
      target_type: "entity",
      target_id: "entity-eu",
    },
  ],
  evidence: ["cash-position:workspace-demo", "forecast:forecast-1", "payment:payment-demo-cloud"],
  input_fingerprint: "brief-fingerprint",
};

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("TreasurFy dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows consolidated cash, freshness, entities, and accounts", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(cashPosition))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(forecast))
      .mockResolvedValueOnce(jsonResponse([paymentProfile]))
      .mockResolvedValueOnce(jsonResponse([pendingPayment]))
      .mockResolvedValueOnce(jsonResponse(dailyBrief));

    render(<App />);

    expect((await screen.findAllByText("£2,191,800")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Northstar UK Ltd")).toHaveLength(2);
    expect(screen.getByText("HSBC")).toBeInTheDocument();
    expect(screen.getByText("1 stale")).toBeInTheDocument();
    expect(screen.getAllByText("£2,118,200").length).toBeGreaterThan(0);
    expect(screen.getByText("Liquidity risks")).toBeInTheDocument();
    expect(screen.getByText("Payment workspace")).toBeInTheDocument();
    expect(screen.getByText(dailyBrief.headline)).toBeInTheDocument();
    expect(screen.getByText("Today's actions")).toBeInTheDocument();
    expect(screen.getByText("Atlas Cloud Services GmbH")).toBeInTheDocument();
    expect(screen.getByText(/No files imported yet/)).toBeInTheDocument();
  });

  it("uploads a CSV and refreshes the dashboard", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(cashPosition))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(forecast))
      .mockResolvedValueOnce(jsonResponse([paymentProfile]))
      .mockResolvedValueOnce(jsonResponse([pendingPayment]))
      .mockResolvedValueOnce(jsonResponse(dailyBrief))
      .mockResolvedValueOnce(jsonResponse(importRun))
      .mockResolvedValueOnce(jsonResponse(cashPosition))
      .mockResolvedValueOnce(jsonResponse([importRun]))
      .mockResolvedValueOnce(jsonResponse({ ...forecast, reused_run: true }))
      .mockResolvedValueOnce(jsonResponse([paymentProfile]))
      .mockResolvedValueOnce(jsonResponse([pendingPayment]))
      .mockResolvedValueOnce(jsonResponse({ ...dailyBrief, reused_run: true }));

    render(<App />);
    await screen.findAllByText("£2,191,800");

    const file = new File(["record_type,account_id"], "balances.csv", {
      type: "text/csv",
    });
    fireEvent.change(screen.getByLabelText(/Choose a CSV file/), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import selected file" }));

    expect(await screen.findByText("2 accepted · 0 rejected · 0 duplicates skipped"))
      .toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(13));
    expect(screen.getByText("balances.csv")).toBeInTheDocument();
  });

  it("approves a pending payment with the checker identity", async () => {
    const approvedPayment: Payment = {
      ...pendingPayment,
      status: "approved",
      decided_by_user_id: "user-demo-approver",
      decided_at: "2026-10-04T09:00:00Z",
      can_export: true,
    };
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(cashPosition))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(forecast))
      .mockResolvedValueOnce(jsonResponse([paymentProfile]))
      .mockResolvedValueOnce(jsonResponse([pendingPayment]))
      .mockResolvedValueOnce(jsonResponse(dailyBrief))
      .mockResolvedValueOnce(jsonResponse(approvedPayment))
      .mockResolvedValueOnce(jsonResponse([approvedPayment]))
      .mockResolvedValueOnce(jsonResponse({
        ...dailyBrief,
        headline: "1 liquidity risk and 0 payment approvals need attention",
      }));

    render(<App />);
    await screen.findByText("Atlas Cloud Services GmbH");
    fireEvent.click(screen.getByRole("button", { name: "Approve as checker" }));

    expect(await screen.findByText("Payment approved by the demo checker.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download XML" })).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(9));
    expect(vi.mocked(fetch).mock.calls[6][1]?.headers).toEqual({
      "X-User-ID": "user-demo-approver",
      "Content-Type": "application/json",
    });
  });
});
