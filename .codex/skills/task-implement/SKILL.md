---
name: task-implement
description: Execute issue-backed stt-codex-cli implementation as atomic phases with TDD-first changes, focused verification, task-commit checkpoints, and systemic risk capture.
---

# Task Implement

Use after `task-intake` has prepared an isolated worktree for an executable
issue.

This skill is a workflow gate. It does not replace `task-intake`,
`task-commit`, `risk-capture`, or `task-pr-create`; it fixes the order in which
they are used during implementation.

Read:

- `../task-system/references/commit-convention.md`
- `../risk-system/references/risk-lifecycle.md` when systemic risk is found
- `../risk-system/references/risk-comment-contract.md` when posting a risk

## Workflow

```text
task-intake
-> phase plan
-> phase loop:
   1. confirm phase goal
   2. write failing test first when code behavior changes
   3. implement the smallest bounded change
   4. run focused verification
   5. if systemic risk is found:
      risk-capture -> risk inbox
      decide continue / stop / risk-resolution
   6. task-commit
-> final verification
-> task-pr-create
```

## Phase Plan

Before editing files, print the implementation phases with:

- phase title
- intent
- expected files
- TDD or test-skip reason
- focused verification command
- expected `task-commit` subject
- completion condition

## Phase Rules

- Each atomic phase closes with `task-commit`.
- Code behavior changes start with a failing test when practical.
- If TDD is not practical, record the test-skip reason in the phase plan and
  commit body.
- Focused verification runs before each `task-commit`.
- Final verification runs before `task-pr-create`.
- Do not leave broad uncommitted diffs across HIL boundaries.

## Risk Rules

`risk-capture` is a systemic risk control record, not a follow-up todo log.
Run it only in the phase where the systemic risk is found.

Use `risk-capture` when:

- the same problem can repeat across future slices
- the agent workflow is unstable
- a verification surface is missing
- lifecycle skills do not protect the real workflow
- an architecture or contract risk affects multiple leaves
- HIL intervention would break traceability or rollback

After capture, decide current-slice impact:

- `none`: keep working after recording
- `affects-future-slice`: keep working after recording
- `slows-current-slice`: recover minimally, then keep working
- `blocks-current-slice`: stop and consider `risk-resolution`

## Comment Rules

- Do not use `task-update` for every phase.
- Phase progress is tracked by `task-commit` history.
- Review progress is summarized in the PR body.
- GitHub comments are reserved for scope changes, HIL blockers, risk captures,
  risk-resolution lifecycle, PR creation, and closeout.

## PR Body Expectation

The PR body should summarize the review surface:

```text
Phase commits:
- Phase 1: <commit> / <focused verification>
- Phase 2: <commit> / <focused verification>

Final verification:
- <command or skip reason>

Captured risks:
- <risk-capture link or none>
```

Use the script to print the checklist for the current issue:

```bash
.codex/skills/task-implement/scripts/run.sh --mode checklist --issue 146 --dry-run
```
