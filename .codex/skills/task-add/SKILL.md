---
name: task-add
description: Create a GitHub umbrella, leaf, standalone, risk-management, or risk-resolution issue for stt-codex-cli through the repo-local issue contract and REST gh api scripts.
---

# Task Add

Create one issue in the repo task graph or risk inbox graph.

Read `../task-system/references/issue-system.md` and `../task-system/references/label-taxonomy.md` when the issue shape or labels are unclear.

Use the script for issue creation:

```bash
.codex/skills/task-add/scripts/run.sh \
  --kind standalone \
  --title "chore: example" \
  --body-file /tmp/body.md \
  --label type:chore \
  --label kind:standalone \
  --label status:intake \
  --label priority:p2 \
  --label area:ops \
  --dry-run
```

Use `--dry-run` before mutation. Use `--yes` for mutation.

`scripts/create-issue.sh` is the lower-level issue creation helper.

Do not call `gh issue create` directly for normal task-add work.
The script uses REST `gh api`.

## Body Language

- Issue body prose is Korean-first.
- Keep established section headings such as `## Context`, `## Scope`, and `## Acceptance Criteria`.
- English is acceptable for paths, commands, labels, URLs, code identifiers, product names, and quoted evidence.
- `task-add` rejects a body file with no Korean characters so a fully English body does not get created silently.

## Kinds

- `umbrella`: parent tracking issue.
- `leaf`: one executable child issue. Requires `--parent #<umbrella>`.
- `standalone`: one bounded executable issue without a parent.
- `risk-management`: singleton repo-level risk capture inbox. Do not run `task-intake` on this kind.
- `risk-resolution`: one bounded issue for selected captured risks.

## Stop

- Missing source context.
- Missing required body sections.
- Labels do not match taxonomy.
- Leaf has no open `kind:umbrella` parent.
- Standalone has a parent.
- Risk-management issue is used as executable implementation work.
- An open `kind:risk-management` inbox already exists.
