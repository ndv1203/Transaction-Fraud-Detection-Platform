"""PostgreSQL 3-Tier Database Models (`raw`, `core`, `analytics` schemas).

Reference: docs/04_database_design.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(UTC)


SCHEMA_TABLES: dict[str, tuple[str, ...]] = {
    "raw": (
        "raw.ingestion_batches",
        "raw.raw_transactions",
    ),
    "core": (
        "core.cards",
        "core.merchants",
        "core.transactions",
        "core.transaction_labels",
        "core.transaction_features",
        "core.fraud_predictions",
        "core.fraud_alerts",
    ),
    "analytics": (
        "analytics.dim_time",
        "analytics.dim_cards",
        "analytics.dim_merchants",
        "analytics.dim_categories",
        "analytics.fact_transactions",
    ),
}


# =============================================================================
# 1. RAW SCHEMA ENTITIES
# =============================================================================


@dataclass
class RawIngestionBatch:
    """Represents `raw.ingestion_batches`."""

    source_name: str
    batch_id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    status: str = "RUNNING"
    input_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    error_summary: dict[str, Any] | None = None

    __schema__ = "raw"
    __tablename__ = "ingestion_batches"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RawTransaction:
    """Represents `raw.raw_transactions`."""

    source_name: str
    payload: dict[str, Any]
    source_trans_num: str | None = None
    is_valid: bool = True
    validation_errors: list[str] | dict[str, Any] | None = None
    batch_id: UUID | None = None
    ingested_at: datetime = field(default_factory=utc_now)
    raw_id: int | None = None

    __schema__ = "raw"
    __tablename__ = "raw_transactions"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# 2. CORE SCHEMA ENTITIES
# =============================================================================


@dataclass
class CoreCard:
    """Represents `core.cards`."""

    cc_num: str
    gender: str | None = None
    dob: date | None = None
    job: str | None = None
    city: str | None = None
    state_code: str | None = None
    zip: str | None = None
    lat: Decimal | float | None = None
    lon: Decimal | float | None = None
    city_pop: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    card_id: int | None = None

    __schema__ = "core"
    __tablename__ = "cards"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoreMerchant:
    """Represents `core.merchants`."""

    merchant_name: str
    primary_category: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    merchant_id: int | None = None

    __schema__ = "core"
    __tablename__ = "merchants"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoreTransaction:
    """Represents `core.transactions`."""

    trans_num: str
    card_id: int
    merchant_id: int
    category: str
    amt: Decimal
    event_time: datetime
    unix_time: int
    merch_lat: Decimal | float | None = None
    merch_lon: Decimal | float | None = None
    ingested_at: datetime = field(default_factory=utc_now)
    processing_status: str = "PROCESSED"
    batch_id: UUID | None = None
    transaction_id: int | None = None

    __schema__ = "core"
    __tablename__ = "transactions"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoreTransactionLabel:
    """Represents `core.transaction_labels` (strictly separated ground-truth label)."""

    transaction_id: int
    actual_is_fraud: bool
    label_source: str = "SPARKOV_GROUND_TRUTH"
    labeled_at: datetime = field(default_factory=utc_now)

    __schema__ = "core"
    __tablename__ = "transaction_labels"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoreTransactionFeature:
    """Represents `core.transaction_features`."""

    transaction_id: int
    tx_count_1h: int | None = None
    tx_count_6h: int | None = None
    tx_count_24h: int | None = None
    amt_sum_1h: Decimal | None = None
    amt_sum_24h: Decimal | None = None
    amt_to_card_mean_ratio: Decimal | float | None = None
    amt_to_cat_median_ratio: Decimal | float | None = None
    unique_merchants_24h: int | None = None
    time_since_last_tx_sec: int | None = None
    dist_home_to_merch_km: Decimal | float | None = None
    merch_to_merch_dist_km: Decimal | float | None = None
    implied_speed_kmh: Decimal | float | None = None
    hour_of_day: int | None = None
    day_of_week: int | None = None
    is_weekend: bool | None = None
    is_night_tx: bool | None = None
    customer_age: Decimal | float | None = None
    feature_generated_at: datetime = field(default_factory=utc_now)

    __schema__ = "core"
    __tablename__ = "transaction_features"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoreFraudPrediction:
    """Represents `core.fraud_predictions`."""

    transaction_id: int
    detection_method: str
    risk_score: Decimal | float
    is_flagged: bool
    risk_level: str
    model_version: str | None = None
    predicted_at: datetime = field(default_factory=utc_now)
    prediction_id: int | None = None

    __schema__ = "core"
    __tablename__ = "fraud_predictions"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoreFraudAlert:
    """Represents `core.fraud_alerts`."""

    prediction_id: int
    transaction_id: int
    alert_reason: dict[str, Any]
    alert_status: str = "NEW"
    reviewer_notes: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    reviewed_at: datetime | None = None
    alert_id: int | None = None

    __schema__ = "core"
    __tablename__ = "fraud_alerts"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# 3. ANALYTICS SCHEMA ENTITIES (Star Schema)
# =============================================================================


@dataclass
class AnalyticsDimTime:
    """Represents `analytics.dim_time`."""

    time_key: int
    date_actual: date
    year: int
    month: int
    day: int
    hour_of_day: int
    day_of_week: int
    day_name: str
    is_weekend: bool
    is_night_window: bool

    __schema__ = "analytics"
    __tablename__ = "dim_time"

    @classmethod
    def from_datetime(cls, dt: datetime) -> AnalyticsDimTime:
        time_key = int(dt.strftime("%Y%m%d%H"))
        dow = dt.weekday()
        hour = dt.hour
        return cls(
            time_key=time_key,
            date_actual=dt.date(),
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour_of_day=hour,
            day_of_week=dow,
            day_name=dt.strftime("%A"),
            is_weekend=(dow >= 5),
            is_night_window=(hour >= 22 or hour <= 3),
        )


@dataclass
class AnalyticsDimCard:
    """Represents `analytics.dim_cards`."""

    card_key: int
    cc_num: str
    gender: str | None = None
    age_group: str | None = None
    city: str | None = None
    state_code: str | None = None
    city_pop: int | None = None
    job: str | None = None

    __schema__ = "analytics"
    __tablename__ = "dim_cards"


@dataclass
class AnalyticsDimMerchant:
    """Represents `analytics.dim_merchants`."""

    merchant_key: int
    merchant_name: str
    primary_category: str | None = None

    __schema__ = "analytics"
    __tablename__ = "dim_merchants"


@dataclass
class AnalyticsDimCategory:
    """Represents `analytics.dim_categories`."""

    category_code: str
    is_online_channel: bool
    category_key: int | None = None

    __schema__ = "analytics"
    __tablename__ = "dim_categories"


@dataclass
class AnalyticsFactTransaction:
    """Represents `analytics.fact_transactions`."""

    transaction_id: int
    trans_num: str
    time_key: int
    card_key: int
    merchant_key: int
    category_key: int
    amt: Decimal
    dist_home_to_merch_km: Decimal | float | None = None
    implied_speed_kmh: Decimal | float | None = None
    tx_count_24h: int | None = None
    risk_score: Decimal | float | None = None
    risk_level: str | None = None
    is_flagged: bool = False
    is_confirmed_fraud: bool | None = None

    __schema__ = "analytics"
    __tablename__ = "fact_transactions"
