"""CLI entrypoint for running the data preprocessing and validation pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from fraud_detection.config import load_config
from fraud_detection.utils.logger import get_logger
from preprocessing.pipeline import process_raw_file

logger = get_logger("scripts.run_preprocessing")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Sparkov CSV preprocessing, schema validation, and Parquet conversion."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional custom path to config.yaml.",
    )
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Optional limit on number of rows to process per file (useful for smoke tests).",
    )
    parser.add_argument(
        "--drop-pii",
        action="store_true",
        help="Drop PII columns (first, last, street) when writing interim Parquet.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config) if args.config else load_config()

    datasets = [
        (cfg.paths.raw_data / "fraudTrain.csv", cfg.paths.interim_data / "train_cleaned.parquet"),
        (cfg.paths.raw_data / "fraudTest.csv", cfg.paths.interim_data / "test_cleaned.parquet"),
    ]

    for raw_csv, out_parquet in datasets:
        if not raw_csv.exists():
            logger.warning("Skipping missing raw dataset: %s", raw_csv)
            continue
        res = process_raw_file(
            raw_csv,
            output_parquet_path=out_parquet,
            settings=cfg,
            drop_pii=args.drop_pii,
            nrows=args.nrows,
        )
        logger.info("Summary for %s: %s", raw_csv.name, res.validation_report.to_summary_dict())


if __name__ == "__main__":
    main()
