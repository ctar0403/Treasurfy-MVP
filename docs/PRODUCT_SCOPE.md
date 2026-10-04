# Product scope

## Product statement

TreasurFy helps finance teams at growth-stage and mid-market SaaS, fintech, and
technology companies understand cash across entities and prepare controlled
payments without a long traditional treasury implementation.

The first market is companies scaling internationally that have a finance team
of roughly 3–20 people and still rely on spreadsheets plus separate bank
portals.

## Product promise

> Treasury visibility and payment preparation live in days, not months, once
> the customer has the required bank access, data, and entitlements.

This promise deliberately separates work controlled by TreasurFy from bank- and
customer-controlled prerequisites.

## Primary users

- Finance leader: needs consolidated cash, forecast, risks, and concise daily
  answers.
- Treasury or finance operator: imports data, maintains assumptions, prepares
  payments, and resolves validation errors.
- Payment approver: reviews and approves or rejects prepared payments.
- Read-only stakeholder: views dashboards and reports without changing data.

## MVP workflows

### 1. Guided workspace onboarding

- Create the company workspace and base currency.
- Add legal entities, banks, accounts, currencies, and opening balances.
- Select reusable statement-import and payment profiles.
- Show what TreasurFy has configured and what still requires customer or bank
  action.
- Import a supplied CSV or CAMT.053-style file and show row-level errors.

### 2. Current cash position

- Show balances by bank, account, currency, entity, and country.
- Show native-currency values and a base-currency equivalent using an explicit
  FX rate and as-of time.
- Show data freshness and incomplete or failed imports.
- Drill from a consolidated total into the contributing accounts.

### 3. 30/60/90-day forecast

- Start from the latest trusted account balances.
- Add scheduled payments, manual inflows/outflows, and simple recurring items.
- Produce daily forecast points and 30/60/90-day summaries.
- Let a user change assumptions and compare a base scenario with one alternative.
- Display inputs and calculation time so the forecast is explainable.

The first forecast is deterministic. It is not an ML prediction and must never
invent expected cash flows.

### 4. Entity liquidity and risk

- Define minimum-cash thresholds per account or entity.
- Rank cash-rich and cash-poor entities in base currency.
- Flag projected threshold breaches and unusually stale data.
- Explain every alert using the balances, flows, and rule that produced it.

### 5. Payments

- Create or import a draft payment using one canonical payment model.
- Validate the payment against a versioned payment profile.
- Support preparer and approver roles with no self-approval.
- Record creation, edits, approval, rejection, and export in an audit trail.
- Export an illustrative `pain.001` XML file after approval.
- Clearly label the workflow as export-only; no bank transmission occurs.

The existing profile registry, deterministic validator, and XML renderer are
the starting point for this workflow after they are extracted and adapted to
persistent, tenant-scoped data.

### 6. Daily treasury brief

- Compute the facts first: total cash, material movement, 30/60/90 outlook,
  threshold breaches, stale feeds, and payments awaiting action.
- Generate a short morning summary from only those computed facts.
- Link every statement to its supporting dashboard item.
- Provide a deterministic template fallback if the AI provider is unavailable.
- Keep the assistant read-only; it cannot create, approve, export, or transmit a
  payment.

## January 2027 demo acceptance criteria

A release candidate is demo-ready when it can:

- represent at least 2 entities, 3 banks, 6 accounts, and GBP/USD/EUR;
- import a clean file and report invalid rows without corrupting valid history;
- reconcile dashboard totals to the latest imported balances;
- answer the four cash and liquidity questions in under 60 seconds;
- calculate reproducible 30/60/90 forecasts from visible inputs;
- identify at least one cash-poor entity and one projected threshold breach;
- prepare, validate, approve, and export one payment with a complete audit trail;
- prevent a preparer from approving their own payment;
- produce a grounded daily brief and a fallback brief;
- show profile version, data freshness, currency-rate timestamp, and onboarding
  status;
- enforce workspace isolation in automated tests;
- complete the critical browser flow in an end-to-end test;
- display that the product does not transmit money or represent bank
  certification.

## Explicit non-goals for this release

- Production bank APIs, SFTP, EBICS, SWIFT, or open-banking credentials
- Sending money or claiming bank certification
- Automated bank reconciliation or general-ledger posting
- Full ERP integration or historical ERP migration
- Probabilistic/ML cash forecasting
- FX execution, debt management, hedging, or investment management
- Bulk payroll, direct debits, sanctions screening, or fraud detection
- Custom mobile applications
- Supporting every bank, country, file format, or payment rail
- Autonomous AI actions

## MVP success measures

Product success is customer evidence, not feature count:

- 4–5 design partners agree to a January demonstration.
- At least 3 complete the core demo and provide structured feedback.
- At least 2 agree to a follow-up using their redacted or synthetic data.
- At least 1 expresses a concrete pilot or willingness-to-pay condition.
- Median time to configure the demo dataset is recorded and improves over the
  first five onboardings.
- The team records where onboarding still requires manual work; repeated work
  becomes the next automation backlog.
