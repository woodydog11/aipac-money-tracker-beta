# Development milestones

## Milestone 1: AIPAC PAC
- Import candidate master data and committee filings.
- Reconcile Schedule B contributions and earmarked/conduit transactions with the receiving campaign's Schedule A; never count the same earmarked gift twice.
- Maintain source filing, amendments, refunds, and deduplication keys.
- **Status: schema prepared; importer not yet implemented for direct PAC receipts/disbursements.**

## Milestone 2: United Democracy Project
- Import FEC Schedule E independent expenditures by candidate and support/oppose indicator.
- Preserve the filing image number, transaction identifier, election cycle, and original payload.
- **Status: ingestion script drafted; requires API credentials, dedicated database, endpoint validation, and reconciliation.**

## Milestone 3: Politician leaderboard
- Join FEC candidate identifiers to elected members and historical elections.
- Display independently verifiable direct, earmarked, support, and opposition totals separately.
- **Status: dashboard placeholder; aggregation and identity matching pending.**

## Milestone 4: U.S. map
- Group verified candidate-level amounts by state and election cycle.
- Support state selection, category toggles, and linked source records.
- **Status: placeholder; geospatial interface pending.**

## Milestone 5: Money & Votes
- Import House and Senate roll calls from official sources and map elected members to Bioguide IDs.
- Present dated events alongside contributions without asserting causation.
- **Status: schema prepared; vote ingestion and UI pending.**

## Operational requirements
- Use a dedicated Supabase project; never reuse an unrelated application's database.
- Keep FEC API key and Supabase service key in server-only secrets.
- Run ingestion and reconciliation separately. All new transactions default to `pending`.
- Only mark transactions `verified` after matching against source filings and accounting for amendments and conduit pass-throughs.
- Schedule incremental refresh after full historical backfill; expose last-successful refresh timestamp.
- Recheck endpoint schemas and rate limits before production ingestion.
