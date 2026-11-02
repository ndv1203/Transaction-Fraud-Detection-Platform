# Git Commit & Workflow Guidelines

## 1. Commit message format

Use Conventional Commits:

`<type>(<scope>): <description>`

- Use lowercase types and scopes.
- Write commit messages in English.
- Use imperative, concise descriptions.
- Do not end the subject with a period.
- Keep the subject around 50–72 characters when practical.
- Use a scope when it improves clarity; omit it when unnecessary.

## 2. Allowed commit types

- `feat`: introduce a new feature
- `fix`: correct a bug
- `refactor`: restructure code without changing intended behavior
- `perf`: improve performance
- `test`: add or update tests
- `docs`: update documentation
- `style`: formatting-only changes
- `build`: change dependencies, build tools, or packaging
- `ci`: change CI/CD configuration
- `chore`: maintenance tasks that do not fit the categories above

Choose the type based on the actual changes in the diff, not merely the task description.

## 3. Commit scope

Use a short, meaningful scope representing the affected module or component.

Examples:
- `feat(candidate-detection): add event classifier`
- `fix(data-loader): handle empty input`
- `test(evaluation): cover threshold selection`

Do not invent scopes when the affected area is unclear.

## 4. Atomic commits

- Each commit should represent one coherent logical change.
- Do not combine unrelated features, fixes, formatting, and dependency updates in one commit.
- Split changes into multiple commits when each change can be independently understood and validated.
- Do not create unnecessary commits for trivial intermediate steps.

## 5. Before committing

- Inspect `git status` and the full diff.
- Review staged changes before committing.
- Never include unrelated user changes.
- Never stage the entire repository blindly with `git add .` when unrelated changes may exist.
- Run relevant tests and checks when practical.
- Never claim tests passed unless they were actually executed and passed.
- Report any checks that could not be run.

## 6. Safety and authorization

- Proactively remind user when reaching milestones to commit, branch, or merge.
- Always display exact commands for user to preview and agree before execution.
- Do not commit, amend, reset, rebase, or discard changes unless authorized by the user or clearly permitted by the task.
- Do not rewrite published history without explicit authorization.
- Do not push or create a pull request unless requested.
- Never commit secrets, credentials, local environment files, or generated artifacts unless explicitly required and safe.
- Preserve unrelated changes in the working tree.

## 7. Completion report

After committing, report:
- Commit hash and message
- Summary of changes
- Tests/checks executed and their results
- Any remaining concerns or uncommitted changes

