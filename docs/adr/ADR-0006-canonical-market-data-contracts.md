# ADR-0006: Canonical market-data contracts

- Status: Accepted
- Date: 2026-09-06
- Decision owner: Product owner
- Linear issue: MS-104
- Epic: E04 / MS-40

## Context

Scanning, scoring, backtesting, and later execution must consume the same market facts without
becoming coupled to one commercial provider. Historical revisions, corporate actions, session
boundaries, and licensing restrictions must remain visible so results can be reproduced and
audited without look-ahead bias.

## Decision

Financial Manager uses immutable provider records and versioned normalized contracts. Phase 1 is
limited to U.S.-listed, USD-denominated equities during regular market hours. Every normalized
record carries source and ingestion timestamps, a raw-record SHA-256 digest, provider record ID,
license tier, dataset version, and normalization version.

The initial contract covers instruments, exchange sessions, corporate actions, daily and intraday
bars, and quotes. Timestamps are timezone-aware UTC; exchange session dates remain explicit.
Adjusted values must declare whether they are raw, split-adjusted, or total-return-adjusted.
Provider adapters translate into this contract at the isolated market-data gateway boundary.

## Consequences

- Provider selection can change without changing downstream strategy interfaces.
- Raw and normalized data must both be retained under their applicable license and retention terms.
- Corrections create new versions; they never silently overwrite data used by a prior decision.
- Extended-hours data is outside Phase 1 and cannot enter decision inputs as regular-session data.
- Provider licensing and redistribution rights are architecture constraints, not procurement notes.

## Verification

- `financial_manager/market_data.py`
- `schemas/market-data/v1/market-data-record.schema.json`
- `tests/test_market_data_contracts.py`
- `docs/market-data/E04-01-canonical-contract.md`
