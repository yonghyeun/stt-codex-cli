# Worktree And VS Code Workspace

All paths are relative to repo root `.` unless explicitly stated otherwise.

## Default Shape

- Branch: `feat/<issue>-<slug>` for feature/refactor/chore work.
- Worktree: sibling path `../<repo-name>-issue-<issue>-<slug>`.
- Base: `origin/main`.
- Workspace file: `./<repo-name>-worktrees.code-workspace`.

## Workspace File

The workspace file is generated from:

```bash
git worktree list --porcelain
```

The file contains local absolute paths and should stay ignored.

## Intake

Use `task-intake` for issue-backed worktree setup.

Raw `git worktree add` is fallback only when the script is broken.

## Cleanup

Use `task-local-closeout` for branch/worktree cleanup after PR merge or explicit closeout.

Cleanup order:

1. Fetch/prune.
2. Detect registered worktrees.
3. Detect branch occupancy.
4. Refuse dirty or unpushed worktrees by default.
5. Remove clean task worktree.
6. Delete local branch.
7. Prune worktrees.
8. Regenerate workspace.
