---
name: risk-resolution
description: Select captured risks from risk-intake output and route them to issue-backed resolution work with inbox start and closeout comments.
---

# Risk Resolution

Use after `risk-intake` identifies risks worth resolving.

Read:

- `../risk-system/references/risk-lifecycle.md`
- `../risk-system/references/risk-comment-contract.md`

Workflow:

1. Read risk intake summary.
2. Select one or more captured risks.
3. Decide target:
   - existing slice
   - new leaf issue
   - standalone issue
   - `kind:risk-resolution` issue
4. Post a resolution-start comment to the risk inbox issue.
5. Execute issue-backed work through `task-intake`.
6. Post resolution closeout to the risk inbox issue.
7. Propagate summary to umbrella when multiple leaves or shared plan context changed.

Use the script for the risk-resolution execution surface:

```bash
.codex/skills/risk-resolution/scripts/run.sh --mode issue-body --help
.codex/skills/risk-resolution/scripts/run.sh --mode start --help
.codex/skills/risk-resolution/scripts/run.sh --mode closeout --help
```

Issue creation stays in `task-add`:

```bash
.codex/skills/task-add/scripts/run.sh --kind risk-resolution ...
```

Start implementation with `task-intake` after the risk-resolution issue exists.

Do not silently fold unrelated risk work into the current slice.
