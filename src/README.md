# TypeScript Source Contract

`src/`는 새 TypeScript 포팅 코드의 기준 위치다.

TypeScript는 현재 primary command와 feature logic의 기준 위치다.
STT 실행도 TypeScript 경계에서 관리한다. Bash는 compatibility wrapper로만 둔다.

## Layout

```text
src/
  app/
    cli/        # Node CLI entrypoint. 파일 IO, argv, process exit code 담당.
  features/
    <feature>/  # 제품 기능 단위. 순수 로직과 feature-local test 담당.
  shared/       # 도메인 없는 재사용 유틸. 필요할 때만 추가.
```

현재 feature:

- `transcript-comparison`
- `token-recovery`
- `code-switch-analysis`
- `audio-recording`
- `clipboard`
- `stt-engine`
- `codex-pty`

## Rules

- `type: module` 기준 ESM을 사용한다.
- 내부 import는 `@/*` alias를 우선 사용한다.
- exported 함수는 private helper보다 위에 둔다.
- top-level callable은 `function` declaration을 우선한다.
- side effect는 `app/cli` 같은 경계에 둔다.
- `features/**`는 가능한 순수 함수와 값 반환 중심으로 작성한다.
- 오류는 CLI boundary에서 exit code와 stderr로 변환한다.
- Python product script와 Python STT adapter는 유지하지 않는다.

## Tests

- 테스트는 Vitest를 사용한다.
- 동작 변경은 failing test를 먼저 추가한다.
- feature 순수 로직은 `src/features/**`에서 직접 검증한다.
- CLI는 exit code, stdout, stderr처럼 사용자 관찰 결과를 검증한다.
