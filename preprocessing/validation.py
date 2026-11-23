"""Data quality and schema validation with non-destructive quarantine reporting.

Follows the 'No Silent Drops' rule (docs/05_pipelines_and_eda.md): invalid or duplicate
records are flagged with detailed reasons rather than silently discarded, so they can
be recorded in `raw.raw_transactions` (`is_valid = FALSE`) and `raw.ingestion_batches`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_CLEANED_COLUMNS: tuple[str, ...] = (
    "trans_date_trans_time",
    "cc_num",
    "merchant",
    "category",
    "amt",
    "gender",
    "city",
    "state_code",
    "zip",
    "lat",
    "lon",
    "city_pop",
    "job",
    "dob",
    "trans_num",
    "unix_time",
    "merch_lat",
    "merch_lon",
)


@dataclass
class ValidationReport:
    """Summary and row-level quarantine details from a batch validation run."""

    input_count: int
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    missing_columns: list[str] = field(default_factory=list)
    error_counts: dict[str, int] = field(default_factory=dict)
    valid_df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    rejected_df: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)

    def to_summary_dict(self) -> dict[str, Any]:
        """Serialize summary statistics for `raw.ingestion_batches.error_summary`."""
        return {
            "input_count": self.input_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "duplicate_count": self.duplicate_count,
            "missing_columns": self.missing_columns,
            "error_counts": self.error_counts,
        }


def validate_transactions(
    df: pd.DataFrame,
    *,
    required_cols: Sequence[str] = REQUIRED_CLEANED_COLUMNS,
    id_col: str = "trans_num",
    require_target: bool = False,
    target_col: str = "is_fraud",
) -> ValidationReport:
    """Validate a standardized transaction DataFrame and split into valid vs. rejected rows.

    Validation rules checked:
        1. Required columns exist and are non-null (`trans_num`, `cc_num`, `amt`, `unix_time`, `trans_date_trans_time`).
        2. `amt > 0` (strictly positive transaction amount).
        3. Valid geographic coordinates: `lat, merch_lat in [-90, 90]`, `lon, merch_lon in [-180, 180]`.
        4. `unix_time > 0`.
        5. Optional target check: `is_fraud in {0, 1}` when `require_target=True` or column is present.
        6. Uniqueness of `trans_num` within the batch (subsequent duplicates are quarantined).

    Args:
        df: Standardized transaction DataFrame (after column renaming).
        required_cols: Sequence of expected column names.
        id_col: Unique transaction identifier column (`trans_num`).
        require_target: Whether `target_col` must be present.
        target_col: Target label column name (`is_fraud`).

    Returns:
        ValidationReport containing `valid_df`, `rejected_df` (with `validation_errors` column),
        and aggregated error counts.
    """
    input_count = len(df)
    expected = list(required_cols)
    if require_target and target_col not in expected:
        expected.append(target_col)

    missing_cols = [c for c in expected if c not in df.columns]
    if missing_cols:
        logger.error("Batch validation failed due to missing columns: %s", missing_cols)
        rejected = df.copy()
        rejected["validation_errors"] = [
            [f"missing_required_columns:{','.join(missing_cols)}"]
        ] * input_count
        return ValidationReport(
            input_count=input_count,
            accepted_count=0,
            rejected_count=input_count,
            duplicate_count=0,
            missing_columns=missing_cols,
            error_counts={"missing_required_columns": input_count},
            valid_df=df.iloc[0:0].copy(),
            rejected_df=rejected,
        )

    if input_count == 0:
        return ValidationReport(
            input_count=0,
            accepted_count=0,
            rejected_count=0,
            duplicate_count=0,
            valid_df=df.copy(),
            rejected_df=df.copy(),
        )

    # Track per-row boolean violation masks
    rule_masks: dict[str, pd.Series] = {}

    critical_not_null = [id_col, "cc_num", "merchant", "category", "amt", "unix_time", "trans_date_trans_time"]
    for col in critical_not_null:
        if col in df.columns:
            mask = df[col].isna()
            if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
                mask = mask | (df[col].astype("string").str.strip() == "")
            if mask.any():
                rule_masks[f"null_or_empty_{col}"] = mask

    if "amt" in df.columns:
        amt_num = pd.to_numeric(df["amt"], errors="coerce")
        invalid_amt = amt_num.isna() | (amt_num <= 0)
        if invalid_amt.any():
            rule_masks["invalid_amt_non_positive"] = invalid_amt

    for lat_col in ("lat", "merch_lat"):
        if lat_col in df.columns:
            lat_num = pd.to_numeric(df[lat_col], errors="coerce")
            invalid_lat = lat_num.isna() | (lat_num < -90.0) | (lat_num > 90.0)
            if invalid_lat.any():
                rule_masks[f"invalid_{lat_col}_range"] = invalid_lat

    for lon_col in ("lon", "merch_lon"):
        if lon_col in df.columns:
            lon_num = pd.to_numeric(df[lon_col], errors="coerce")
            invalid_lon = lon_num.isna() | (lon_num < -180.0) | (lon_num > 180.0)
            if invalid_lon.any():
                rule_masks[f"invalid_{lon_col}_range"] = invalid_lon

    if "unix_time" in df.columns:
        ut_num = pd.to_numeric(df["unix_time"], errors="coerce")
        invalid_ut = ut_num.isna() | (ut_num <= 0)
        if invalid_ut.any():
            rule_masks["invalid_unix_time"] = invalid_ut

    if target_col in df.columns:
        target_num = pd.to_numeric(df[target_col], errors="coerce")
        invalid_target = target_num.isna() | (~target_num.isin([0, 1]))
        if invalid_target.any():
            rule_masks[f"invalid_{target_col}_domain"] = invalid_target

    duplicate_count = 0
    if id_col in df.columns:
        dup_mask = df[id_col].notna() & df.duplicated(subset=[id_col], keep="first")
        duplicate_count = int(dup_mask.sum())
        if duplicate_count > 0:
            rule_masks[f"duplicate_{id_col}"] = dup_mask

    if not rule_masks:
        return ValidationReport(
            input_count=input_count,
            accepted_count=input_count,
            rejected_count=0,
            duplicate_count=0,
            valid_df=df.copy().reset_index(drop=True),
            rejected_df=df.iloc[0:0].copy(),
        )

    combined_invalid = pd.Series(False, index=df.index)
    error_counts: dict[str, int] = {}
    for rule_name, mask in rule_masks.items():
        combined_invalid = combined_invalid | mask
        error_counts[rule_name] = int(mask.sum())

    valid_df = df.loc[~combined_invalid].copy().reset_index(drop=True)
    rejected_df = df.loc[combined_invalid].copy()

    # Build per-row list of triggered validation error strings for rejected rows
    row_errors: list[list[str]] = []
    for idx in rejected_df.index:
        errs = [rule_name for rule_name, mask in rule_masks.items() if bool(mask.loc[idx])]
        row_errors.append(errs)
    rejected_df["validation_errors"] = row_errors
    rejected_df = rejected_df.reset_index(drop=True)

    logger.info(
        "Validation complete: input=%s | accepted=%s | rejected=%s | duplicates=%s",
        f"{input_count:,}",
        f"{len(valid_df):,}",
        f"{len(rejected_df):,}",
        f"{duplicate_count:,}",
    )

    return ValidationReport(
        input_count=input_count,
        accepted_count=len(valid_df),
        rejected_count=len(rejected_df),
        duplicate_count=duplicate_count,
        error_counts=error_counts,
        valid_df=valid_df,
        rejected_df=rejected_df,
    )
