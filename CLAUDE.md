# Claude Code Instructions

## Git Workflow

- Always create a worktree
- Always work in a branch
- Branch prefix: feat/ or fix/
- Pull request required
- Squash and merge only

## Commit & Pull RequestIdentity

git config user.name "Claude Code"
git config user.email "<claude-code@automation.local>"

## Commit Convention

Use Conventional Commits:

feat(scope): description      → minor release
fix(scope): description       → patch release
chore(scope): description     → no release (maintenance, deps, config)
chore(ci): description        → no release (CI/CD changes — never use `ci:` alone)
docs(scope): description      → no release
refactor(scope): description  → patch release
perf(scope): description      → patch release

## Pull Request Rules

PR title MUST follow conventional commits.

PR description must contain:

- Summary
- Motivation
- Implementation details

Tests must be done.

CI must pass.

## Project Architecture

Frontend:
will see later but likely:

- Vue 3
- Pinia store
- composables for logic

Backend:

- FastAPI
- service layer
- repository layer

## Coding Rules

- Prefer small PRs
- Do not modify unrelated files
- Write clear commit messages
