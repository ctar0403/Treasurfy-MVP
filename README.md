# TreasurFy MVP

TreasurFy is a treasury workspace for growth-stage companies that manage
multiple entities, banks, accounts, and currencies.

The MVP answers five practical questions:

1. How much cash do we have now?
2. What will our cash position be in 30, 60, and 90 days?
3. Which entities are cash-rich or cash-poor?
4. Where are our liquidity risks?
5. Which payments need preparation or approval?

## How it works

```text
Bank/ERP files
    -> reusable import profiles
    -> normalized accounts, balances, transactions, and expected cash flows
    -> cash position, forecast, and liquidity calculations
    -> dashboard and grounded daily treasury brief

Payment draft
    -> canonical payment model
    -> reusable payment profile and deterministic validation
    -> maker/checker approval
    -> illustrative ISO 20022 XML export
```

Bank-specific mapping and payment knowledge is stored in versioned profiles so
it can be reused for later customers instead of rebuilt during every
implementation.

The January demonstration will use synthetic or redacted files. It will not
connect to production banks or transmit money. Payment export does not mean a
bank has certified or accepted the file.

## MVP scope

- Workspace users with admin, preparer, approver, and viewer roles
- Legal entities, banks, accounts, currencies, and data freshness
- File-based balance and transaction imports
- Consolidated cash position with account/entity drill-down
- Explainable 30/60/90-day forecast
- Cash-rich/cash-poor ranking and minimum-cash alerts
- Payment preparation, validation, approval, audit, and XML export
- Read-only daily brief generated from calculated facts
- Reusable onboarding, import, and payment profiles

Not included in the MVP: real bank connectivity, payment transmission, full ERP
integration, automated reconciliation, ML forecasting, FX trading, debt
management, or autonomous AI actions.

## Delivery steps

1. Foundation: API, database, workspace isolation, seed data, tests
2. Onboarding and balance/transaction imports
3. Cash dashboard and currency conversion
4. Forecasting and liquidity alerts
5. Payment preparation, approval, and export
6. Daily brief, web experience, deployment, and hardening

Each step is delivered as a tested Git commit. The first target customer remains
a UK/US growth-stage SaaS, fintech, or technology company using GBP, USD, and
EUR. The first input is a documented CSV format; the first payment output is an
illustrative ISO 20022 `pain.001` file.

## Repository layout

```text
apps/api/   FastAPI application and tests
apps/web/   React and TypeScript treasury dashboard
infra/      Local and deployment configuration
```

## Current implementation

Step 1 is implemented in `apps/api`:

- FastAPI application and SQLite development database
- Workspace, membership/role, entity, bank-account, FX-rate, and audit models
- Synthetic demo data for three entities and six GBP/USD/EUR accounts
- Workspace access boundary using a temporary `X-User-ID` identity header
- Consolidated base-currency cash position with entity/account drill-down
- Balance and FX timestamps plus stale-account reporting
- Automated health, calculation, reconciliation, and isolation tests
- Versioned CSV balance/transaction imports with persisted run history
- Exact-file and transaction-level duplicate protection
- Partial imports with persisted row numbers and validation issues
- Responsive cash dashboard with entity and account drill-down
- Browser CSV upload, validation results, and import history
- Reproducible 30/60/90-day forecasts from dated expected cash flows
- Entity minimum-cash rules, rankings, and projected liquidity alerts

The identity header is only an MVP seam and will be replaced by managed login.
The demo FX rates are explicit synthetic inputs, not live market data.

## Run the API

From `apps/api` with Python 3.12 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m uvicorn treasurfy.main:app --reload
```

Open the API documentation at `http://127.0.0.1:8000/docs`.

The seeded cash-position request is:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/workspaces/workspace-demo/cash-position `
  -Headers @{ 'X-User-ID' = 'user-demo-admin' }
```

The first run creates `apps/api/treasurfy.db`. Remove it only when intentionally
resetting local synthetic data.

## Import bank data

The reusable profile `treasurfy-bank-csv` version `1.0.0` accepts UTF-8 CSV
files with these columns:

```text
record_type,account_id,occurred_at,amount,currency,transaction_id,description
```

- `record_type` is `BALANCE` or `TRANSACTION`.
- `occurred_at` is an ISO 8601 timestamp with a timezone.
- `currency` must match the configured account.
- `transaction_id` is required for transactions and provides duplicate
  protection.
- Valid rows are saved even if other rows fail; rejected rows are returned with
  their source line and reason.
- Uploading the exact same file again returns the original run without writing
  duplicate data.

A working file is available at `apps/api/samples/bank_data.csv`. Upload it with:

```powershell
curl.exe --noproxy "*" `
  -H "X-User-ID: user-demo-admin" `
  -F "file=@samples/bank_data.csv;type=text/csv" `
  http://127.0.0.1:8000/api/workspaces/workspace-demo/imports/bank-csv
```

Import history is available from:

```text
GET /api/workspaces/workspace-demo/imports
```

## Run the web dashboard

Keep the API running, then open a second PowerShell window:

```powershell
cd apps\web
npm.cmd install
npm.cmd run test
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. The dashboard uses the temporary demo identity and
workspace automatically. To point it at another API, set `VITE_API_URL` before
running or building the web application.

Create a production bundle with:

```powershell
npm.cmd run build
```

## Forecasting and liquidity

The forecast starts with the latest account balances, converts all values using
the workspace's explicit FX rates, and applies planned inflows and outflows on
their due dates. It stores a SHA-256 fingerprint of every balance, rate, flow,
rule, and forecast date used. Running it again with unchanged inputs returns the
same immutable run.

```text
POST /api/workspaces/workspace-demo/forecasts
GET  /api/workspaces/workspace-demo/expected-cash-flows
POST /api/workspaces/workspace-demo/expected-cash-flows
```

The seeded data includes seven expected flows and minimum-cash rules for each
entity. One European entity intentionally crosses its threshold so the alert
workflow is visible in the dashboard's forecast chart, horizon cards, ranked
entity positions, expected-flow list, and liquidity warning.

The next delivery step is payment preparation, profile validation,
maker/checker approval, audit history, and illustrative ISO 20022 export.
