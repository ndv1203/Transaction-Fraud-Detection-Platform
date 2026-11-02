"""Unit tests for the data loader and transaction cleaner modules."""

from pathlib import Path

import pandas as pd

from preprocessing.cleaner import clean_transactions
from preprocessing.loader import load_parquet, load_raw_csv, save_parquet


def test_clean_transactions_renames_and_deduplicates() -> None:
    """Verify column renaming, deduplication, and chronological sorting."""
    raw_df = pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2],
            "trans_num": ["tx_2", "tx_1", "tx_1"],
            "trans_date_trans_time": [
                "2020-01-01 00:05:00",
                "2020-01-01 00:01:00",
                "2020-01-01 00:01:00",
            ],
            "unix_time": [1577837100, 1577836860, 1577836860],
            "cc_num": ["1111", "2222", "2222"],
            "merchant": ["merch_a", "merch_b", "merch_b"],
            "category": ["grocery_pos", "shopping_net", "shopping_net"],
            "amt": [15.5, 250.0, 250.0],
            "state": ["NY", "CA", "CA"],
            "lat": [40.7, 34.0, 34.0],
            "long": [-74.0, -118.2, -118.2],
            "merch_lat": [40.8, 34.1, 34.1],
            "merch_long": [-74.1, -118.3, -118.3],
            "dob": ["1990-05-10", "1985-11-20", "1985-11-20"],
            "is_fraud": [0, 1, 1],
        }
    )

    cleaned_df = clean_transactions(raw_df)

    # 'Unnamed: 0' should be removed and duplicate 'tx_1' should be dropped.
    assert "Unnamed: 0" not in cleaned_df.columns
    assert len(cleaned_df) == 2

    # SQL-reserved column names must be standardized.
    assert "state_code" in cleaned_df.columns
    assert "lon" in cleaned_df.columns
    assert "merch_lon" in cleaned_df.columns
    assert "state" not in cleaned_df.columns
    assert "long" not in cleaned_df.columns
    assert "merch_long" not in cleaned_df.columns

    # Rows must be sorted chronologically by unix_time ('tx_1' before 'tx_2').
    assert list(cleaned_df["trans_num"]) == ["tx_1", "tx_2"]
    assert pd.api.types.is_datetime64_any_dtype(cleaned_df["trans_date_trans_time"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned_df["dob"])


def test_load_raw_csv_and_parquet_roundtrip(tmp_path: Path) -> None:
    """Verify memory-efficient CSV loading and Parquet serialization."""
    csv_file = tmp_path / "sample.csv"
    pd.DataFrame(
        {
            "Unnamed: 0": [0],
            "trans_num": ["tx_100"],
            "trans_date_trans_time": ["2020-06-01 12:00:00"],
            "unix_time": [1591012800],
            "cc_num": ["9999"],
            "merchant": ["fraud_Store"],
            "category": ["misc_net"],
            "amt": [99.95],
            "first": ["John"],
            "last": ["Doe"],
            "gender": ["M"],
            "street": ["123 Main St"],
            "city": ["Austin"],
            "state": ["TX"],
            "zip": ["78701"],
            "lat": [30.26],
            "long": [-97.74],
            "city_pop": [950000],
            "job": ["Engineer"],
            "dob": ["1992-03-15"],
            "merch_lat": [30.30],
            "merch_long": [-97.70],
            "is_fraud": [0],
        }
    ).to_csv(csv_file, index=False)

    df_loaded = load_raw_csv(csv_file)
    assert "Unnamed: 0" not in df_loaded.columns
    assert df_loaded["amt"].dtype == "float32"
    assert df_loaded["is_fraud"].dtype == "int8"

    parquet_file = tmp_path / "sample.parquet"
    save_parquet(df_loaded, parquet_file)
    df_reloaded = load_parquet(parquet_file)
    assert len(df_reloaded) == 1
    assert df_reloaded.loc[0, "trans_num"] == "tx_100"
