# STT Buffer Handoff Report

## Scope

- Issue: `#32` under umbrella `#28`.
- Measurement path: persistent worker file handoff vs persistent worker buffer handoff.
- Fixed smoke input set: `cmd-0002, cmd-0018, cmd-0021, cmd-0024`.
- Non-scope: release gap tuning, beam/VAD tuning, token recovery.

## Reproduce

```bash
STT_PYTHON_BIN=/path/to/.venv/bin/python \
STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \
scripts/measure_audio_handoff_latency.py \
  --run-id 20260623-buffer-handoff-large-v3-cuda-float16 \
  --input-root /home/yonghyeun/stt-codex-cli/evals/inputs/speech/v1 \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --report-output evals/stt_accuracy/reports/2026-06-23-buffer-handoff.md
```

## Prior Baseline

- `#29` file-based subprocess average: `5.956` seconds.

## Summary

| path | average request seconds | average case score | average normalized CER | delta vs #29 subprocess avg |
| --- | ---: | ---: | ---: | ---: |
| file | 2.619 | 0.6423 | 0.3156 | -3.337 |
| buffer | 2.536 | 0.6423 | 0.3156 | -3.420 |

- buffer vs persistent-worker file average delta: `-0.083` seconds.

## Case Results

| sample | path | request s | case score | #29 case score | score delta | failures |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| cmd-0002 | file | 6.108 | 1.0000 | 1.0000 | 0.0000 | none |
| cmd-0018 | file | 1.195 | 0.3147 | 0.3147 | 0.0000 | phonetic_transcript_mismatch, hallucination |
| cmd-0021 | file | 1.523 | 0.3435 | 0.3435 | 0.0000 | phonetic_transcript_mismatch, hallucination |
| cmd-0024 | file | 1.652 | 0.9111 | 0.9111 | 0.0000 | phonetic_transcript_mismatch |
| cmd-0002 | buffer | 5.679 | 1.0000 | 1.0000 | 0.0000 | none |
| cmd-0018 | buffer | 1.231 | 0.3147 | 0.3147 | 0.0000 | phonetic_transcript_mismatch, hallucination |
| cmd-0021 | buffer | 1.560 | 0.3435 | 0.3435 | 0.0000 | phonetic_transcript_mismatch, hallucination |
| cmd-0024 | buffer | 1.675 | 0.9111 | 0.9111 | 0.0000 | phonetic_transcript_mismatch |

## Measurement Boundary

- Measured: persistent worker request wall time for file path handoff.
- Measured: persistent worker request wall time for base64 WAV buffer handoff.
- Measured: fixed smoke set accuracy with the existing STT accuracy evaluator.
- Not measured: live `arecord` stop latency, child PTY injection latency, terminal render latency.
