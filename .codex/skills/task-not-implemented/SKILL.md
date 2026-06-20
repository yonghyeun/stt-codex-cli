---
name: task-not-implemented
description: Close intentionally unimplemented stt-codex-cli issues as not planned with a reasoned comment, optional PR close, and no local cleanup.
---

# Task Not Implemented

Use when a task should terminate without implementation.

This is not a failure cleanup skill. It records an explicit decision that the
issue will not be implemented in the current plan. It mutates GitHub issues and,
optionally, an open PR. It must not remove branches, worktrees, or generated
workspace entries.

Always dry-run first:

```bash
.codex/skills/task-not-implemented/scripts/run.sh --issue 55 --body-file /tmp/not-implemented.md --dry-run
```

Mutation requires explicit confirmation:

```bash
.codex/skills/task-not-implemented/scripts/run.sh --issue 55 --body-file /tmp/not-implemented.md --yes
```

Not-implemented closeout does:

- verify the issue exists
- post the supplied reason comment
- replace any `status:*` label with `status:done`
- add `wontfix` by default
- close the issue with reason `not planned`
- optionally comment on and close an open PR when `--pr <number>` is provided

Use `task-local-closeout` separately when branch/worktree cleanup is needed.
