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
compose.yaml   Containerized local deployment
```

## Current implementation

All six MVP delivery steps are implemented across `apps/api` and `apps/web`:

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
- Versioned payment profiles and deterministic draft validation
- Separate payment maker/checker identities and approval enforcement
- Payment audit history and repeatable illustrative ISO 20022 XML export
- Responsive payment preparation and approval workspace
- Evidence-linked daily treasury brief with prioritized actions
- Immutable brief runs that are reused while their source inputs remain unchanged
- API safety headers, response request IDs, container health checks, and non-root images

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

## Temporary Cloudflare demo from this PC

For a private demo without paying for a server, this PC can serve the app
through Cloudflare Tunnel. This is a temporary setup: the PC and both app
processes must stay on and connected to the internet. Use synthetic data only.
The MVP has demo identities rather than real login, so protect the hostname
with a Cloudflare Access email allowlist before publishing the tunnel route.

1. In Cloudflare Zero Trust, create a self-hosted Access application for the
   chosen demo hostname and allow only the demo attendees' email addresses.
2. In Cloudflare Networking > Tunnels, create a tunnel and add a published
   application route for that hostname to `http://127.0.0.1:5173`. Keep the
   tunnel token private; run the install/run command Cloudflare gives you on
   this PC.
3. Start the API in one PowerShell window:

   ```powershell
   cd apps\api
   .\.venv\Scripts\python.exe -m uvicorn treasurfy.main:app --host 127.0.0.1 --port 8000
   ```

4. Build and serve the web app in another PowerShell window. Replace the
   hostname with the exact subdomain configured in Cloudflare:

   ```powershell
   cd apps\web
   $env:TREASURFY_DEMO_HOST = "demo.example.com"
   npm.cmd run build
   npm.cmd run preview
   ```

The preview server proxies `/api` to the local API, so browsers use the same
hostname for both. For an always-on demo, move the existing Docker Compose
deployment to an always-on host and point a Cloudflare Tunnel there instead.

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

## Payment preparation and approval

The seeded payment profile accepts GBP, USD, and EUR credit transfers up to
1,000,000 in the payment currency. Validation checks workspace ownership,
entity/account alignment, source-account currency, profile currency and amount
limits, execution date, beneficiary country, and account identifier format.

The web demonstration uses separate synthetic identities: Priya is the maker
and Alex is the checker. The API rejects self-approval even when an admin has
both permissions. A seeded EUR payment is ready for approval so the workflow
can be tested immediately.

```text
GET  /api/workspaces/workspace-demo/payment-profiles
GET  /api/workspaces/workspace-demo/payments
POST /api/workspaces/workspace-demo/payments
POST /api/workspaces/workspace-demo/payments/{payment_id}/submit
POST /api/workspaces/workspace-demo/payments/{payment_id}/approve
POST /api/workspaces/workspace-demo/payments/{payment_id}/reject
GET  /api/workspaces/workspace-demo/payments/{payment_id}/audit-events
GET  /api/workspaces/workspace-demo/payments/{payment_id}/iso20022
```

XML export is available only after approval. Repeated export returns the same
content and SHA-256 digest. The generated `pain.001.001.03` document is an
illustrative interoperability artifact: it is not certified by a bank and is
never transmitted.

## Daily treasury brief

The brief is calculated from the same cash position, forecast, liquidity rules,
and payment states shown elsewhere in the dashboard. Every exception links back
to concrete evidence identifiers. It does not use an LLM to invent or reinterpret
financial values. A SHA-256 input fingerprint makes repeated generation
reproducible and invalidates the brief when a source balance, flow, rule, or
payment state changes.

```text
POST /api/workspaces/workspace-demo/daily-briefs
```

The dashboard presents the current cash and forecast metrics, liquidity and data
quality exceptions, and an action queue ordered by operational priority.

## Run with containers

Docker Compose builds a non-root API container and a static web container with a
same-origin API proxy. SQLite data is stored in the named `treasurfy-data` volume.

```powershell
docker compose up --build
```

Open `http://127.0.0.1:5173`. The API remains available directly at
`http://127.0.0.1:8000`, including health checks at `/api/health`.

Stop the containers with:

```powershell
docker compose down
```

The MVP is now feature-complete for a synthetic-data pilot. Production rollout
still requires managed authentication, secrets management, database migrations,
real bank certification/connectivity, monitoring, backups, and an external
security review.
