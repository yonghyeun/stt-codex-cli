# Commit Convention

## Topic Commit Subject

Use:

```text
<type>: <한국어 요약>
```

Allowed types:

- `feat`
- `fix`
- `docs`
- `test`
- `chore`
- `refactor`
- `design`
- `infra`

Topic commits describe one reviewable branch work unit. Keep the conventional
commit type prefix, but write the summary in Korean prose. They are allowed to
use the standard type prefix because they are not the main-branch landing marker.

## Language

- Commit subject와 body는 가능한 한 한국어로 작성한다.
- Conventional commit type, path, command, label, URL, code identifier, product
  name, quoted error는 원문 표기를 유지할 수 있다.
- 기술 literal을 어색하게 번역하지 않는다. 대신 literal 주변의 설명을
  한국어 문장으로 작성한다.

## Landing Commit Subject

For PR squash merge commits that land on `main`, use:

```text
land(<type>): <PR-level summary> (#<PR number>)
```

Examples:

```text
land(chore): PR landing commit 규약 정리 (#130)
land(feat): attachment cleanup plan surface 추가 (#117)
land(refactor): note contract source 정리 (#102)
```

Rules:

- `land(...)` marks a main-branch landing commit in Git graph views.
- `<type>` reuses the topic commit type list above.
- `<PR-level summary>` describes the whole PR, not one internal topic commit.
- `#<PR number>` identifies the landed review surface.
- Issue and risk references belong in the body, not the subject.

## Body

For agent-authored task commits, include:

```text
의도:
- <왜 이 커밋이 필요한가>

범위:
- <어디를 바꿨는가>

변경:
- <무엇을 바꿨는가>

방식:
- <어떻게 해결했는가>

검증:
- <명령, dry-run, 수동 확인, 또는 생략 사유>

리스크:
- <남은 위험, 의도적 미해결, 주의점>

후속:
- <없음 또는 issue/risk link>
```

Use `task-commit` for agent-authored topic commits when possible:

```bash
.codex/skills/task-commit/scripts/run.sh --dry-run ...
.codex/skills/task-commit/scripts/run.sh --yes ...
```

For landing commits, the body must include:

```text
Closes #<issue>
Refs #<umbrella-or-risk-issue>
PR #<pr>

<closeout body>
```

## Slice Rules

- One commit should represent one reviewable unit.
- Do not mix implementation and unrelated cleanup.
- Do not hide risk discovery inside an implementation commit.
- If a bottleneck is not solved in the current slice, record it in the issue,
  experiment note, follow-up task, or `risk-capture` when it affects the shared
  risk inbox.
- Topic commits and landing commits serve different history roles. Do not use
  `land(...)` for branch-local topic commits.
