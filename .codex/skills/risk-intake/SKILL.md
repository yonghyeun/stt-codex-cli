---
name: risk-intake
description: Read risk inbox comments through REST gh api and summarize captured bottlenecks without mutating GitHub.
---

# Risk Intake

Use when selecting which captured risks should become resolution work.

Run:

```bash
.codex/skills/risk-intake/scripts/run.sh --risk-issue <risk-management-inbox-issue>
```

The script reads the singleton inbox comments and prints captured risks grouped by status, type,
severity, and source slice. It does not mutate GitHub.

`scripts/read-comments.sh` is the lower-level comment reader.
