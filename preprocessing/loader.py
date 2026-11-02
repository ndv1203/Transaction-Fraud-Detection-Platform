"""Data loading, Google Drive archive extraction, and memory-optimized I/O."""

import shutil
import zipfile
from pathlib import Path
from typing import Any

import gdown
import pandas as pd

from fraud_detection.config import PROJECT_ROOT, load_config
from fraud_detection.utils.logger import get_logger

logger = get_logger(__name__)

# Downcast numeric types during CSV parsing to keep peak memory under ~300MB on 8GB RAM.
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
    "zip": "string",
    "lat": "float32",
    "long": "float32",
    "city_pop": "int32",
    "job": "category",
    "dob": "string",
    "trans_num": "string",
    "unix_time": "int64",
    "merch_lat": "float32",
    "merch_long": "float32",
    "is_fraud": "int8",
}


def download_and_extract_raw_data(
    config: dict[str, Any] | None = None,
    force_download: bool = False,
) -> tuple[Path, Path]:
    """Download the Sparkov zip archive from Google Drive and extract CSV files.

    Checks whether `fraudTrain.csv` and `fraudTest.csv` already exist in
    `data/raw/` before downloading to prevent duplicate downloads or overwrites.

    Args:
        config: Project configuration dictionary. If `None`, loads default
            configuration from `configs/config.yaml`.
        force_download: Whether to re-download and re-extract even if raw CSV
            files already exist on disk. Defaults to `False`.

    Returns:
        A tuple of `(train_csv_path, test_csv_path)` pointing to the extracted
        files inside `data/raw/`.

    Raises:
        RuntimeError: If the download fails or expected CSV files are missing
            after archive extraction.
    """
    cfg = config or load_config()
    raw_dir = PROJECT_ROOT / cfg["paths"]["raw_data"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_cfg = cfg["data_source"]
    train_csv_path = raw_dir / source_cfg["train_csv"]
    test_csv_path = raw_dir / source_cfg["test_csv"]

    # Skip download and extraction if both raw CSV files already exist on disk.
    if not force_download and train_csv_path.exists() and test_csv_path.exists():
        logger.info(
            "Raw dataset files already exist in %s. Skipping download.",
            raw_dir,
        )
        return train_csv_path, test_csv_path

    archive_path = raw_dir / source_cfg["archive_name"]
    file_id = source_cfg["gdrive_file_id"]

    if not archive_path.exists() or force_download:
        logger.info(
            "Downloading dataset archive from Google Drive (ID: %s) to %s...",
            file_id,
            archive_path,
        )
        downloaded_path = gdown.download(
            id=file_id,
            output=str(archive_path),
            quiet=False,
            fuzzy=True,
        )
        if not downloaded_path or not archive_path.exists():
            raise RuntimeError(
                "Failed to download archive from Google Drive. Verify that the "
                "file sharing permission is set to 'Anyone with the link'."
            )

    logger.info("Extracting %s into %s...", archive_path.name, raw_dir)
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            if member.is_dir():
                continue
            # Flatten nested directory structures inside the zip into data/raw/.
            target_filename = Path(member.filename).name
            if not target_filename:
                continue
            target_path = raw_dir / target_filename
            with zip_ref.open(member) as source_stream, target_path.open(
                "wb"
            ) as target_file:
                shutil.copyfileobj(source_stream, target_file)

    if source_cfg.get("remove_zip_after_extract", True) and archive_path.exists():
        logger.info(
            "Removing temporary zip archive %s to save disk space.",
            archive_path,
        )
        archive_path.unlink()

    if not train_csv_path.exists() or not test_csv_path.exists():
        extracted_files = [p.name for p in raw_dir.iterdir() if p.is_file()]
        raise RuntimeError(
            f"Expected '{train_csv_path.name}' and '{test_csv_path.name}' in "
            f"{raw_dir}, but found: {extracted_files}"
        )

    logger.info(
        "Successfully prepared raw CSV files: %s, %s",
        train_csv_path.name,
        test_csv_path.name,
    )
    return train_csv_path, test_csv_path


def load_raw_csv(csv_path: Path | str, nrows: int | None = None) -> pd.DataFrame:
    """Load a raw Sparkov CSV file with memory-efficient data types.

    Args:
        csv_path: Path to the CSV file (`fraudTrain.csv` or `fraudTest.csv`).
        nrows: Optional maximum number of rows to read (useful for quick testing).

    Returns:
        A `pandas.DataFrame` with downcasted numeric and categorical columns.

    Raises:
        FileNotFoundError: If `csv_path` does not exist.
    """
    resolved_path = Path(csv_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"CSV file not found: {resolved_path}")

    logger.info("Loading CSV file from %s...", resolved_path)
    # Exclude 'Unnamed: 0' index column during read to avoid allocating extra memory.
    df = pd.read_csv(
        resolved_path,
        dtype=SPARKOV_DTYPE_MAP,
        usecols=lambda col: col != "Unnamed: 0",
        nrows=nrows,
        low_memory=False,
    )
    mem_mb = df.memory_usage(deep=True).sum() / (1024**2)
    logger.info(
        "Loaded %s: shape=%s, memory=%.2f MB",
        resolved_path.name,
        df.shape,
        mem_mb,
    )
    return df


def save_parquet(df: pd.DataFrame, output_path: Path | str) -> Path:
    """Save a DataFrame to disk in Apache Parquet format.

    Args:
        df: DataFrame to persist.
        output_path: Destination file path (`.parquet`).

    Returns:
        Resolved `Path` to the written Parquet file.
    """
    resolved_path = Path(output_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(resolved_path, engine="pyarrow", compression="snappy", index=False)
    logger.info("Saved Parquet file to %s (shape=%s)", resolved_path, df.shape)
    return resolved_path


def load_parquet(parquet_path: Path | str) -> pd.DataFrame:
    """Load a DataFrame from an Apache Parquet file.

    Args:
        parquet_path: Path to the `.parquet` file.

    Returns:
        Loaded `pandas.DataFrame`.

    Raises:
        FileNotFoundError: If `parquet_path` does not exist.
    """
    resolved_path = Path(parquet_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {resolved_path}")

    df = pd.read_parquet(resolved_path, engine="pyarrow")
    logger.info("Loaded Parquet file from %s (shape=%s)", resolved_path, df.shape)
    return df
