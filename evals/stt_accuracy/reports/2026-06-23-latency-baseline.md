# STT Latency Baseline

## Scope

- Issue: `#29` under umbrella `#28`.
- Measurement path: file-based `scripts/transcribe.sh` subprocess.
- Fixed smoke input set: `cmd-0002, cmd-0018, cmd-0021, cmd-0024`.
- Non-scope: persistent worker, adapter split, buffer handoff, release gap, beam/VAD experiments.

## Reproduce

```bash
STT_PYTHON_BIN=/home/yonghyeun/stt-codex-cli/.venv/bin/python \
STT_SITE_PACKAGES=/home/yonghyeun/stt-codex-cli/.venv/lib/python3.12/site-packages \
scripts/measure_stt_latency_baseline.py \
  --run-id 20260623-latency-baseline-large-v3-cuda-float16 \
  --input-root /home/yonghyeun/stt-codex-cli/evals/inputs/speech/v1 \
  --baseline-result /home/yonghyeun/stt-codex-cli/evals/stt_accuracy/runs/20260622-corrected-corpus-baseline-large-v3-cuda-float16-r2/result.json \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --report-output evals/stt_accuracy/reports/2026-06-23-latency-baseline.md
```

If ignored WAV artifacts are absent in the current worktree, pass `--input-root`
pointing at a local speech/v1 input root that contains `audio.wav` files.
If the current worktree has no `.venv`, use `STT_PYTHON_BIN` and
`STT_SITE_PACKAGES` to point `scripts/transcribe.sh` at an existing venv.

## Config

- `run_id`: `20260623-latency-baseline-large-v3-cuda-float16`.
- `suite_id`: `codex-command-accuracy-v1`.
- `input_set`: `speech/v1`.
- `input_root`: `/home/yonghyeun/stt-codex-cli/evals/inputs/speech/v1`.
- `run_dir`: `evals/stt_accuracy/runs/20260623-latency-baseline-large-v3-cuda-float16`.
- `model`: `large-v3`.
- `device`: `cuda`.
- `compute_type`: `float16`.
- `language`: `ko`.
- `beam_size`: `5`.
- `vad_filter`: `True`.

## Accuracy Floor

- Fixed smoke set에서 empty transcript 추가 발생 금지.
- `cmd-0002`: exact 또는 normalized equivalent 유지.
- `cmd-0018`: 현재 `speech/v1` 한글 음가 expected 기준으로 추가 악화 방지.
- `cmd-0021`: 현재 `speech/v1` 한글 음가 expected 기준으로 추가 악화 방지.
- `cmd-0024`: 현재 `speech/v1` 한글 음가 expected 기준으로 추가 악화 방지.
- 후속 speed leaf의 fixed smoke 비교 기준은 이 report의 current-input case result다.
- corrected corpus baseline artifact와 current `expected.txt`가 다르면 per-case quality delta를 직접 비교하지 않는다.
- 전체 suite 실행 leaf: `average_case_score` 상대 5% 초과 하락 금지.
- 전체 suite 실행 leaf: `average_normalized_char_error_rate` 상대 10% 초과 악화 금지.

## Baseline Reference

- path: `/home/yonghyeun/stt-codex-cli/evals/stt_accuracy/runs/20260622-corrected-corpus-baseline-large-v3-cuda-float16-r2/result.json`.
- run id: `20260622-corrected-corpus-baseline-large-v3-cuda-float16-r2`.
- total/failed: `24` / `16`.
- average_case_score: `0.6512`.
- average_text_similarity: `0.7062`.
- average_normalized_char_error_rate: `0.3174`.
- average_critical_token_f1: `0.2756`.
- warning: baseline reference `expected_text` differs from current `expected.txt` for `cmd-0018, cmd-0021, cmd-0024`; latency numbers are directly comparable, but quality deltas need contract review.

## Latency Summary

| field | average seconds | total seconds |
| --- | ---: | ---: |
| `subprocess_elapsed_seconds` | 5.956 | 23.825 |
| `transcribe_internal_elapsed_seconds` | 5.397 | 21.588 |
| `model_load_elapsed_seconds` | 3.733 | 14.934 |
| `decode_elapsed_seconds` | 1.663 | 6.652 |
| `quality_eval_elapsed_seconds` | 0.001 | 0.004 |

## Case Results

| sample | category | audio s | subprocess s | internal s | model load s | decode s | quality s | case score | failures | baseline score |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| cmd-0002 | korean_command | 4.222 | 6.067 | 5.521 | 4.122 | 1.397 | 0.001 | 1.0000 | none | 1.0000 |
| cmd-0018 | code_identifier | 5.843 | 5.750 | 5.193 | 3.723 | 1.470 | 0.001 | 0.3147 | phonetic_transcript_mismatch, hallucination | 0.9657 |
| cmd-0021 | long_form | 7.806 | 5.951 | 5.388 | 3.552 | 1.835 | 0.001 | 0.3435 | phonetic_transcript_mismatch, hallucination | 0.8617 |
| cmd-0024 | long_form | 6.782 | 6.057 | 5.486 | 3.537 | 1.949 | 0.001 | 0.9111 | phonetic_transcript_mismatch | 0.3524 |

## Measurement Boundary

- Measured: `scripts/transcribe.sh` subprocess wall time.
- Measured: `scripts/transcribe.py` internal model load, decode, output write timing via `--timing-json`.
- Measured separately: transcript quality comparison using the existing STT accuracy harness.
- Not measured in this file-based run: `arecord` stop, live temp WAV creation, PTY injection, temp audio cleanup.
- Full CUDA suite not rerun for this leaf; fixed smoke set is the #28 governance comparison surface.
