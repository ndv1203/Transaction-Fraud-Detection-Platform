"""Unit tests for core config, preprocessing (loader, cleaner, validation, splitter), and 3-tier PostgreSQL database design."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from database.connection import SCHEMA_SQL_PATH, load_schema_sql
from database.models import (
    SCHEMA_TABLES,
    AnalyticsDimTime,
    CoreCard,
    CoreFraudAlert,
    CoreFraudPrediction,
    CoreMerchant,
    CoreTransaction,
    CoreTransactionLabel,
    RawIngestionBatch,
    RawTransaction,
)
from database.repository import FraudRepository
from fraud_detection.config import PROJECT_ROOT, load_config
from fraud_detection.utils.logger import get_logger
from preprocessing.cleaner import (
    clean_transactions,
)
from preprocessing.feature_engineering import FeaturePipeline
from preprocessing.loader import load_parquet, load_raw_csv
from preprocessing.pipeline import process_raw_file
from preprocessing.splitter import temporal_train_val_split
from preprocessing.validation import validate_transactions


def _make_sample_raw_df() -> pd.DataFrame:
    """Create a synthetic raw Sparkov DataFrame with original CSV column names."""
    return pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2, 3, 4],
            "trans_date_trans_time": [
                "2019-01-01 00:00:18",
                "2019-01-01 01:15:00",
                "2019-01-01 02:30:00",
                "2019-01-02 10:00:00",
                "2019-01-03 14:45:00",
            ],
            "cc_num": ["1111222233334444", "1111222233334444", "5555666677778888", "5555666677778888", "9999000011112222"],
            "merchant": ["fraud_Rippin, Kub and Mann", "fraud_Heller, Gutmann and Zieme", "fraud_Kiehn Inc", "fraud_Kiehn Inc", "fraud_Kutch, Hermiston and Farrell"],
            "category": ["misc_net", "grocery_pos", "gas_transport", "shopping_net", "shopping_pos"],
            "amt": [4.97, 107.23, 45.00, 850.50, 29.99],
            "first": ["Jennifer", "Jennifer", "Stephanie", "Stephanie", "Edward"],
            "last": ["Banks", "Banks", "Gill", "Gill", "Sanchez"],
            "gender": ["F", "F", "F", "F", "M"],
            "street": ["561 Perry Cove", "561 Perry Cove", "43039 Riley Greens", "43039 Riley Greens", "594 White Dale"],
            "city": ["Moravian Falls", "Moravian Falls", "Malad City", "Malad City", "Athena"],
            "state": ["NC", "NC", "ID", "ID", "OR"],
            "zip": ["28654", "28654", "83252", "83252", "97813"],
            "lat": [36.0788, 36.0788, 42.1808, 42.1808, 45.8225],
            "long": [-81.1781, -81.1781, -112.2620, -112.2620, -118.4977],
            "city_pop": [3495, 3495, 4154, 4154, 1500],
            "job": ["Psychologist", "Psychologist", "Special educational needs teacher", "Special educational needs teacher", "Engineer"],
            "dob": ["1988-03-09", "1988-03-09", "1978-06-21", "1978-06-21", "1965-11-12"],
            "trans_num": ["tx_001", "tx_002", "tx_003", "tx_004", "tx_005"],
            "unix_time": [1546300818, 1546305300, 1546309800, 1546423200, 1546526700],
            "merch_lat": [36.011293, 36.055000, 42.150000, 42.210000, 45.800000],
            "merch_long": [-82.048315, -81.200000, -112.300000, -112.100000, -118.500000],
            "is_fraud": [0, 0, 0, 1, 0],
        }
    )


def test_config_and_logger_initialization(tmp_path: Path) -> None:
    cfg = load_config()
    assert cfg.project.name == "transaction-fraud-detection-platform"
    assert cfg.project.seed == 42
    assert cfg.preprocessing.id_col == "trans_num"
    assert cfg.preprocessing.rename_cols == {
        "state": "state_code",
        "long": "lon",
        "merch_long": "merch_lon",
    }
    assert cfg.paths.raw_data == PROJECT_ROOT / "data" / "raw"

    log_file = tmp_path / "test.log"
    log = get_logger("test_fraud_logger", log_file=log_file)
    log.info("Health check log line")
    assert log_file.exists()
    assert "Health check log line" in log_file.read_text(encoding="utf-8")


def test_cleaner_standardization_and_deduplication() -> None:
    raw_df = _make_sample_raw_df()
    # Add a duplicate row for tx_002
    dup_df = pd.concat([raw_df, raw_df.iloc[[1]]], ignore_index=True)

    cleaned = clean_transactions(dup_df, drop_pii=True, deduplicate=True)
    assert len(cleaned) == 5
    assert "state_code" in cleaned.columns
    assert "lon" in cleaned.columns
    assert "merch_lon" in cleaned.columns
    for old_col in ("state", "long", "merch_long", "Unnamed: 0", "first", "last", "street"):
        assert old_col not in cleaned.columns
    assert pd.api.types.is_datetime64_any_dtype(cleaned["trans_date_trans_time"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["dob"])


def test_validation_quarantines_invalid_and_duplicate_rows() -> None:
    df = clean_transactions(_make_sample_raw_df(), drop_pii=False, deduplicate=False)

    # Inject invalid rows: negative amount, out-of-range latitude, duplicate trans_num
    bad_rows = df.iloc[:3].copy()
    bad_rows.loc[bad_rows.index[0], "trans_num"] = "tx_bad_amt"
    bad_rows.loc[bad_rows.index[0], "amt"] = -15.0

    bad_rows.loc[bad_rows.index[1], "trans_num"] = "tx_bad_lat"
    bad_rows.loc[bad_rows.index[1], "lat"] = 125.0  # > 90 degrees

    # bad_rows.index[2] keeps trans_num == "tx_003" -> duplicate!
    combined = pd.concat([df, bad_rows], ignore_index=True)

    report = validate_transactions(combined, require_target=True)
    assert report.input_count == 8
    assert report.accepted_count == 5
    assert report.rejected_count == 3
    assert report.duplicate_count == 1
    assert "invalid_amt_non_positive" in report.error_counts
    assert "invalid_lat_range" in report.error_counts
    assert "duplicate_trans_num" in report.error_counts
    assert "validation_errors" in report.rejected_df.columns


def test_temporal_splitter_zero_leakage() -> None:
    df = clean_transactions(_make_sample_raw_df())
    # Shuffle rows intentionally to verify chronological sorting
    shuffled = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    split = temporal_train_val_split(shuffled, val_size=0.4)
    assert len(split.train_df) == 3
    assert len(split.val_df) == 2
    assert split.train_df["unix_time"].max() <= split.val_df["unix_time"].min()
    assert split.cold_start_val_cards == 1  # card 9999000011112222 appears only in the last row


def test_loader_and_pipeline_roundtrip(tmp_path: Path) -> None:
    raw_df = _make_sample_raw_df()
    csv_path = tmp_path / "sample_raw.csv"
    parquet_path = tmp_path / "sample_cleaned.parquet"
    raw_df.to_csv(csv_path, index=False)

    loaded_csv = load_raw_csv(csv_path)
    assert len(loaded_csv) == 5

    res = process_raw_file(csv_path, output_parquet_path=parquet_path, drop_pii=True)
    assert res.output_path == parquet_path
    assert parquet_path.exists()
    assert res.validation_report.accepted_count == 5

    reloaded = load_parquet(parquet_path)
    assert len(reloaded) == 5
    assert "state_code" in reloaded.columns
    assert "first" not in reloaded.columns


def test_feature_pipeline_composability() -> None:
    df = clean_transactions(_make_sample_raw_df())
    fp = FeaturePipeline()
    fp.add_step("extract_hour", lambda d: d.assign(hour_of_day=d["trans_date_trans_time"].dt.hour))
    out = fp.transform(df)
    assert "hour_of_day" in out.columns
    assert list(out["hour_of_day"]) == [0, 1, 2, 10, 14]


def test_postgres_3tier_schema_and_repository() -> None:
    ddl = load_schema_sql(SCHEMA_SQL_PATH)
    for schema_name, tables in SCHEMA_TABLES.items():
        assert f"CREATE SCHEMA IF NOT EXISTS {schema_name};" in ddl
        for tbl in tables:
            assert f"CREATE TABLE IF NOT EXISTS {tbl}" in ddl

    for view_name in (
        "analytics.agg_hourly_transactions",
        "analytics.agg_daily_fraud",
        "analytics.agg_category_metrics",
    ):
        assert f"CREATE OR REPLACE VIEW {view_name}" in ddl

    # Test AnalyticsDimTime builder
    dt = datetime(2020, 6, 21, 23, 15, 0, tzinfo=UTC)
    dim_t = AnalyticsDimTime.from_datetime(dt)
    assert dim_t.time_key == 2020062123
    assert dim_t.is_weekend is True
    assert dim_t.is_night_window is True

    # Test Repository with a mock DB session
    executed: list[tuple[str, dict[str, Any]]] = []

    class FakeResult:
        def __init__(self, row_id: int) -> None:
            self._row_id = row_id

        def fetchone(self) -> tuple[int]:
            return (self._row_id,)

    class FakeSession:
        def execute(self, stmt: Any, params: dict[str, Any]) -> FakeResult:
            executed.append((str(stmt), params))
            return FakeResult(101)

    repo = FraudRepository(FakeSession())
    batch = RawIngestionBatch(source_name="sparkov_fraudTrain_csv")
    repo.save_ingestion_batch(batch)
    repo.complete_ingestion_batch(batch, input_count=5, accepted_count=5, rejected_count=0)

    raw_tx = RawTransaction(
        source_name="sparkov_fraudTrain_csv",
        source_trans_num="tx_001",
        payload={"trans_num": "tx_001", "amt": 4.97},
        batch_id=batch.batch_id,
    )
    assert repo.log_raw_transaction(raw_tx) == 101

    card = CoreCard(cc_num="1111222233334444", state_code="NC")
    assert repo.upsert_card(card) == 101

    merch = CoreMerchant(merchant_name="fraud_Kiehn Inc", primary_category="gas_transport")
    assert repo.upsert_merchant(merch) == 101

    tx = CoreTransaction(
        trans_num="tx_001",
        card_id=101,
        merchant_id=101,
        category="misc_net",
        amt=Decimal("4.97"),
        event_time=dt,
        unix_time=1546300818,
        batch_id=batch.batch_id,
    )
    assert repo.insert_transaction_idempotent(tx) == 101

    repo.upsert_transaction_label(CoreTransactionLabel(transaction_id=101, actual_is_fraud=False))
    pred = CoreFraudPrediction(
        transaction_id=101,
        detection_method="RULE_BASED",
        risk_score=Decimal("0.75000"),
        is_flagged=True,
        risk_level="HIGH",
        model_version="rules_v1.0",
    )
    assert repo.save_prediction(pred) == 101

    alert = CoreFraudAlert(
        prediction_id=101,
        transaction_id=101,
        alert_reason={"triggered_rules": ["R001"]},
    )
    assert repo.create_alert(alert) == 101
    assert len(executed) == 9
