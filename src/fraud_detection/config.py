"""Configuration loader and project path management."""

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


def load_config(config_path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    """Load the project YAML configuration file.

    Args:
        config_path: Path to the YAML configuration file. Defaults to
            `configs/config.yaml` at the project root.

    Returns:
        A dictionary containing the parsed configuration parameters.

    Raises:
        FileNotFoundError: If the specified configuration file does not exist.
    """
    resolved_path = Path(config_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)
