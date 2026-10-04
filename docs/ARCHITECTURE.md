# Architecture

## Design principles

1. Deterministic financial calculations; AI only explains computed results.
2. Every financial value has currency, source, effective date, and import/run
   provenance.
3. Tenant isolation is enforced in services and verified in tests.
4. Payment preparation and approval are separate actions with an immutable
   audit history.
5. Bank-specific knowledge lives in versioned profiles and adapters, not in UI
   conditionals.
6. External integrations are replaceable boundaries. The MVP can use files and
   sandboxes without redesigning the core domain.
7. Prefer a modular monolith until real scale or reliability evidence requires
   separate services.

## Proposed stack

- Web: React, TypeScript, Vite, TanStack Query, React Hook Form
- API: Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic
- Database: PostgreSQL
- Jobs: database-backed job records plus a small worker/cron process; add Redis
  only when retries or load justify it
- Tests: Pytest, Vitest, Playwright
- Local environment: Docker Compose
- Initial hosting target: managed PostgreSQL plus separate web/API services and
  a scheduled job runner
- Observability: structured logs, request IDs, health checks, error monitoring,
  and import/job metrics

Specific dependency versions will be selected and locked when implementation
begins. The first prototype's dependencies should not be copied blindly into a
new production-oriented environment.

## System view

```text
Browser
  |
  v
React web app
  |
  v
FastAPI modular monolith
  |
  +-- Identity and workspace access
  +-- Onboarding and profile selection
  +-- Imports and normalization
  +-- Cash position and FX conversion
  +-- Forecast and liquidity rules
  +-- Payment preparation and approval
  +-- Daily brief generation
  +-- Audit log
  |
  +--> PostgreSQL
  +--> Object storage (original import/export artifacts)
  +--> Optional AI provider (aggregate, read-only facts only)
  +--> Future bank/ERP adapters
```

## Domain modules

| Module | Responsibilities |
|---|---|
| Identity | Users, memberships, roles, workspace scoping |
| Onboarding | Entities, banks, accounts, profile selection, readiness |
| Imports | File intake, parsing, validation, idempotency, provenance |
| Cash | Balance snapshots, transactions, FX rates, consolidation |
| Forecast | Expected flows, recurring rules, scenarios, forecast points |
| Liquidity | Thresholds, rankings, projected breaches, explanations |
| Payments | Drafts, validation, approval state machine, XML export |
| Profiles | Versioned statement/payment mappings and promotion status |
| Briefs | Computed fact package, summary generation, citations/fallback |
| Audit | Append-only records for security- and finance-relevant actions |

## Core records

- `workspaces`, `users`, `memberships`
- `entities`, `banks`, `bank_accounts`
- `import_profiles`, `import_profile_versions`, `import_runs`
- `balance_snapshots`, `transactions`
- `fx_rates`
- `expected_cash_flows`, `recurrence_rules`
- `forecast_runs`, `forecast_points`, `liquidity_rules`, `liquidity_alerts`
- `payment_profiles`, `payment_profile_versions`
- `payments`, `payment_approvals`, `payment_artifacts`
- `daily_briefs`, `audit_events`

All tenant-owned records carry `workspace_id`. Monetary amounts use decimal
types, never binary floating point. Timestamps are stored in UTC and rendered in
the user's chosen timezone.

## Import path

```text
Original file
  -> profile-specific parser
  -> canonical rows
  -> structural validation
  -> duplicate/idempotency check
  -> transaction + balance write in one database transaction
  -> recalculation request
  -> import report with accepted and rejected rows
```

Original files and generated exports are retained outside the database with a
checksum and access-controlled metadata record. No import silently overwrites
prior history.

## Forecast calculation

For each account and date:

```text
closing balance = previous closing balance
                + expected inflows
                - expected outflows
                - approved/scheduled payments not already represented
```

Aggregation occurs after per-account calculation. Base-currency totals identify
the exact FX rate and as-of time used. A forecast run is immutable so a user can
reproduce what they saw in a prior brief.

## Payment state machine

```text
DRAFT -> VALIDATED -> PENDING_APPROVAL -> APPROVED -> EXPORTED
   |          |              |               |
   +--------> REJECTED <------+---------------+
```

- Editing an approved or rejected payment creates a new draft revision.
- The actor who submits a payment cannot approve that revision.
- Export requires an approved revision and a recorded payment-profile version.
- There is no `SENT` state in this MVP.

## AI boundary

The brief service receives a structured fact package such as:

```json
{
  "cash_total": {"amount": "2400000.00", "currency": "GBP"},
  "forecast_30d": {"amount": "2050000.00", "currency": "GBP"},
  "alerts": [{"code": "ENTITY_BELOW_THRESHOLD", "entity_id": "..."}],
  "pending_approvals": 3,
  "source_run_ids": ["..."]
}
```

An AI provider may turn these facts into prose, but may not calculate or change
the facts. Output is schema-validated, stored with its model/prompt version, and
rendered with links to the source run IDs. Failure uses a deterministic template.

## Security baseline

- Managed OIDC authentication; no home-grown password storage
- Role checks for every write and tenant check for every read
- CSRF/cookie protection or short-lived bearer-token controls, depending on the
  chosen identity provider
- Encryption in transit and at rest through hosting providers
- Secrets only in deployment secret stores, never in Git
- Sensitive-value redaction in logs and error reporting
- File type/size limits and malware scanning decision before customer uploads
- Append-only audit events with actor, action, target, time, and request ID
- Idempotency keys for imports, payment submission, approval, and export
- Backups and a restore drill before any real customer data is accepted

This baseline is necessary but does not make the MVP production-banking ready.
A separate security and regulatory review is required before real credentials,
bank connectivity, or money movement enter scope.
