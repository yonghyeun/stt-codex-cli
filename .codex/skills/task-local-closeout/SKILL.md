---
name: task-local-closeout
description: Clean up local stt-codex-cli task worktrees, branches, and the generated VS Code workspace without mutating GitHub issues or PRs.
---

# Task Local Closeout

Use when a task is terminal locally and only branch/worktree/workspace cleanup is
needed.

This skill must not mutate GitHub issues or PRs. It may pass `--pr <number>`
only for read-only verification that a squash-merged branch is safe to remove.

Always dry-run first:

```bash
.codex/skills/task-local-closeout/scripts/run.sh --branch feat/55-task-skill-system-bootstrap --pr 56 --dry-run
```

Mutation requires explicit confirmation:

```bash
.codex/skills/task-local-closeout/scripts/run.sh --branch <branch> --yes
```

Local closeout removes:

- the registered task worktree
- the local task branch
- the corresponding folder entry from `stt-codex-cli-worktrees.code-workspace`

Stop by default when:

- target is the main worktree
- worktree is dirty
- branch has unpushed/local-only commits
- path is not a registered worktree
- filesystem removal fails

If cleanup is unsafe, report a pending cleanup receipt.
