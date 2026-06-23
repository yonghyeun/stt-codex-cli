# Beam/VAD Latency Tradeoff

## Scope

- Issue: `#35` under umbrella `#28`.
- Coverage: fixed smoke set only.
- Matrix: `beam_size=5/1` x `vad_filter=on/off`.
- Fixed smoke input set: `cmd-0002, cmd-0018, cmd-0021, cmd-0024`.
- Non-scope: prompt tuning, token recovery, worker/buffer handoff, release gap.

## Reproduce

```bash
STT_PYTHON_BIN=/path/to/.venv/bin/python \
STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \
scripts/evaluate_beam_vad_tradeoff.py \
  --run-id-prefix 20260623-beam-vad-fixed-smoke-large-v3-cuda-float16 \
  --input-root /home/yonghyeun/stt-codex-cli/evals/inputs/speech/v1 \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --report-output evals/stt_accuracy/reports/2026-06-23-beam-vad-tradeoff.md \
  --force
```

## Summary

- `#29` current-input fixed-smoke subprocess average: `5.956` seconds.

| combo | beam | VAD | avg latency s | avg decode s | delta vs default s | delta vs #29 avg s | avg case score | avg normalized CER | floor | decision |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `beam5-vad-on` | 5 | on | 5.191 | 1.812 | 0.000 | -0.765 | 0.6423 | 0.3156 | pass | default_only |
| `beam1-vad-on` | 1 | on | 5.173 | 1.712 | -0.018 | -0.783 | 0.6423 | 0.3156 | pass | fixed-smoke-only-candidate |
| `beam5-vad-off` | 5 | off | 5.334 | 1.962 | 0.143 | -0.622 | 0.6233 | 0.3394 | fail | excluded_accuracy_floor |
| `beam1-vad-off` | 1 | off | 5.111 | 1.722 | -0.080 | -0.845 | 0.6233 | 0.3394 | fail | excluded_accuracy_floor |

## Case Floor

| combo | sample | case score | #29 case score | normalized CER | failures | decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `beam5-vad-on` | `cmd-0002` | 1.0000 | 1.0000 | 0.0000 | none | pass |
| `beam5-vad-on` | `cmd-0018` | 0.3147 | 0.3147 | 0.6897 | phonetic_transcript_mismatch, hallucination | pass |
| `beam5-vad-on` | `cmd-0021` | 0.3435 | 0.3435 | 0.4615 | phonetic_transcript_mismatch, hallucination | pass |
| `beam5-vad-on` | `cmd-0024` | 0.9111 | 0.9111 | 0.1111 | phonetic_transcript_mismatch | pass |
| `beam1-vad-on` | `cmd-0002` | 1.0000 | 1.0000 | 0.0000 | none | pass |
| `beam1-vad-on` | `cmd-0018` | 0.3147 | 0.3147 | 0.6897 | phonetic_transcript_mismatch, hallucination | pass |
| `beam1-vad-on` | `cmd-0021` | 0.3435 | 0.3435 | 0.4615 | phonetic_transcript_mismatch, hallucination | pass |
| `beam1-vad-on` | `cmd-0024` | 0.9111 | 0.9111 | 0.1111 | phonetic_transcript_mismatch | pass |
| `beam5-vad-off` | `cmd-0002` | 0.9238 | 1.0000 | 0.0952 | phonetic_transcript_mismatch | fail_cmd_0002_regression |
| `beam5-vad-off` | `cmd-0018` | 0.3147 | 0.3147 | 0.6897 | phonetic_transcript_mismatch, hallucination | pass |
| `beam5-vad-off` | `cmd-0021` | 0.3435 | 0.3435 | 0.4615 | phonetic_transcript_mismatch, hallucination | pass |
| `beam5-vad-off` | `cmd-0024` | 0.9111 | 0.9111 | 0.1111 | phonetic_transcript_mismatch | pass |
| `beam1-vad-off` | `cmd-0002` | 0.9238 | 1.0000 | 0.0952 | phonetic_transcript_mismatch | fail_cmd_0002_regression |
| `beam1-vad-off` | `cmd-0018` | 0.3147 | 0.3147 | 0.6897 | phonetic_transcript_mismatch, hallucination | pass |
| `beam1-vad-off` | `cmd-0021` | 0.3435 | 0.3435 | 0.4615 | phonetic_transcript_mismatch, hallucination | pass |
| `beam1-vad-off` | `cmd-0024` | 0.9111 | 0.9111 | 0.1111 | phonetic_transcript_mismatch | pass |

## Decision

- Default accuracy-first profile remains `beam_size=5`, VAD on.
- Full suite was not run in this leaf; all candidate decisions are fixed-smoke-only.
- A combo marked `fixed-smoke-only-candidate` may inform speed profile docs, but must not be promoted as suite-backed.

## Measurement Boundary

- Measured: fixed smoke subprocess latency and accuracy for each beam/VAD combo.
- Not measured: full suite, live PTT latency, child PTY injection latency, terminal render latency.
- Raw transcript artifacts remain local-only under `evals/stt_accuracy/runs/`.
