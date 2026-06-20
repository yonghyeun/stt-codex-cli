# TypeScript Porting Contract

## Goal

이 repo는 Python/Bash 기반 STT prototype을 TypeScript primary command로 전환한다.

faster-whisper 자체는 Python package이므로 `scripts/transcribe.py`를 STT adapter로
유지한다. 그 외 사용자-facing orchestration과 deterministic helper는 TypeScript를
우선한다.

## Current Ported Surface

- `src/features/transcript-comparison`: Python `scripts/compare_transcript.py`의
  normalize/exact 비교 의미를 TypeScript 순수 함수로 옮긴다.
- `src/features/token-recovery`: manual memory 기반 token recovery 순수 로직.
- `src/features/code-switch-analysis`: Latin token preservation 분석.
- `src/features/audio-recording`: `arecord` command construction과 녹음 helper.
- `src/features/clipboard`: `xclip`/`wl-copy` backend 선택과 command mapping.
- `src/features/stt-adapter`: TypeScript에서 Python faster-whisper adapter를 호출하는 경계.
- `src/features/codex-pty`: key parsing, child argv, run id, trigger split.
- `src/app/cli/*.ts`: 파일 IO, argv parsing, stdout/stderr, exit code를 담당한다.
- `npm run compare-transcript -- expected.txt actual.txt`: normalized 비교.
- `npm run compare-transcript -- --exact expected.txt actual.txt`: exact 비교.
- `npm run stt-codex --`: Codex child PTY와 STT transcript injection primary command.
- `npm run transcribe --`: Python STT adapter 호출 command.
- `npm run record --`, `npm run stt-clipboard --`, `npm run record-clipboard --`,
  `npm run push-to-talk --`: 이전 prototype의 TypeScript command.

## Source Boundary

- `src/app/cli`: argv, file IO, stdout/stderr, exit code.
- `src/features`: 제품 기능 단위의 순수 로직.
- `src/shared`: domain-free helper. 필요할 때만 추가.
- `scripts`: legacy prototype과 Python STT adapter 유지 영역.

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
- 기존 Python/Bash script는 비교 기준으로 유지할 수 있지만 새 검증 surface는 TypeScript command를 우선한다.

기본 검증 명령:

```bash
npm test
npm run typecheck
npm run lint
npm run format:check
```

## Porting Order

1. 결정적 텍스트 비교 로직. 완료.
2. fixture result 분석 로직. 완료.
3. token recovery 관련 순수 로직. 완료.
4. CLI orchestration 보조 레이어. 완료.
5. PTY wrapper와 STT injection. 완료.
6. Python/Bash legacy 제거 여부는 실제 장비 E2E 이후 결정.

## Non-Goals

- faster-whisper 자체를 Node 구현으로 바꾸지 않는다.
- STT 정확도 자체를 개선하지 않는다.
- 실제 장비 E2E 없이 legacy script를 삭제하지 않는다.
