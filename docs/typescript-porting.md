# TypeScript Porting Contract

## Goal

이 repo는 Python/Bash 기반 STT prototype을 유지하면서, 검증 가능한 보조 로직부터
TypeScript로 점진 포팅한다.

첫 포팅 대상은 deterministic transcript 비교 CLI다. STT runtime,
faster-whisper 호출, PTY wrapper는 이번 범위에서 유지한다.

## Source Boundary

- `src/app/cli`: argv, file IO, stdout/stderr, exit code.
- `src/features`: 제품 기능 단위의 순수 로직.
- `src/shared`: domain-free helper. 필요할 때만 추가.
- `scripts`: 기존 Python/Bash entrypoint 유지 영역.

## Code Guidelines

- TypeScript strict mode를 기본으로 한다.
- ESM만 사용한다.
- top-level callable은 `function` declaration을 우선한다.
- exported API는 private helper보다 먼저 배치한다.
- 함수 추출 기준은 길이가 아니라 의미다.
- hidden mutation과 global state를 피한다.
- side effect는 CLI boundary에 모은다.

## Test Guidelines

- Vitest를 기본 test runner로 사용한다.
- 코드 동작 변경은 failing test를 먼저 작성한다.
- 순수 로직은 fixture 없이 빠르게 검증한다.
- CLI entrypoint는 exit code, stdout, stderr를 관찰 값으로 검증한다.
- 기존 STT fixture regression은 Python/Bash suite를 유지한다.

## Porting Order

1. 결정적 텍스트 비교 로직.
2. fixture result 분석 로직.
3. token recovery 관련 순수 로직.
4. CLI orchestration 보조 레이어.
5. PTY wrapper와 STT runtime은 별도 결정 후 이관.

## Non-Goals

- 이번 단계에서 Python/Bash runtime을 삭제하지 않는다.
- 이번 단계에서 faster-whisper 호출부를 Node로 바꾸지 않는다.
- 이번 단계에서 STT 정확도 자체를 개선하지 않는다.
