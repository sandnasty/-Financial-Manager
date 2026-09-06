from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from financial_manager.market_data import (
    SCHEMA_VERSION,
    AdjustmentStatus,
    BarRecord,
    CorporateActionRecord,
    CorporateActionType,
    DataContractError,
    InstrumentRecord,
    MarketSession,
    SourceMetadata,
    canonical_record_bytes,
    canonical_record_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)


def source() -> SourceMetadata:
    return SourceMetadata(
        provider="contract-test",
        provider_record_id="record-1",
        source_timestamp=NOW,
        ingested_at=datetime(2026, 9, 4, 20, 0, 1, tzinfo=UTC),
        raw_record_sha256="a" * 64,
        license_tier="test-only",
        dataset_version="test-2026-09-04",
    )


class MarketDataContractTests(unittest.TestCase):
    def test_instrument_enforces_phase_one_scope(self) -> None:
        record = InstrumentRecord(
            instrument_id="instrument-1",
            ticker="TEST",
            name="Contract Test Equity",
            mic="XNAS",
            currency="USD",
            country="US",
            active=True,
            effective_from=date(2020, 1, 1),
            effective_to=None,
            source=source(),
        )
        self.assertEqual(record.currency, "USD")
        with self.assertRaisesRegex(DataContractError, "U.S.-listed"):
            InstrumentRecord(
                instrument_id="instrument-2",
                ticker="TEST",
                name="Out of scope",
                mic="XTSE",
                currency="CAD",
                country="CA",
                active=True,
                effective_from=date(2020, 1, 1),
                effective_to=None,
                source=source(),
            )

    def test_bar_rejects_impossible_ohlc_and_naive_time(self) -> None:
        with self.assertRaisesRegex(DataContractError, "OHLC"):
            BarRecord(
                instrument_id="instrument-1",
                interval="15m",
                starts_at=NOW,
                ends_at=datetime(2026, 9, 4, 20, 15, tzinfo=UTC),
                open=Decimal("100"),
                high=Decimal("99"),
                low=Decimal("98"),
                close=Decimal("100"),
                volume=1_000,
                session=MarketSession.REGULAR,
                adjustment=AdjustmentStatus.RAW,
                source=source(),
            )
        with self.assertRaisesRegex(DataContractError, "timezone-aware UTC"):
            SourceMetadata(
                provider="test",
                provider_record_id="record",
                source_timestamp=datetime(2026, 9, 4, 20, 0),
                ingested_at=NOW,
                raw_record_sha256="a" * 64,
                license_tier="test-only",
                dataset_version="test",
            )

    def test_corporate_action_requires_type_specific_fields(self) -> None:
        with self.assertRaisesRegex(DataContractError, "split actions"):
            CorporateActionRecord(
                instrument_id="instrument-1",
                action_type=CorporateActionType.SPLIT,
                ex_date=date(2026, 9, 4),
                split_from=None,
                split_to=None,
                cash_amount=None,
                new_ticker=None,
                source=source(),
            )

    def test_canonical_serialization_is_stable_and_versioned(self) -> None:
        record = InstrumentRecord(
            instrument_id="instrument-1",
            ticker="TEST",
            name="Contract Test Equity",
            mic="XNAS",
            currency="USD",
            country="US",
            active=True,
            effective_from=date(2020, 1, 1),
            effective_to=None,
            source=source(),
        )
        first = canonical_record_bytes(record)
        self.assertEqual(first, canonical_record_bytes(record))
        self.assertEqual(len(canonical_record_sha256(record)), 64)
        self.assertIn(b'"record_type":"instrument"', first)
        self.assertIn(b'"schema_version":"1.0.0"', first)
        self.assertIn(b'"normalization_version":"1.0.0"', first)

        schema = json.loads(
            (ROOT / "schemas/market-data/v1/market-data-record.schema.json").read_text()
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], SCHEMA_VERSION)
        source_required = set(schema["$defs"]["source"]["required"])
        self.assertTrue(
            {"source_timestamp", "ingested_at", "raw_record_sha256", "license_tier"}
            <= source_required
        )
        self.assertEqual(
            {item["properties"]["record_type"]["const"] for item in schema["oneOf"]},
            {"instrument", "exchange_session", "corporate_action", "bar", "quote"},
        )


if __name__ == "__main__":
    unittest.main()
