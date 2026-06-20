# README And AGENTS Boundary

## README

README files describe repo content and local folder context.

Use README files for:

- STT prototype architecture and product contract
- script usage and verification commands
- experiment record placement
- generated output boundaries

## AGENTS

Root `AGENTS.md` stays scoped to repo routing rules and changed-path reading
requirements.

`.codex/AGENTS.md` stays scoped to repo-local skill and task lifecycle rules.

Do not add GitHub lifecycle details to unrelated feature docs unless explicitly
needed for the task.

## Skills

Repo task operating contracts live under:

```text
.codex/skills/**
```

Detailed operating references live under each skill's `references/` folder.

Do not create `docs/operations` for this task system.
