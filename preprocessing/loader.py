"""Data loading and saving utilities for raw, interim, and processed datasets."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)

# Memory-efficient dtype mapping for the raw Sparkov Credit Card Fraud CSV files
SPARKOV_DTYPE_MAP: dict[str, str] = {
    "cc_num": "string",
    "merchant": "category",
    "category": "category",
    "amt": "float32",
    "first": "string",
    "last": "string",
    "gender": "category",
    "street": "string",
    "city": "string",
    "state": "category",
    "state_code": "category",
    "zip": "string",
    "lat": "float32",
    "long": "float32",
    "lon": "float32",
    "city_pop": "int32",
    "job": "category",
    "dob": "string",
    "trans_num": "string",
    "unix_time": "int64",
    "merch_lat": "float32",
    "merch_long": "float32",
    "merch_lon": "float32",
    "is_fraud": "int8",
}


def load_raw_csv(
    file_path: str | Path,
    *,
    dtype_map: dict[str, str] | None = None,
    usecols: Sequence[str] | Callable[[str], bool] | None = None,
    nrows: int | None = None,
    parse_dates: bool = True,
) -> pd.DataFrame:
    """Load a raw Sparkov CSV file with memory-optimized data types.

    Args:
        file_path: Path to the CSV file (e.g., fraudTrain.csv or fraudTest.csv).
        dtype_map: Optional custom column dtype mapping. Defaults to SPARKOV_DTYPE_MAP.
        usecols: Optional sequence of column names or predicate to filter columns.
        nrows: Optional limit on the number of rows to read.
        parse_dates: Whether to parse 'trans_date_trans_time' and 'dob' as datetime.

    Returns:
        Loaded pandas DataFrame.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw CSV file not found: {path}")

    effective_dtypes = dtype_map if dtype_map is not None else SPARKOV_DTYPE_MAP
    logger.info("Loading raw CSV from %s (nrows=%s)...", path, nrows)

    df = pd.read_csv(
        path,
        dtype=effective_dtypes,
        usecols=usecols,
        nrows=nrows,
        low_memory=False,
    )

    if parse_dates:
        if "trans_date_trans_time" in df.columns and not pd.api.types.is_datetime64_any_dtype(
            df["trans_date_trans_time"]
        ):
            df["trans_date_trans_time"] = pd.to_datetime(
                df["trans_date_trans_time"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
            )
        if "dob" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["dob"]):
            df["dob"] = pd.to_datetime(df["dob"], format="%Y-%m-%d", errors="coerce")

    mem_mb = df.memory_usage(deep=True).sum() / (1024**2)
    logger.info(
        "Loaded %s rows x %s cols from %s (%.2f MB).",
        f"{len(df):,}",
        df.shape[1],
        path.name,
        mem_mb,
    )
    return df


def save_parquet(
    df: pd.DataFrame,
    file_path: str | Path,
    *,
    compression: str = "snappy",
    index: bool = False,
    **kwargs: Any,
) -> Path:
    """Save a DataFrame to Parquet format, creating parent directories if needed."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, engine="pyarrow", compression=compression, index=index, **kwargs)
    logger.info("Saved DataFrame (%s rows x %s cols) to %s.", f"{len(df):,}", df.shape[1], path)
    return path


def load_parquet(
    file_path: str | Path,
    *,
    columns: Sequence[str] | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Load a DataFrame from a Parquet file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {path}")
    df = pd.read_parquet(path, engine="pyarrow", columns=columns, **kwargs)
    logger.info("Loaded Parquet (%s rows x %s cols) from %s.", f"{len(df):,}", df.shape[1], path)
    return df
