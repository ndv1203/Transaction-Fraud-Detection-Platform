"""Data cleaning, schema standardization, and timestamp parsing for Sparkov data."""

from typing import Any

import pandas as pd

from fraud_detection.config import load_config
from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)


def clean_transactions(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Clean and standardize raw Sparkov transaction data.

    Performs the following operations in-place where possible to minimize RAM:
    1. Drops redundant index columns (`Unnamed: 0`) if present.
    2. Renames SQL-reserved column names (`state` -> `state_code`,
       `long` -> `lon`, `merch_long` -> `merch_lon`).
    3. Parses `trans_date_trans_time` and `dob` into datetime objects.
    4. Removes duplicate transactions based on the unique `trans_num` key.
    5. Sorts transactions chronologically by `unix_time` to prepare for
       time-window feature engineering and out-of-time splitting.

    Args:
        df: Raw transaction DataFrame loaded from `data/raw/`.
        config: Project configuration dictionary. If `None`, loads default
            configuration from `configs/config.yaml`.

    Returns:
        Cleaned and chronologically sorted `pandas.DataFrame`.
    """
    cfg = config or load_config()
    prep_cfg = cfg["preprocessing"]

    # Drop Unnamed: 0 if it was not already excluded during CSV loading.
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Rename columns that collide with SQL keywords for end-to-end consistency.
    rename_map: dict[str, str] = prep_cfg.get("rename_cols", {})
    if rename_map:
        df = df.rename(columns=rename_map)

    id_col = prep_cfg["id_col"]
    timestamp_col = prep_cfg["timestamp_col"]
    unix_time_col = prep_cfg["unix_time_col"]

    # Deduplicate by transaction ID before sorting.
    initial_rows = len(df)
    df = df.drop_duplicates(subset=[id_col], keep="first")
    dropped_dups = initial_rows - len(df)
    if dropped_dups > 0:
        logger.info("Removed %d duplicate transaction rows.", dropped_dups)

    # Parse datetime columns for temporal feature extraction and age calculation.
    if timestamp_col in df.columns:
        df[timestamp_col] = pd.to_datetime(
            df[timestamp_col], format="%Y-%m-%d %H:%M:%S"
        )
    if "dob" in df.columns:
        df["dob"] = pd.to_datetime(df["dob"], format="%Y-%m-%d")

    # Sort chronologically to guarantee causal ordering for rolling velocity features.
    if unix_time_col in df.columns:
        df = df.sort_values(by=[unix_time_col, id_col], kind="mergesort").reset_index(
            drop=True
        )

    mem_mb = df.memory_usage(deep=True).sum() / (1024**2)
    logger.info(
        "Finished cleaning DataFrame: shape=%s, memory=%.2f MB",
        df.shape,
        mem_mb,
    )
    return df
