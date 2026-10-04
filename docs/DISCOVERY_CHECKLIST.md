# Customer discovery checklist

Use the same questions for each prospective design partner. Capture facts and
examples, not only feature requests.

## Company and buyer

- Company size, stage, sector, countries, legal entities, finance-team size
- Primary user and economic buyer
- What event made treasury painful now?
- What would justify changing the current process?

## Current stack

- Banks and account count by country/currency
- ERP/accounting platform and version
- Bank portals, spreadsheets, BI tools, and payment tools currently used
- Statement/report formats available: CSV, BAI2, MT940, CAMT.053, API, SFTP
- Payment formats/rails used: pain.001, ACH, Faster Payments, wire, SEPA, other

## Daily workflow

- How is current cash assembled and how long does it take?
- Who performs the work and who checks it?
- How are 30/60/90 forecasts built and updated?
- How are entity surpluses, deficits, and minimum balances identified?
- Which morning questions are hardest to answer confidently?

## Payments

- Where are payments created, approved, and sent today?
- Maker/checker and approval thresholds
- Single, bulk, domestic, and cross-border volumes
- Which fields are bank-standard, company-specific, and account-specific?
- Which implementation/testing steps repeat for each customer?
- What evidence is required before a format is trusted in production?

## Implementation

- Time from purchase to first useful dashboard
- Time from bank entitlement to tested payment file/connection
- Tasks owned by the customer, bank, ERP partner, and vendor
- Longest delays and most common failed tests
- Security, procurement, compliance, and data-residency blockers

## Commercial validation

- Which one outcome has measurable value?
- What is the cost of the manual process or liquidity mistake?
- Would the customer test with synthetic/redacted data in January?
- What must be true for a paid pilot?
- Preferred pricing unit: entity, account, module, payment volume, or flat tier
- Who else must approve a pilot?

## Required evidence pack

Ask for redacted or synthetic examples only until data handling is approved:

- account and entity inventory;
- one balance/transaction export;
- one forecast spreadsheet;
- one payment input and expected output;
- approval policy;
- onboarding checklist or test feedback;
- exact bank/ERP terminology and error messages.

## Interview summary

After each call, record:

- top three painful jobs;
- current time/cost baseline;
- first useful TreasurFy outcome;
- must-have integration;
- objections and risks;
- willingness-to-test and willingness-to-pay condition;
- next action, owner, and date.
