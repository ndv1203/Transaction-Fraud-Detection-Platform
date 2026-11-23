"""Dataset splitting utilities (chronological / Out-of-Time splitting for zero leakage)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TemporalSplitResult:
    """Container for chronological Train / Validation split results and metadata."""

    train_df: pd.DataFrame
    val_df: pd.DataFrame
    cutoff_unix_time: int
    cutoff_timestamp: pd.Timestamp | None
    cold_start_val_cards: int


def temporal_train_val_split(
    df: pd.DataFrame,
    *,
    val_size: float = 0.15,
    unix_time_col: str = "unix_time",
    timestamp_col: str = "trans_date_trans_time",
    id_col: str = "trans_num",
    card_col: str = "cc_num",
) -> TemporalSplitResult:
    """Split a transaction dataset chronologically into Train and Out-of-Time Validation sets.

    Ensures zero temporal leakage: every record in `train_df` occurs on or before the
    temporal split boundary, and every record in `val_df` occurs on or after it.

    Args:
        df: Cleaned transaction DataFrame.
        val_size: Fraction of the latest transactions assigned to the validation split (0 < val_size < 1).
        unix_time_col: Column containing Unix epoch timestamp in seconds.
        timestamp_col: Optional datetime column for human-readable cutoff logging.
        id_col: Tie-breaker transaction identifier column for deterministic ordering.
        card_col: Card identifier column used to report cold-start cards in Validation.

    Returns:
        TemporalSplitResult with `train_df`, `val_df`, and split diagnostics.
    """
    if not (0.0 < val_size < 1.0):
        raise ValueError(f"val_size must be strictly between 0 and 1, got {val_size}")
    if len(df) < 2:
        raise ValueError("DataFrame must contain at least 2 rows to perform a train/val split.")
    if unix_time_col not in df.columns:
        raise ValueError(f"Column '{unix_time_col}' is required for chronological splitting.")

    sort_cols = [unix_time_col]
    if id_col in df.columns:
        sort_cols.append(id_col)

    sorted_df = df.sort_values(by=sort_cols, ascending=True).reset_index(drop=True)

    split_idx = round(len(sorted_df) * (1.0 - val_size))
    split_idx = max(1, min(len(sorted_df) - 1, split_idx))

    train_df = sorted_df.iloc[:split_idx].copy().reset_index(drop=True)
    val_df = sorted_df.iloc[split_idx:].copy().reset_index(drop=True)

    cutoff_unix = int(val_df[unix_time_col].iloc[0])
    cutoff_ts: pd.Timestamp | None = None
    if timestamp_col in val_df.columns:
        cutoff_ts = pd.Timestamp(val_df[timestamp_col].iloc[0])

    cold_start_cards = 0
    if card_col in train_df.columns and card_col in val_df.columns:
        train_cards = set(train_df[card_col].dropna().unique())
        val_cards = set(val_df[card_col].dropna().unique())
        cold_start_cards = len(val_cards - train_cards)

    logger.info(
        "Chronological split complete: train=%s rows | val=%s rows (val_size=%.2f, cutoff=%s, cold_start_cards=%d)",
        f"{len(train_df):,}",
        f"{len(val_df):,}",
        val_size,
        cutoff_ts if cutoff_ts is not None else cutoff_unix,
        cold_start_cards,
    )

    return TemporalSplitResult(
        train_df=train_df,
        val_df=val_df,
        cutoff_unix_time=cutoff_unix,
        cutoff_timestamp=cutoff_ts,
        cold_start_val_cards=cold_start_cards,
    )
