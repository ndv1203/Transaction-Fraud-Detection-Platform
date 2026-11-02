# Workspace Agent Rules Router

Keep system prompt context minimal. Follow these primary directives and read specific guidelines on-demand:

## 1. Tooling & Coding Standards
- **Exclusively `uv`**: Always use `uv` commands (`uv add`, `uv run`, `uv sync`). Never use `pip`, `conda`, or `poetry`.
- **Google Style**: Strictly write comments and docstrings adhering to Google Python Style Guide (`Args:`, `Returns:`, `Raises:`).
- **Trigger**: When writing code, tests, or managing dependencies, read [.agents/guidelines/coding-standards.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/.agents/guidelines/coding-standards.md) for full formatting details.

## 2. Git Workflow & Commits
- **Conventional Commits**: Always format commits as `<type>(<scope>): <description>`.
- **Safety First**: Proactively remind user at milestones. Always show exact commands for user preview and approval before executing any state-changing Git command.
- **Trigger**: Before staging, committing, branching, or merging, read [.agents/guidelines/git-commit.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/.agents/guidelines/git-commit.md) for allowed types, scopes, atomic commit rules, and completion reporting format.

