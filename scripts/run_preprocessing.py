"""CLI entrypoint for downloading, cleaning, and preparing Sparkov datasets."""

import gc
import sys
from pathlib import Path

# Ensure both project root (for `preprocessing`) and `src` (for `fraud_detection`)
# are importable when executing this script directly via `uv run python scripts/...`.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fraud_detection.config import PROJECT_ROOT, load_config  # noqa: E402
from fraud_detection.utils.logger import get_logger  # noqa: E402
from preprocessing.cleaner import clean_transactions  # noqa: E402
from preprocessing.loader import (  # noqa: E402
    download_and_extract_raw_data,
    load_raw_csv,
    save_parquet,
)

logger = get_logger(__name__)


def main() -> None:
    """Execute the raw data download, cleaning, and Parquet conversion workflow."""
    config = load_config()
    interim_dir = PROJECT_ROOT / config["paths"]["interim_data"]
    interim_dir.mkdir(parents=True, exist_ok=True)

    train_csv_path, test_csv_path = download_and_extract_raw_data(config=config)

    # Process train and test splits sequentially and trigger garbage collection
    # between splits to keep peak memory consumption safe on 8GB RAM machines.
    for split_name, csv_path in [("train", train_csv_path), ("test", test_csv_path)]:
        output_parquet = interim_dir / f"{split_name}_cleaned.parquet"
        logger.info("Processing '%s' split from %s...", split_name, csv_path.name)

        df_raw = load_raw_csv(csv_path)
        df_clean = clean_transactions(df_raw, config=config)
        save_parquet(df_clean, output_parquet)

        del df_raw, df_clean
        gc.collect()

    logger.info("Preprocessing stage (raw -> interim Parquet) completed successfully.")


if __name__ == "__main__":
    main()
