# Scripts

`scripts/`는 compatibility wrapper만 둔다.

Primary 사용자-facing command는 repo root의 `npm run ...` TypeScript command다.

## Primary Commands

```bash
npm run stt-codex --
npm run transcribe -- audio.wav --model tiny --device cpu
npm run record --
npm run stt-clipboard -- audio.wav
npm run record-clipboard -- --duration 3
npm run recover-tokens -- --fixture fixtures/token-recovery-v1.json
npm run compare-transcript -- expected.txt actual.txt
npm run run-fixture-suite -- fixtures/kss-ko-core-v1.json --model tiny --device cpu
npm run analyze-code-switch-suite -- output/suite/result.json
```

## Compatibility Wrappers

남아 있는 `.sh` 파일은 legacy 구현이 아니라 TS command forwarding layer다.

- `scripts/record.sh` -> `npm run record --`
- `scripts/copy_text.sh` -> `npm run copy-text --`
- `scripts/stt_clipboard.sh` -> `npm run stt-clipboard --`
- `scripts/record_clipboard.sh` -> `npm run record-clipboard --`
- `scripts/run_fixture_suite.sh` -> `npm run run-fixture-suite --`
- `scripts/transcribe.sh` -> `npm run transcribe --`

## STT Engine

STT 실행은 `npm run transcribe --` TypeScript command가 담당한다.

내부 구현은 npm dependency `nodejs-whisper`의 번들 `whisper.cpp` CLI를 사용한다.
Python adapter와 pip requirements는 유지하지 않는다.

기본 model cache 위치는 `output/models/whisper.cpp`다.

CUDA 실행이 필요하면 `--device cuda` 또는 `--stt-device cuda`를 사용한다.
이 경우 local CMake/CUDA build가 필요하다.
