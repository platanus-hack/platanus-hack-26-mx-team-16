---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
argument-hint: [message]
description: Create a git commit
---

## Context

- Current git status: !`git status`
- Current git diff: !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Based on the above changes, create a single git commit following the **Conventional Commits** specification.

### Commit message format

```
<type>(<scope>): <description>

[optional body]
```

### Rules

1. **type** must be one of: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
2. **scope** is optional but recommended — use the domain or module affected (e.g., `auth`, `transactions`, `ui`)
3. **description** must be lowercase, imperative mood, no period at the end
4. Add a **body** only if the changes need further explanation
5. If the argument `$ARGUMENTS` is provided, use it as guidance for the commit message
6. Do not include any "Co-Authored-By" lines in the commit message
7. Before committing, stage all modified, deleted, and untracked files that are part of the changes using `git add`. Include both tracked changes and new untracked files relevant to the work. Do NOT stage files that contain secrets (`.env`, credentials, etc.)
