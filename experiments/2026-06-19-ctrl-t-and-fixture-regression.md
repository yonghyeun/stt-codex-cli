# Ctrl+T Trigger and Fixture Regression

## Scope

- `scripts/stt_codex.py` STT mode 기본 trigger를 `ctrl+t`로 바꾼다.
- 마이크 입력 품질과 분리해 fixture 기준 STT 성능을 다시 확인한다.

## Decision

- STT mode 기본 trigger는 `ctrl+t`다.
- `t` 단독키는 일반 typing과 충돌하므로 기본값에서 제외한다.
- `--inject-key t`로 사용자가 명시 선택하는 것은 허용한다.

## Verification

Wrapper:

```bash
python3 -m py_compile scripts/stt_codex.py
scripts/stt_codex.py --help
scripts/stt_codex.py --stt-model tiny --stt-device cpu --stt-compute-type int8 --release-gap 0.25 --min-duration 0.1 --max-duration 3 --cmd bash -- -lc 'IFS= read -r -t 20 line; printf "child:%s\n" "$line"'
```

- `ptt key: ctrl+t` status 확인.
- `ctrl+t` 입력으로 recording start/stop 확인.
- `tiny/cpu/int8` STT 호출 확인.
- 무발화 결과가 empty transcript로 skip되는 것 확인.
- 임시 WAV 삭제 확인.

KSS Korean fixture:

```bash
scripts/run_fixture_suite.sh fixtures/kss-ko-core-v1.json --model large-v3 --device cuda --compute-type float16
```

- PASS 6/6.
- exact 5/6.
- normalized 6/6.
- output: `output/suite/kss-ko-core-v1-large-v3-cuda-float16.json`.

HiKE code-switch fixture:

```bash
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
```

- exact 0/5.
- normalized 0/5.
- Latin token preservation 14/28, 50.00%.
- output: `output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json`.

## Interpretation

- 한국어 fixture 기준으로는 `large-v3` CUDA 경로가 정상이다.
- 실제 마이크 입력의 낮은 품질은 마이크 장치, gain, noise, 거리 문제일 가능성이 있다.
- 한영 혼합 token 보존 문제는 fixture에서도 재현된다.
- token recovery는 후속 기능으로 유지한다.

## Follow-up

- 장비 변경 후 실제 발화로 다시 end-to-end 테스트한다.
- 필요하면 `--keep-audio`로 실제 발화 WAV를 남겨 fixture와 비교한다.
