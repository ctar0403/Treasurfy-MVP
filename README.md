# TreasurFy MVP

TreasurFy is a treasury workspace for growth-stage companies with multiple
entities, banks, accounts, and currencies. The first customer-facing MVP is
designed to answer five questions quickly:

1. How much cash do we have now?
2. What will our cash position be in 30, 60, and 90 days?
3. Which entities are cash-rich or cash-poor?
4. Where are the immediate liquidity risks?
5. Which payments are waiting to be prepared or approved?

Its product wedge is faster implementation: bank-data mappings and payment
rules are represented as reusable, versioned profiles rather than rebuilt for
every customer.

## January 2027 demonstration

The MVP will demonstrate a seeded multi-entity company with multiple UK and US
bank accounts. A user can import balances and transactions, inspect consolidated
cash, run a simple forecast, review liquidity alerts, read a grounded daily
brief, and prepare/approve/export a payment file.

The MVP will not connect to a production bank or transmit money. A successful
payment validation means only that the instruction satisfies the selected
profile. Bank entitlements, credentials, testing, and production activation
remain external steps.

## Documentation

- [Product scope](docs/PRODUCT_SCOPE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Build plan](docs/BUILD_PLAN.md)
- [Customer discovery checklist](docs/DISCOVERY_CHECKLIST.md)
- [First prototype review](docs/FIRST_PROTOTYPE_REVIEW.md)

## Planned repository shape

```text
apps/
  api/       FastAPI application and domain services
  web/       React and TypeScript application
docs/        Product, architecture, and delivery decisions
infra/       Local and deployment configuration
```

Implementation begins only after the Phase 0 product decisions in the build
plan are accepted. This prevents the first sprint from encoding guesses about
the initial country, bank, payment rail, ERP, and design partner.
