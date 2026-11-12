# AIPAC Money Tracker — Beta

A source-first, responsive political finance explorer covering AIPAC PAC, United Democracy Project, and additional organizations only when documented relationships are established.

## Current state

The React/TypeScript dashboard is a UI beta. **Financial totals and politician rankings are not yet connected**; no fabricated figures are displayed.

## Run locally

```bash
npm install
npm run dev
npm run build
```

## Deploy to Netlify

Import this GitHub repository in Netlify. The included `netlify.toml` configures the Vite build command (`npm run build`), output directory (`dist`), and SPA fallback.

## Official committee sources

- [AIPAC PAC — C00797670](https://www.fec.gov/data/committee/C00797670/)
- [United Democracy Project — C00799031](https://www.fec.gov/data/committee/C00799031/)
- [FEC Open API](https://api.open.fec.gov/developers/)

## Accounting methodology

1. Direct PAC contributions, earmarked/conduit activity, and independent expenditures are separately classified.
2. Independent support and opposition spending are never described as money received by candidates.
3. Refunds, amendments, transfers, and pass-throughs must be reconciled to prevent double counting.
4. Additional network entities require evidence of an organizational or financial relationship, including effective dates.
5. Congressional voting data can be compared with financial activity without asserting causation.
6. Each published amount must retain a link to its original filing and a refresh timestamp.

## Next development phase

Build server-side FEC ingestion and PostgreSQL reconciliation, candidate identity matching, tested aggregates, and interactive maps. Keep API secrets server-side rather than in frontend `VITE_*` variables.
