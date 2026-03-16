# Claude Code Instructions

## Git Workflow

- Always create a worktree
- Always work in a branch
- Branch prefix: feat/ or fix/
- Pull request required
- Squash and merge only

## Commit Identity

git config user.name "Claude Code"
git config user.email "<claude-code@automation.local>"

## Commit Convention

Use Conventional Commits:

feat(scope): description
fix(scope): description

## Pull Request Rules

PR title MUST follow conventional commits.

PR description must contain:

- Summary
- Motivation
- Implementation details

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
