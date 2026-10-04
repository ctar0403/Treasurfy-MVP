import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { CashPosition, ImportRun } from "./types";

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
      .mockResolvedValueOnce(jsonResponse([]));

    render(<App />);

    expect(await screen.findByText("£2,191,800")).toBeInTheDocument();
    expect(screen.getAllByText("Northstar UK Ltd")).toHaveLength(2);
    expect(screen.getByText("HSBC")).toBeInTheDocument();
    expect(screen.getByText("1 stale")).toBeInTheDocument();
    expect(screen.getByText(/No files imported yet/)).toBeInTheDocument();
  });

  it("uploads a CSV and refreshes the dashboard", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(cashPosition))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(importRun))
      .mockResolvedValueOnce(jsonResponse(cashPosition))
      .mockResolvedValueOnce(jsonResponse([importRun]));

    render(<App />);
    await screen.findByText("£2,191,800");

    const file = new File(["record_type,account_id"], "balances.csv", {
      type: "text/csv",
    });
    fireEvent.change(screen.getByLabelText(/Choose a CSV file/), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import selected file" }));

    expect(await screen.findByText("2 accepted · 0 rejected · 0 duplicates skipped"))
      .toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(5));
    expect(screen.getByText("balances.csv")).toBeInTheDocument();
  });
});
