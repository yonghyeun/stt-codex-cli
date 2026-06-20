---
name: task-commit
description: Create a Korean topic commit for one reviewable STT experiment task work unit using the repo commit convention.
---

# Task Commit

Use when staged changes are ready to become one topic commit.

Commit subject와 body는 가능한 한 한국어로 작성한다. Path, command, label,
URL, code identifier 같은 기술 literal은 원문 표기를 유지하고, 주변 설명을
한국어 문장으로 작성한다.

Read:

- `../task-system/references/commit-convention.md`

Always dry-run first:

```bash
.codex/skills/task-commit/scripts/run.sh \
  --type chore \
  --subject "작업 단위 커밋 스킬 추가" \
  --intent "커밋 단위의 판단 근거를 body에 남기기 위함" \
  --scope ".codex/skills/task-commit" \
  --change "topic commit 메시지 생성 스킬을 추가" \
  --approach "정책 reference를 실행형 wrapper로 감싸고 dry-run을 제공" \
  --verification "scripts/run.test.sh 통과" \
  --risk "기존 커밋에는 소급 적용하지 않음" \
  --follow-up "없음" \
  --dry-run
```

Mutation requires staged changes and explicit confirmation:

```bash
.codex/skills/task-commit/scripts/run.sh \
  --type chore \
  --subject "작업 단위 커밋 스킬 추가" \
  --intent "커밋 단위의 판단 근거를 body에 남기기 위함" \
  --scope ".codex/skills/task-commit" \
  --change "topic commit 메시지 생성 스킬을 추가" \
  --approach "정책 reference를 실행형 wrapper로 감싸고 dry-run을 제공" \
  --verification "scripts/run.test.sh 통과" \
  --risk "기존 커밋에는 소급 적용하지 않음" \
  --follow-up "없음" \
  --yes
```

This skill creates branch-local topic commits only. Do not use it for PR squash
landing commits. Use `task-merge` for landing commits.
