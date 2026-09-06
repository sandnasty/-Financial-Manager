"""Versioned, provider-neutral market-data contracts for Phase 1."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = "1.0.0"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TICKER = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")
_MIC = re.compile(r"^[A-Z0-9]{4}$")
_INTERVALS = frozenset({"1m", "5m", "15m", "30m", "1d"})


class MarketSession(StrEnum):
    REGULAR = "regular"


class AdjustmentStatus(StrEnum):
    RAW = "raw"
    SPLIT_ADJUSTED = "split_adjusted"
    TOTAL_RETURN_ADJUSTED = "total_return_adjusted"


class CorporateActionType(StrEnum):
    SPLIT = "split"
    CASH_DIVIDEND = "cash_dividend"
    SYMBOL_CHANGE = "symbol_change"
    DELISTING = "delisting"


class DataContractError(ValueError):
    """Raised when a record violates the canonical market-data contract."""


def _require_text(name: str, value: str) -> None:
    if not value.strip():
        raise DataContractError(f"{name} is required")


def _require_utc(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise DataContractError(f"{name} must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Lineage, licensing, and timing attached to every canonical record."""

    provider: str
    provider_record_id: str
    source_timestamp: datetime
    ingested_at: datetime
    raw_record_sha256: str
    license_tier: str
    dataset_version: str
    normalization_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "provider",
            "provider_record_id",
            "license_tier",
            "dataset_version",
            "normalization_version",
        ):
            _require_text(name, getattr(self, name))
        _require_utc("source_timestamp", self.source_timestamp)
        _require_utc("ingested_at", self.ingested_at)
        if self.ingested_at < self.source_timestamp:
            raise DataContractError("ingested_at cannot precede source_timestamp")
        if not _SHA256.fullmatch(self.raw_record_sha256):
            raise DataContractError("raw_record_sha256 must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class InstrumentRecord:
    instrument_id: str
    ticker: str
    name: str
    mic: str
    currency: str
    country: str
    active: bool
    effective_from: date
    effective_to: date | None
    source: SourceMetadata

    def __post_init__(self) -> None:
        _require_text("instrument_id", self.instrument_id)
        _require_text("name", self.name)
        if not _TICKER.fullmatch(self.ticker):
            raise DataContractError("ticker must use the canonical uppercase format")
        if not _MIC.fullmatch(self.mic):
            raise DataContractError("mic must be a four-character ISO 10383 code")
        if self.currency != "USD" or self.country != "US":
            raise DataContractError("Phase 1 permits only U.S.-listed USD instruments")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise DataContractError("effective_to cannot precede effective_from")


@dataclass(frozen=True, slots=True)
class ExchangeSessionRecord:
    mic: str
    session_date: date
    opens_at: datetime
    closes_at: datetime
    is_trading_day: bool
    source: SourceMetadata

    def __post_init__(self) -> None:
        if not _MIC.fullmatch(self.mic):
            raise DataContractError("mic must be a four-character ISO 10383 code")
        _require_utc("opens_at", self.opens_at)
        _require_utc("closes_at", self.closes_at)
        if self.is_trading_day and self.opens_at >= self.closes_at:
            raise DataContractError("a trading session must open before it closes")


@dataclass(frozen=True, slots=True)
class BarRecord:
    instrument_id: str
    interval: str
    starts_at: datetime
    ends_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    session: MarketSession
    adjustment: AdjustmentStatus
    source: SourceMetadata

    def __post_init__(self) -> None:
        _require_text("instrument_id", self.instrument_id)
        _require_utc("starts_at", self.starts_at)
        _require_utc("ends_at", self.ends_at)
        if self.interval not in _INTERVALS:
            raise DataContractError("unsupported Phase 1 bar interval")
        if self.starts_at >= self.ends_at:
            raise DataContractError("bar starts_at must precede ends_at")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise DataContractError("bar prices must be positive")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise DataContractError("bar OHLC values are inconsistent")
        if self.low > self.high or self.volume < 0:
            raise DataContractError("bar range and volume must be valid")


@dataclass(frozen=True, slots=True)
class QuoteRecord:
    instrument_id: str
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    session: MarketSession
    source: SourceMetadata

    def __post_init__(self) -> None:
        _require_text("instrument_id", self.instrument_id)
        if self.bid <= 0 or self.ask <= 0 or self.bid > self.ask:
            raise DataContractError("quote must have positive bid at or below ask")
        if self.bid_size < 0 or self.ask_size < 0:
            raise DataContractError("quote sizes cannot be negative")


@dataclass(frozen=True, slots=True)
class CorporateActionRecord:
    instrument_id: str
    action_type: CorporateActionType
    ex_date: date
    split_from: Decimal | None
    split_to: Decimal | None
    cash_amount: Decimal | None
    new_ticker: str | None
    source: SourceMetadata

    def __post_init__(self) -> None:
        _require_text("instrument_id", self.instrument_id)
        if self.action_type is CorporateActionType.SPLIT:
            if not self.split_from or not self.split_to:
                raise DataContractError("split actions require a positive ratio")
            if self.split_from <= 0 or self.split_to <= 0:
                raise DataContractError("split ratio values must be positive")
        if self.action_type is CorporateActionType.CASH_DIVIDEND:
            if self.cash_amount is None or self.cash_amount < 0:
                raise DataContractError("cash dividends require a non-negative amount")
        if self.action_type is CorporateActionType.SYMBOL_CHANGE:
            if self.new_ticker is None or not _TICKER.fullmatch(self.new_ticker):
                raise DataContractError("symbol changes require a canonical new ticker")


def canonical_record_bytes(record: Any) -> bytes:
    """Serialize one immutable record deterministically for manifests and replay."""

    record_types = {
        InstrumentRecord: "instrument",
        ExchangeSessionRecord: "exchange_session",
        CorporateActionRecord: "corporate_action",
        BarRecord: "bar",
        QuoteRecord: "quote",
    }
    record_type = record_types.get(type(record))
    if record_type is None:
        raise DataContractError("unsupported canonical record type")

    def normalize(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in sorted(value.items())}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return format(value, "f")
        if isinstance(value, StrEnum):
            return value.value
        return value

    values = asdict(record)
    source = values.pop("source")
    envelope = {
        "payload": values,
        "record_type": record_type,
        "schema_version": SCHEMA_VERSION,
        "source": source,
    }
    return (json.dumps(normalize(envelope), separators=(",", ":"), sort_keys=True) + "\n").encode()


def canonical_record_sha256(record: Any) -> str:
    return hashlib.sha256(canonical_record_bytes(record)).hexdigest()
