# Pre-E2E Closeout

## Scope

- 실제 마이크 E2E 전까지 완료된 prototype 상태를 정리한다.
- 사용자가 장비 교체 후 바로 테스트할 수 있도록 gate를 명확히 둔다.
- 새로운 기능 구현은 하지 않는다.

## Implemented

- `scripts/stt_codex.py`가 Codex CLI를 child PTY로 실행한다.
- 기본 Codex 실행에는 `--no-alt-screen`을 붙인다.
- parent status line은 `[stt-parent]` prefix로 표시한다.
- 기본 STT trigger는 `ctrl+t`다.
- STT mode는 push-to-talk 녹음 후 raw transcript를 child PTY 입력창에 삽입한다.
- Enter 자동 전송은 하지 않는다.
- 기본 실행에서는 임시 audio를 삭제한다.
- `--save-run`을 켠 경우에만 `output/runs/`에 audio, transcript, metadata를 저장한다.
- `--inject-mode fixed-text`는 PTY injection smoke test 용도로 유지한다.

## Current Baseline

2026-06-20 재검증 기준.

KSS Korean fixture:

- Model: `large-v3`.
- Device: `cuda`.
- Compute type: `float16`.
- PASS 6/6.
- exact 5/6.
- normalized 6/6.

HiKE code-switch fixture:

- Model: `large-v3`.
- Device: `cuda`.
- Compute type: `float16`.
- exact 0/5.
- normalized 0/5.
- Latin token preservation 14/28, 50%.

Phase 16 save-run smoke:

- `skipped_short_recording` 저장 확인.
- `empty_transcript` 저장 확인.
- `audio.wav`, `transcript.txt`, `metadata.json` 생성 확인.

## Verification

```bash
python3 -m py_compile scripts/stt_codex.py
scripts/stt_codex.py --help
git diff --check
scripts/run_fixture_suite.sh fixtures/kss-ko-core-v1.json --model large-v3 --device cuda --compute-type float16
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
```

Result:

- syntax/help/whitespace check 성공.
- KSS fixture PASS 6/6.
- HiKE Latin token preservation 14/28, 50.00%.

## Known Issues Before E2E

- 실제 마이크 입력 품질이 낮으면 STT 결과가 크게 나빠진다.
- `Ctrl+T` trigger는 terminal key repeat와 tmux 설정에 영향을 받는다.
- 한영 혼합 Latin token 보존은 아직 약하다.
- token recovery와 personal vocabulary는 후속 기능이다.
- STT 실행 중 wrapper event loop가 잠시 block될 수 있다.

## E2E Gate

E2E는 장비 교체 후 실제 발화로 수행한다.

통과 기준:

- wrapper 안에서 Codex CLI가 뜬다.
- `Ctrl+T`로 recording start/stop이 보인다.
- 실제 발화 transcript가 Codex CLI 입력창에 삽입된다.
- 자동 Enter가 발생하지 않는다.
- 사용자가 직접 확인 후 Enter를 누를 수 있다.
- 기본 실행에서는 audio/transcript가 남지 않는다.
- `--save-run` 실행에서는 run artifact가 남는다.

## Recommended E2E Command

```bash
scripts/stt_codex.py --save-run --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

마이크 품질 비교가 필요 없으면 `--save-run`을 제거한다.
