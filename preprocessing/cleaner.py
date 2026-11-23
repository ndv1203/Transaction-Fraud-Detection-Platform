"""Data cleaning, missing value handling, and timestamp standardization."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_RENAME_COLS: dict[str, str] = {
    "state": "state_code",
    "long": "lon",
    "merch_long": "merch_lon",
}

DEFAULT_DROP_COLS: tuple[str, ...] = ("Unnamed: 0", "first", "last", "street")


def standardize_column_names(
    df: pd.DataFrame,
    rename_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Rename columns that conflict with SQL reserved keywords or naming conventions.

    Default mapping:
        state -> state_code
        long -> lon
        merch_long -> merch_lon
    """
    mapping = rename_map if rename_map is not None else DEFAULT_RENAME_COLS
    active_map = {k: v for k, v in mapping.items() if k in df.columns}
    if active_map:
        df = df.rename(columns=active_map)
    return df


def drop_unused_columns(
    df: pd.DataFrame,
    drop_cols: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Drop index/PII columns configured for removal."""
    cols_to_drop = list(drop_cols) if drop_cols is not None else list(DEFAULT_DROP_COLS)
    existing = [c for c in cols_to_drop if c in df.columns]
    if existing:
        df = df.drop(columns=existing)
    return df


def standardize_timestamps(
    df: pd.DataFrame,
    timestamp_col: str = "trans_date_trans_time",
    dob_col: str = "dob",
) -> pd.DataFrame:
    """Ensure transaction timestamp and date of birth columns are parsed as datetime."""
    out = df.copy()
    if timestamp_col in out.columns and not pd.api.types.is_datetime64_any_dtype(
        out[timestamp_col]
    ):
        out[timestamp_col] = pd.to_datetime(out[timestamp_col], errors="coerce")
    if dob_col in out.columns and not pd.api.types.is_datetime64_any_dtype(out[dob_col]):
        out[dob_col] = pd.to_datetime(out[dob_col], errors="coerce")
    return out


def deduplicate_transactions(
    df: pd.DataFrame,
    id_col: str = "trans_num",
    keep: str = "first",
) -> pd.DataFrame:
    """Deduplicate transactions by unique business key (`trans_num`)."""
    if id_col not in df.columns:
        return df
    before = len(df)
    deduped = df.drop_duplicates(subset=[id_col], keep=keep).reset_index(drop=True)
    removed = before - len(deduped)
    if removed > 0:
        logger.warning("Removed %d duplicate transaction rows by '%s'.", removed, id_col)
    return deduped


def clean_transactions(
    df: pd.DataFrame,
    *,
    rename_map: dict[str, str] | None = None,
    drop_cols: Sequence[str] | None = ("Unnamed: 0",),
    drop_pii: bool = False,
    deduplicate: bool = True,
    id_col: str = "trans_num",
    timestamp_col: str = "trans_date_trans_time",
) -> pd.DataFrame:
    """Execute the core data cleaning and standardization steps on a DataFrame.

    Args:
        df: Input transaction DataFrame.
        rename_map: Column rename mapping (defaults to state->state_code, long->lon, merch_long->merch_lon).
        drop_cols: Columns to drop immediately (defaults to ("Unnamed: 0",)).
        drop_pii: If True, also drops PII columns ("first", "last", "street").
        deduplicate: Whether to drop duplicate rows based on `id_col`.
        id_col: Transaction unique business identifier column.
        timestamp_col: Event timestamp column name.

    Returns:
        Cleaned and standardized DataFrame.
    """
    out = df.copy()
    out = standardize_column_names(out, rename_map=rename_map)

    effective_drop: list[str] = list(drop_cols) if drop_cols is not None else []
    if drop_pii:
        for col in DEFAULT_DROP_COLS:
            if col not in effective_drop:
                effective_drop.append(col)

    out = drop_unused_columns(out, drop_cols=effective_drop)
    out = standardize_timestamps(out, timestamp_col=timestamp_col)

    if deduplicate:
        out = deduplicate_transactions(out, id_col=id_col)

    return out
