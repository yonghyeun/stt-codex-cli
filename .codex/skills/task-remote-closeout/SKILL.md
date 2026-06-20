---
name: task-remote-closeout
description: Close completed stt-codex-cli GitHub issues with a closeout comment and status label sync without touching local branches or worktrees.
---

# Task Remote Closeout

Use when the task is complete remotely and no local cleanup is requested.

This skill mutates GitHub issues only. It must not remove worktrees, delete
branches, or edit `stt-codex-cli-worktrees.code-workspace`.

Always dry-run first:

```bash
.codex/skills/task-remote-closeout/scripts/run.sh --issue 55 --body-file /tmp/closeout.md --dry-run
```

Mutation requires explicit confirmation:

```bash
.codex/skills/task-remote-closeout/scripts/run.sh --issue 55 --body-file /tmp/closeout.md --yes
```

Remote closeout does:

- verify the issue exists
- post the supplied closeout comment
- replace any `status:*` label with `status:done`
- close the issue with reason `completed`
- optionally post an umbrella update when `--umbrella <number>` is provided

Use `task-local-closeout` separately when branch/worktree cleanup is needed.
