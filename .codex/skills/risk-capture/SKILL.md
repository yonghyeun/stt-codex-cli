---
name: risk-capture
description: Post structured Risk Capture comments to the repo risk inbox when bottlenecks are discovered during slice execution.
---

# Risk Capture

Use when slice work reveals a bottleneck that should be tracked outside the current implementation.

Read:

- `../risk-system/references/risk-lifecycle.md`
- `../risk-system/references/risk-comment-contract.md`

Post to the open `kind:risk-management` inbox issue with:

```bash
.codex/skills/risk-capture/scripts/run.sh \
  --risk-issue <risk-management-inbox-issue> \
  --source-slice <slice-issue> \
  --type bottleneck \
  --severity medium \
  --impact slows-current-slice \
  --handling defer \
  --observation "what was found" \
  --evidence "file, command, error, or issue link" \
  --dry-run
```

Use `--dry-run` before mutation. Use `--yes` for mutation.

`scripts/comment.sh` is the lower-level comment helper.
