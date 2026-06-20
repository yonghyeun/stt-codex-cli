# Codex Agent Contract

이 문서는 `.codex/**` 변경의 1차 계약이다.

## Migrated Surface

- `task-system`은 task 운영 규칙 reference다.
- `task-commit`은 로컬 Git topic commit helper다.
- `task-add`, `task-update`, `task-intake`, `task-pr-create`, `task-merge`,
  `task-remote-closeout`, `task-local-closeout`, `task-not-implemented`는
  GitHub issue/PR lifecycle용 실행 skill이다.
- `risk-system`, `risk-capture`, `risk-intake`, `risk-resolution`은 task 진행 중
  발견한 risk를 원격 issue graph에 연결하기 위한 실행 skill이다.

## Skill Entry Point

- 실행형 skill은 `skills/<skill-name>/scripts/run.sh`를 agent-facing entrypoint로 둔다.
- `scripts/run.sh --help`는 네트워크와 mutation 없이 성공해야 한다.
- mutation 가능 skill은 `--dry-run`을 제공한다.
- mutation 실행은 `--yes` 같은 명시 확인 인자를 요구한다.

## Test Contract

- 복사된 skill은 새 repo에서 동작하는 범위만 유지한다.
- GitHub mutation skill은 항상 `--dry-run`을 먼저 실행한다.
- GitHub mutation 실행은 `--yes` 같은 명시 확인 인자를 요구한다.
