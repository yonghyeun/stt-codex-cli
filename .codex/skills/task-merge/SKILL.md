---
name: task-merge
description: Merge a stt-codex-cli PR, then orchestrate remote issue closeout and local branch/worktree cleanup through the atomic lifecycle skills.
---

# Task Merge

Use when the user asks to merge a PR and finish the task lifecycle.

This skill is an orchestrator. It must not inline remote issue closeout or local
cleanup logic. It calls:

- `task-remote-closeout` for GitHub issue comment, status sync, and close
- `task-local-closeout` for local branch/worktree/workspace cleanup

Always dry-run first:

```bash
.codex/skills/task-merge/scripts/run.sh \
  --pr 56 \
  --issue 55 \
  --branch feat/55-task-skill-system-bootstrap \
  --body-file /tmp/closeout.md \
  --dry-run
```

Mutation requires explicit confirmation:

```bash
.codex/skills/task-merge/scripts/run.sh \
  --pr 56 \
  --issue 55 \
  --branch feat/55-task-skill-system-bootstrap \
  --body-file /tmp/closeout.md \
  --yes
```

Merge orchestration does:

- verify the PR exists
- report required check status
- squash merge the PR when it is still open
- write the squash merge subject as `land(<type>): <PR-level summary> (#<PR>)`
- skip merge when the PR is already merged
- call `task-remote-closeout`
- call `task-local-closeout`

The landing subject is derived from the PR title. A PR title such as
`chore: PR commit convention 계약 정리` lands as
`land(chore): PR commit convention 계약 정리 (#<PR>)`. The landing body prepends
`Closes #<issue>`, optional `Refs #<umbrella>`, and `PR #<PR>` to the supplied
closeout body.

If a later step fails after merge, rerun the failed atomic skill directly:

- remote issue still open: run `task-remote-closeout`
- local worktree still present: run `task-local-closeout`

Use `--skip-local` only when local cleanup should be deferred. Use
`--skip-checks` only when the repo has no required checks or checks were
verified outside the script.
