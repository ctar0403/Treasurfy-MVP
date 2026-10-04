# First prototype review

Review date: 4 October 2026

## What exists

The earlier advisory prototype is a compact FastAPI application demonstrating:

- a canonical payment model;
- two versioned illustrative payment profiles;
- a profile registry with startup validation;
- deterministic profile-driven validation, including IBAN checks;
- a simplified `pain.001.001.03` XML renderer;
- a small static demonstration interface;
- onboarding states separating software work from credentials, bank UAT, and
  production activation.

Its automated suite currently passes **34 tests**. The prototype is a useful
technical spike, not a customer MVP.

## Reuse decision

Reuse by extraction and adaptation:

- canonical payment concepts and normalization rules;
- immutable profile/rule models;
- registry validation patterns;
- generic dotted-field rule evaluation;
- IBAN validation;
- renderer dispatch and deterministic XML tests;
- clear certification/evidence status language;
- test fixtures for valid and invalid profiles.

Do not copy as the new foundation:

- the static HTML/JavaScript interface;
- in-memory profile loading as the only persistence strategy;
- fictional profiles as if they were bank-compatible;
- the single-user/no-auth application shape;
- simplified XML as a production ISO 20022 implementation;
- onboarding states without tenant, user, audit, and revision records.

## Extraction spike

During Phase 0:

1. Copy the eligible domain code into a temporary branch of the new repository.
2. Preserve and run the relevant tests before changing behavior.
3. Move it behind the new workspace-scoped payment module.
4. Add persistence and explicit profile revisions/evidence status.
5. Replace illustrative assumptions only when a real specification or design
   partner supplies evidence.
6. Keep provenance in commit history; do not copy the prior repository's `.git`
   directory or virtual environment.

## Gap to the customer MVP

The earlier prototype does not include authentication, workspaces, a database,
bank/account data, imports, consolidated cash, FX rates, forecasting, liquidity
rules, approval roles, audit records, daily briefs, or deployment operations.
Those are new product capabilities and are planned explicitly rather than being
treated as small extensions to the spike.
