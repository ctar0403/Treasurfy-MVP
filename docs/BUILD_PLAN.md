# Build plan

## Target

Deliver a stable customer-demonstration release by **5 January 2027**, with the
final two weeks of December reserved for fixes and holiday/calendar risk. The
plan starts on **5 October 2026**.

The schedule assumes one technical lead with limited but dependable weekly
capacity and one product/commercial lead supplying domain decisions, sample
data, and design-partner access. Scope must be reduced if that capacity is not
available; dates should not be protected by silently lowering quality or
security gates.

## Default assumptions until customer evidence changes them

- Customer: growth-stage UK/US SaaS, fintech, or technology company
- Data: synthetic and redacted file imports, not live production credentials
- Statement input: TreasurFy CSV first; CAMT.053-style adapter second
- Payment output: ISO 20022 `pain.001` export, not bank transmission
- ERP: CSV export from NetSuite or an equivalent system
- Currencies: GBP, USD, and EUR
- Base currency: selected per workspace
- Forecast: deterministic known cash flows plus manual/recurring assumptions
- AI: read-only summary of computed facts with deterministic fallback

These are implementation defaults, not market claims.

## Delivery phases

### Phase 0 — scope lock and evidence pack (5–9 October)

Product/commercial lead:

- select one primary customer archetype and one named design-partner candidate;
- choose the first country, bank, payment rail, and ERP workflow;
- supply anonymized examples of a balance report, transaction export, payment
  input, payment output, and approval policy;
- define what “payments in the MVP” means and accept export-only as the safety
  boundary;
- rank the demo questions and approve the January demo script.

Technical lead:

- turn supplied files into canonical field mappings;
- create architecture decision records for identity, hosting, file storage, and
  the first adapters;
- extract only the reusable payment engine from the earlier prototype behind
  tests;
- create the product backlog and trace each story to an acceptance criterion.

Exit gate:

- the first user, dataset, import format, payment profile, and demo path are
  written down and accepted;
- no unresolved choice can alter the core data model for Sprint 1.

### Phase 1 — product foundation (10–23 October)

- Create the API/web workspace, locked dependencies, local containers, and CI.
- Add PostgreSQL migrations and seed data.
- Integrate managed authentication and workspace-scoped roles.
- Implement entities, banks, accounts, memberships, and audit events.
- Add a synthetic demo company with 2 entities, 3 banks, and 6 accounts.
- Establish unit, API integration, and one browser smoke test.

Exit gate:

- two test workspaces cannot access each other's records;
- a new developer can run migrations, seed data, tests, API, and web app from
  documented commands;
- CI runs on every branch update.

### Phase 2 — onboarding, imports, and cash position (24 October–6 November)

- Build the onboarding checklist and account configuration.
- Define the canonical statement/balance records.
- Implement TreasurFy CSV import with preview, row errors, and idempotency.
- Add the second adapter only if a real design-partner file is available.
- Store import provenance and data freshness.
- Build consolidated cash views with entity/bank/account/currency drill-down.
- Add explicit, timestamped FX rates for base-currency totals.

Exit gate:

- imported totals reconcile exactly to the sample source files;
- re-importing the same file does not duplicate balances or transactions;
- invalid rows are reported and do not silently corrupt accepted history;
- a user can answer “How much cash do we have now?” with visible freshness.

### Phase 3 — forecasting and liquidity (7–20 November)

- Implement manual and recurring expected cash flows.
- Add scheduled approved payments to the forecast without double-counting.
- Generate immutable daily forecast runs and 30/60/90 summaries.
- Add one alternative scenario with adjustable assumptions.
- Add account/entity minimum-cash rules and projected breach alerts.
- Build cash-rich/cash-poor ranking and explainable alert details.

Exit gate:

- forecast results reproduce from a fixed fixture;
- every value traces to an opening balance, expected flow, payment, or FX rate;
- threshold tests cover crossing, recovery, and missing/stale-data cases;
- the remaining three cash/liquidity questions can be answered from the UI.

### Phase 4 — reusable payment workflow (21 November–4 December)

- Adapt the earlier canonical payment model, registry, validators, and renderer.
- Persist versioned payment profiles and their evidence status.
- Add payment draft/edit/submit/reject/approve state transitions.
- Enforce preparer/approver separation and idempotent actions.
- Export approved illustrative `pain.001` XML and record its checksum.
- Add onboarding readiness for profile, credentials, UAT, and activation.
- Add complete audit coverage and authorization tests.

Exit gate:

- the same canonical instruction produces profile-specific validation results;
- a preparer cannot self-approve or export an unapproved payment;
- an approved payment exports deterministic, parseable XML;
- no endpoint or screen claims the file was sent to a bank.

### Phase 5 — daily brief and demo experience (5–12 December)

- Build the structured treasury fact package.
- Add deterministic brief generation first.
- Add one AI provider behind an interface, with redacted aggregate inputs,
  schema validation, timeout, and fallback.
- Link brief statements to forecast runs, alerts, and approval queues.
- Build the complete guided January demo path and resettable demo data.

Exit gate:

- AI failure never blocks dashboards or produces missing core facts;
- every numeric statement matches its source record;
- the demo can be reset and repeated without manual database edits.

### Phase 6 — hardening and release candidate (13–20 December)

- Run accessibility, responsive-layout, security, and authorization reviews.
- Add backup/restore and deployment runbooks.
- Test malformed/large imports, duplicate requests, failure recovery, and stale
  FX/data paths.
- Run browser tests for onboarding, dashboard, forecast, payment approval/export,
  and daily brief.
- Deploy a staging release with synthetic data and monitoring.
- Rehearse with the product lead and at least one friendly reviewer.

Exit gate:

- all product acceptance criteria pass;
- no critical/high security issue is open;
- backup restore and demo reset have been performed, not merely documented;
- release notes list known limitations and customer-data restrictions.

### Buffer and launch preparation (21 December–4 January)

- Fix release-candidate defects only; do not add net-new features.
- Prepare scripts and redacted datasets for each January design partner.
- Schedule demonstrations and assign note-taking/follow-up ownership.

### Customer demonstrations (from 5 January)

- Run 4–5 demonstrations using the same core script.
- Record task success, objections, requested integrations, willingness-to-pay
  conditions, and implementation friction.
- Hold a weekly evidence review and change the backlog only from repeated or
  commercially decisive findings.

## Work breakdown and ownership

| Workstream | Product/commercial lead | Technical lead | Joint decision |
|---|---|---|---|
| Customer | Recruit design partners; run interviews | Observe workflows; capture technical constraints | Target segment and pilot criteria |
| Product | Prioritize user problems; approve demo story | Define behavior and acceptance tests | MVP scope and cuts |
| Data | Obtain redacted/synthetic examples; explain fields | Canonicalize, validate, and secure them | First adapters |
| Payments | Document bank/customer steps and approval policy | Build profile, validation, approval, export | Export boundary and evidence status |
| Delivery | Maintain pipeline and demo calendar | Architecture, code, tests, deployment | Release readiness |
| Business | Positioning, pricing interviews, partnerships | Technical diligence and estimates | Pilot offer |

## Weekly operating rhythm

- Monday: written priorities, risks, and decisions needed.
- Midweek: asynchronous demo or short progress note.
- One 30-minute decision call: review working software and unblock only the
  highest-impact choices.
- Friday: update the acceptance checklist, risks, and customer evidence.
- Product decisions receive a response within two business days; otherwise the
  documented default assumption is used for the sprint and revisited later.

## Engineering quality gates

Every phase requires:

- migrations that apply from an empty database;
- unit tests for calculations and state machines;
- tenant isolation and role-authorization tests for every new resource;
- API contract tests and at least one happy-path browser test;
- structured logs without payment/account secrets;
- documentation for data sources and known limitations;
- a reviewable demonstration using synthetic data.

Before accepting real customer data, additionally require a threat model,
privacy/data-processing decision, retention policy, backup/restore evidence,
incident process, and legal/regulatory review.

## Scope-cut order if capacity is lower than planned

Cut in this order while preserving the core customer test:

1. Remove the second import adapter; keep one well-supported CSV profile.
2. Remove the alternative forecast scenario; keep the base 30/60/90 forecast.
3. Use only the deterministic daily brief; defer the external AI provider.
4. Reduce payment formats to one illustrative `pain.001` profile.
5. Reduce visual polish and secondary reports.

Do not cut tenant isolation, role separation, audit events, deterministic money
math, import idempotency, or the no-transmission boundary.

## Principal risks and responses

| Risk | Early signal | Response |
|---|---|---|
| Scope expands into a full TMS | New modules added without customer evidence | Enforce explicit non-goals and scope-cut order |
| No usable customer data | Phase 0 samples remain missing | Build one CSV path with synthetic fixtures; do not guess bank semantics |
| “Live in days” overpromises | External bank steps are counted as product time | Show separate TreasurFy/customer/bank clocks and onboarding states |
| Payments create false production confidence | Requests for send/connect language | Keep export-only state machine and prominent limitations |
| Forecast appears smarter than its inputs | Users cannot explain a number | Preserve immutable runs and input provenance |
| AI invents financial facts | Summary differs from dashboard | Constrain it to structured facts, validate output, and use fallback |
| Limited technical availability | Two consecutive gates slip | Cut scope immediately and protect the January core flow |
| Cross-tenant or approval flaw | Authorization test fails | Block release until corrected |

## Definition of done

The MVP is done for January demonstrations only when:

- every acceptance criterion in `PRODUCT_SCOPE.md` passes;
- the full seeded browser journey passes in CI and staging;
- deployment, reset, backup/restore, and demo runbooks have been exercised;
- the product/commercial lead can run the demo without developer intervention;
- limitations and non-production boundaries are visible in the product;
- the next backlog is based on design-partner evidence, not unvalidated breadth.
