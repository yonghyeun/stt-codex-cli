# Phase 16: Optional Run Artifacts

## Scope

- 기본 실행에서는 audio와 transcript를 영구 저장하지 않는다.
- 사용자가 `--save-run`을 명시한 경우에만 run artifact를 저장한다.
- 저장 단위는 push-to-talk recording 1회다.
- token recovery는 수행하지 않는다.

## Script

- `scripts/stt_codex.py`.

## Behavior

- `--save-run`을 주면 `output/runs/` 아래에 run directory를 만든다.
- directory 이름은 `YYYYMMDD-HHMMSS-mmm-stt-codex` 형식이다.
- 같은 millisecond에 충돌하면 `-001` suffix를 붙인다.
- 각 run directory에는 `audio.wav`, `transcript.txt`, `metadata.json`을 저장한다.
- `metadata.json`에는 recording config, STT option, elapsed time, outcome, injected 여부를 기록한다.
- `--keep-audio`는 system temp directory의 임시 WAV도 남기는 debug option으로 유지한다.

## Commands

기본 저장 실행:

```bash
scripts/stt_codex.py --save-run
```

정확도 기준 모델:

```bash
scripts/stt_codex.py --save-run --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

저장 위치 명시:

```bash
scripts/stt_codex.py --save-run --run-output-dir output/runs
```

## Result

- `python3 -m py_compile scripts/stt_codex.py` 성공.
- `scripts/stt_codex.py --help` 성공.
- `--save-run --inject-key t --min-duration 5` smoke test에서 `skipped_short_recording` 저장 확인.
- `--save-run --inject-key t --stt-model tiny --stt-device cpu --stt-compute-type int8` smoke test에서 STT 호출 후 `empty_transcript` 저장 확인.
- 생성된 run directory에 `audio.wav`, `transcript.txt`, `metadata.json` 3개 파일이 존재하는 것을 확인했다.
- `metadata.json`에 `outcome`, `injected`, `elapsed_seconds`, recording config, STT option이 기록되는 것을 확인했다.

## Risk

- `--save-run`은 사용자의 실제 발화 audio와 transcript를 파일로 남긴다.
- `output/`은 Git 추적 제외 상태지만, 외부 공유 전에는 artifact 확인이 필요하다.
