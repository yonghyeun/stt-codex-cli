# Scripts

`scripts/`는 compatibility wrapper와 Python STT adapter만 둔다.

Primary 사용자-facing command는 repo root의 `npm run ...` TypeScript command다.

## Primary Commands

```bash
npm run stt-codex --
npm run transcribe -- audio.wav --model tiny --device cpu --compute-type int8
npm run record --
npm run stt-clipboard -- audio.wav
npm run record-clipboard -- --duration 3
npm run recover-tokens -- --fixture fixtures/token-recovery-v1.json
npm run compare-transcript -- expected.txt actual.txt
npm run run-fixture-suite -- fixtures/kss-ko-core-v1.json --model tiny --device cpu --compute-type int8
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

## Python Boundary

`scripts/transcribe.py`만 Python으로 남긴다.

이 파일은 faster-whisper package를 호출하는 adapter다. TypeScript command
`npm run transcribe --`와 `npm run stt-codex --`는 이 adapter를 통해 로컬 STT를 실행한다.

STT Python runtime 탐색 순서:

1. `STT_PYTHON`
2. 현재 worktree의 `.venv/bin/python`
3. main worktree의 `.venv/bin/python`
4. `python3`

Python adapter setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

CUDA 실행이 필요하면 추가 설치한다.

```bash
.venv/bin/pip install -r requirements-cuda.txt
```
