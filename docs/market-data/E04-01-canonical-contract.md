# E04-01 canonical market-data contract

## Phase 1 datasets

| Dataset | Minimum content | Primary consumers |
|---|---|---|
| Instrument master | Stable ID, ticker history, name, MIC, active dates, USD/US scope | All services |
| Exchange sessions | Trading date and UTC open/close instants by MIC | Ingestion, features, backtests |
| Corporate actions | Splits, cash dividends, symbol changes, delistings | Normalization, accounting |
| Daily bars | Regular-session OHLCV, raw and declared adjustment status | Screening, backtests |
| Intraday bars | 1, 5, 15, and 30-minute regular-session OHLCV | 15–30 minute scans |
| Quotes | Bid/ask, sizes, event/source time | Opportunity scoring, freshness checks |

## Time and identity rules

- All event and ingestion timestamps are timezone-aware UTC.
- The exchange trading date and MIC remain explicit; neither is inferred from UTC date alone.
- A stable internal `instrument_id` survives ticker changes.
- Provider IDs are lineage identifiers and never replace the internal instrument ID.
- Phase 1 decision inputs are U.S.-listed, USD-denominated equities in the regular session only.

## Immutability, revisions, and replay

Raw provider responses are append-only and content-addressed by SHA-256. Normalization produces a
new dataset version when source facts or normalization logic change. A decision, score, backtest,
or recommendation must record the exact dataset and normalization versions it consumed. Replay
sorts by source time and uses ingestion time to prevent later corrections from appearing early.

## Quality gates

The gateway must reject or quarantine malformed identity, non-UTC time, impossible OHLC ranges,
negative sizes or volume, duplicates with conflicting content, and Region/session ambiguity. It
must measure freshness, completeness, duplicate rate, ordering delay, gap duration, revision rate,
and provider availability. Thresholds are provider/cadence-specific and are set in E04-02/E04-07.

## Licensing and retention

Every record carries provider and license-tier metadata. Provider selection must document real-time
display rights, non-display/automated-use rights, historical retention, derived-data rights,
redistribution restrictions, audit retention, rate limits, and termination/export behavior. The
system fails closed when a requested use is not permitted by the active license.
