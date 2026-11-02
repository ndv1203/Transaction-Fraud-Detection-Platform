# Package Management & Coding Standards

## 1. Use `uv` Exclusively (No `pip`)
- **Mandatory Tooling**: Always use `uv` throughout the entire project instead of `pip`, `venv`, `pip-tools`, `poetry`, or `conda`.
- **Command Conventions**:
  - Adding dependencies: `uv add <package>` (or `uv add --dev <package>` for development tools).
  - Removing dependencies: `uv remove <package>`.
  - Syncing environment: `uv sync`.
  - Running scripts, tests, and tools: `uv run <command>` (e.g., `uv run pytest`, `uv run ruff check`, `uv run python scripts/run_preprocessing.py`).
- **Prohibition**: Never run or suggest `pip install` or `python -m pip` in terminal commands, Dockerfiles, CI/CD workflows, or documentation.

## 2. Google Style Guide for Comments & Docstrings
- **Docstring Format**: All Python modules, classes, functions, and methods must use **Google-style docstrings** (`"""..."""`) with standard sections where applicable:
  - One-line summary (imperative mood, ending with a period), followed by a blank line and optional detailed description.
  - `Args:`: Parameter names, types (if not already clear from type hints), and descriptions.
  - `Returns:`: Return type and description of the returned value.
  - `Raises:`: Exceptions that may be raised and under what conditions.
  - `Attributes:`: Public class/instance attributes for classes.
- **Inline & Block Comments**:
  - Follow Google Python Style Guide conventions: start with `# ` (a hash and a single space), indent to the same level as the code being described, and leave at least two spaces before inline comments.
  - Focus comments on explaining *why* a decision or algorithm is used (e.g., memory optimization for 8GB RAM, preventing data leakage), rather than restating *what* trivial code does.

