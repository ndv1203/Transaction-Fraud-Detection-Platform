"""Data access layer (Repository pattern) for the PostgreSQL 3-Tier schema (`raw`, `core`, `analytics`)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from database.models import (
    CoreCard,
    CoreFraudAlert,
    CoreFraudPrediction,
    CoreMerchant,
    CoreTransaction,
    CoreTransactionFeature,
    CoreTransactionLabel,
    RawIngestionBatch,
    RawTransaction,
    utc_now,
)


class PostgresQueries:
    """Parameterized idempotent SQL statements for the 3-tier PostgreSQL database."""

    INSERT_INGESTION_BATCH = """
        INSERT INTO raw.ingestion_batches (
            batch_id, source_name, started_at, completed_at,
            status, input_count, accepted_count, rejected_count, error_summary
        ) VALUES (
            :batch_id, :source_name, :started_at, :completed_at,
            :status, :input_count, :accepted_count, :rejected_count, CAST(:error_summary AS JSONB)
        )
        ON CONFLICT (batch_id) DO UPDATE SET
            completed_at = EXCLUDED.completed_at,
            status = EXCLUDED.status,
            input_count = EXCLUDED.input_count,
            accepted_count = EXCLUDED.accepted_count,
            rejected_count = EXCLUDED.rejected_count,
            error_summary = EXCLUDED.error_summary;
    """

    INSERT_RAW_TRANSACTION = """
        INSERT INTO raw.raw_transactions (
            source_trans_num, source_name, payload, is_valid,
            validation_errors, batch_id, ingested_at
        ) VALUES (
            :source_trans_num, :source_name, CAST(:payload AS JSONB), :is_valid,
            CAST(:validation_errors AS JSONB), :batch_id, :ingested_at
        )
        RETURNING raw_id;
    """

    UPSERT_CARD = """
        INSERT INTO core.cards (
            cc_num, gender, dob, job, city, state_code, zip, lat, lon, city_pop, created_at
        ) VALUES (
            :cc_num, :gender, :dob, :job, :city, :state_code, :zip, :lat, :lon, :city_pop, :created_at
        )
        ON CONFLICT (cc_num) DO UPDATE SET
            city = COALESCE(EXCLUDED.city, core.cards.city),
            state_code = COALESCE(EXCLUDED.state_code, core.cards.state_code),
            job = COALESCE(EXCLUDED.job, core.cards.job),
            city_pop = COALESCE(EXCLUDED.city_pop, core.cards.city_pop)
        RETURNING card_id;
    """

    UPSERT_MERCHANT = """
        INSERT INTO core.merchants (
            merchant_name, primary_category, created_at
        ) VALUES (
            :merchant_name, :primary_category, :created_at
        )
        ON CONFLICT (merchant_name) DO UPDATE SET
            primary_category = COALESCE(EXCLUDED.primary_category, core.merchants.primary_category)
        RETURNING merchant_id;
    """

    UPSERT_TRANSACTION = """
        INSERT INTO core.transactions (
            trans_num, card_id, merchant_id, category, amt,
            event_time, unix_time, merch_lat, merch_lon,
            ingested_at, processing_status, batch_id
        ) VALUES (
            :trans_num, :card_id, :merchant_id, :category, :amt,
            :event_time, :unix_time, :merch_lat, :merch_lon,
            :ingested_at, :processing_status, :batch_id
        )
        ON CONFLICT (trans_num) DO NOTHING
        RETURNING transaction_id;
    """

    UPSERT_TRANSACTION_LABEL = """
        INSERT INTO core.transaction_labels (
            transaction_id, actual_is_fraud, label_source, labeled_at
        ) VALUES (
            :transaction_id, :actual_is_fraud, :label_source, :labeled_at
        )
        ON CONFLICT (transaction_id) DO UPDATE SET
            actual_is_fraud = EXCLUDED.actual_is_fraud,
            label_source = EXCLUDED.label_source,
            labeled_at = EXCLUDED.labeled_at;
    """

    UPSERT_TRANSACTION_FEATURES = """
        INSERT INTO core.transaction_features (
            transaction_id, tx_count_1h, tx_count_6h, tx_count_24h,
            amt_sum_1h, amt_sum_24h, amt_to_card_mean_ratio, amt_to_cat_median_ratio,
            unique_merchants_24h, time_since_last_tx_sec, dist_home_to_merch_km,
            merch_to_merch_dist_km, implied_speed_kmh, hour_of_day, day_of_week,
            is_weekend, is_night_tx, customer_age, feature_generated_at
        ) VALUES (
            :transaction_id, :tx_count_1h, :tx_count_6h, :tx_count_24h,
            :amt_sum_1h, :amt_sum_24h, :amt_to_card_mean_ratio, :amt_to_cat_median_ratio,
            :unique_merchants_24h, :time_since_last_tx_sec, :dist_home_to_merch_km,
            :merch_to_merch_dist_km, :implied_speed_kmh, :hour_of_day, :day_of_week,
            :is_weekend, :is_night_tx, :customer_age, :feature_generated_at
        )
        ON CONFLICT (transaction_id) DO UPDATE SET
            tx_count_1h = EXCLUDED.tx_count_1h,
            tx_count_6h = EXCLUDED.tx_count_6h,
            tx_count_24h = EXCLUDED.tx_count_24h,
            amt_sum_1h = EXCLUDED.amt_sum_1h,
            amt_sum_24h = EXCLUDED.amt_sum_24h,
            amt_to_card_mean_ratio = EXCLUDED.amt_to_card_mean_ratio,
            amt_to_cat_median_ratio = EXCLUDED.amt_to_cat_median_ratio,
            unique_merchants_24h = EXCLUDED.unique_merchants_24h,
            time_since_last_tx_sec = EXCLUDED.time_since_last_tx_sec,
            dist_home_to_merch_km = EXCLUDED.dist_home_to_merch_km,
            merch_to_merch_dist_km = EXCLUDED.merch_to_merch_dist_km,
            implied_speed_kmh = EXCLUDED.implied_speed_kmh,
            hour_of_day = EXCLUDED.hour_of_day,
            day_of_week = EXCLUDED.day_of_week,
            is_weekend = EXCLUDED.is_weekend,
            is_night_tx = EXCLUDED.is_night_tx,
            customer_age = EXCLUDED.customer_age,
            feature_generated_at = EXCLUDED.feature_generated_at;
    """

    INSERT_FRAUD_PREDICTION = """
        INSERT INTO core.fraud_predictions (
            transaction_id, detection_method, risk_score,
            is_flagged, risk_level, model_version, predicted_at
        ) VALUES (
            :transaction_id, :detection_method, :risk_score,
            :is_flagged, :risk_level, :model_version, :predicted_at
        )
        RETURNING prediction_id;
    """

    INSERT_FRAUD_ALERT = """
        INSERT INTO core.fraud_alerts (
            prediction_id, transaction_id, alert_status,
            alert_reason, reviewer_notes, created_at, reviewed_at
        ) VALUES (
            :prediction_id, :transaction_id, :alert_status,
            CAST(:alert_reason AS JSONB), :reviewer_notes, :created_at, :reviewed_at
        )
        RETURNING alert_id;
    """


class FraudRepository:
    """Repository wrapping idempotent operations across `raw`, `core`, and `analytics`."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def _execute(self, sql: str, params: dict[str, Any]) -> Any:
        try:
            from sqlalchemy import text

            stmt = text(sql)
        except ImportError:
            stmt = sql
        return self.session.execute(stmt, params)

    def save_ingestion_batch(self, batch: RawIngestionBatch) -> RawIngestionBatch:
        """Create or update an ingestion batch record in `raw.ingestion_batches`."""
        params = batch.to_dict()
        params["batch_id"] = str(batch.batch_id)
        params["error_summary"] = (
            json.dumps(batch.error_summary) if batch.error_summary is not None else None
        )
        self._execute(PostgresQueries.INSERT_INGESTION_BATCH, params)
        return batch

    def complete_ingestion_batch(
        self,
        batch: RawIngestionBatch,
        *,
        status: str = "SUCCEEDED",
        input_count: int = 0,
        accepted_count: int = 0,
        rejected_count: int = 0,
        error_summary: dict[str, Any] | None = None,
    ) -> RawIngestionBatch:
        """Finalize an ingestion batch with counts and error summary."""
        batch.completed_at = utc_now()
        batch.status = status
        batch.input_count = input_count
        batch.accepted_count = accepted_count
        batch.rejected_count = rejected_count
        batch.error_summary = error_summary
        return self.save_ingestion_batch(batch)

    def log_raw_transaction(self, raw_tx: RawTransaction) -> int | None:
        """Insert a raw transaction payload (valid or quarantined) into `raw.raw_transactions`."""
        params = {
            "source_trans_num": raw_tx.source_trans_num,
            "source_name": raw_tx.source_name,
            "payload": json.dumps(raw_tx.payload, default=str),
            "is_valid": raw_tx.is_valid,
            "validation_errors": (
                json.dumps(raw_tx.validation_errors)
                if raw_tx.validation_errors is not None
                else None
            ),
            "batch_id": str(raw_tx.batch_id) if isinstance(raw_tx.batch_id, UUID) else raw_tx.batch_id,
            "ingested_at": raw_tx.ingested_at,
        }
        result = self._execute(PostgresQueries.INSERT_RAW_TRANSACTION, params)
        row = result.fetchone() if hasattr(result, "fetchone") else None
        if row is not None:
            raw_tx.raw_id = int(row[0])
        return raw_tx.raw_id

    def upsert_card(self, card: CoreCard) -> int | None:
        """Insert or update a cardholder record in `core.cards`."""
        result = self._execute(PostgresQueries.UPSERT_CARD, card.to_dict())
        row = result.fetchone() if hasattr(result, "fetchone") else None
        if row is not None:
            card.card_id = int(row[0])
        return card.card_id

    def upsert_merchant(self, merchant: CoreMerchant) -> int | None:
        """Insert or update a merchant record in `core.merchants`."""
        result = self._execute(PostgresQueries.UPSERT_MERCHANT, merchant.to_dict())
        row = result.fetchone() if hasattr(result, "fetchone") else None
        if row is not None:
            merchant.merchant_id = int(row[0])
        return merchant.merchant_id

    def insert_transaction_idempotent(self, tx: CoreTransaction) -> int | None:
        """Insert a normalized transaction into `core.transactions` (`ON CONFLICT DO NOTHING`)."""
        params = tx.to_dict()
        params["batch_id"] = str(tx.batch_id) if isinstance(tx.batch_id, UUID) else tx.batch_id
        result = self._execute(PostgresQueries.UPSERT_TRANSACTION, params)
        row = result.fetchone() if hasattr(result, "fetchone") else None
        if row is not None:
            tx.transaction_id = int(row[0])
        return tx.transaction_id

    def upsert_transaction_label(self, label: CoreTransactionLabel) -> None:
        """Store ground-truth fraud label in `core.transaction_labels`."""
        self._execute(PostgresQueries.UPSERT_TRANSACTION_LABEL, label.to_dict())

    def upsert_transaction_features(self, features: CoreTransactionFeature) -> None:
        """Store computed transaction features in `core.transaction_features`."""
        self._execute(PostgresQueries.UPSERT_TRANSACTION_FEATURES, features.to_dict())

    def save_prediction(self, prediction: CoreFraudPrediction) -> int | None:
        """Insert a risk score record into `core.fraud_predictions`."""
        result = self._execute(PostgresQueries.INSERT_FRAUD_PREDICTION, prediction.to_dict())
        row = result.fetchone() if hasattr(result, "fetchone") else None
        if row is not None:
            prediction.prediction_id = int(row[0])
        return prediction.prediction_id

    def create_alert(self, alert: CoreFraudAlert) -> int | None:
        """Insert an explainable alert record into `core.fraud_alerts`."""
        params = alert.to_dict()
        params["alert_reason"] = json.dumps(alert.alert_reason, default=str)
        result = self._execute(PostgresQueries.INSERT_FRAUD_ALERT, params)
        row = result.fetchone() if hasattr(result, "fetchone") else None
        if row is not None:
            alert.alert_id = int(row[0])
        return alert.alert_id
