# CLI Option and File Path Rerecord

## Context

This report records the corpus adjustment for issue #20.

The previous `cli_option` and `file_path` samples used literal Codex input strings
as `expected.txt`. That made the corpus assume the user speaks symbols such as
`--dry-run`, path separators, underscores, and file extensions literally.

For this pass, the affected samples were rewritten so `expected.txt` matches the
actual spoken phrase used during recording. This changes the local evaluation
meaning for these samples from "recover the final Codex input literal" toward
"transcribe what the user actually said".

## Target Samples

| Sample | Category | Policy |
| --- | --- | --- |
| `cmd-0009` | `file_path` | `actual_spoken_phrase` |
| `cmd-0010` | `file_path` | `actual_spoken_phrase` |
| `cmd-0011` | `file_path` | `actual_spoken_phrase` |
| `cmd-0012` | `file_path` | `actual_spoken_phrase` |
| `cmd-0013` | `cli_option` | `actual_spoken_phrase` |
| `cmd-0014` | `cli_option` | `actual_spoken_phrase` |
| `cmd-0015` | `cli_option` | `actual_spoken_phrase` |
| `cmd-0016` | `cli_option` | `actual_spoken_phrase` |

## Recording Evidence

New local-only `audio.wav` files were generated for all target samples.

Duration check:

| Sample | Duration seconds |
| --- | ---: |
| `cmd-0009` | 5.971500 |
| `cmd-0010` | 8.019500 |
| `cmd-0011` | 6.270188 |
| `cmd-0012` | 8.062188 |
| `cmd-0013` | 5.118188 |
| `cmd-0014` | 9.299500 |
| `cmd-0015` | 5.331500 |
| `cmd-0016` | 4.606188 |

`git check-ignore -v` confirmed that every target `audio.wav` remains ignored by
the `evals/inputs/speech/**/samples/**/audio.wav` rule.

The same ignored WAV files were copied to the main worktree, and SHA256 hashes
matched between the issue worktree and the main worktree.

## Contract Updates

`metadata.json` for target samples now records:

- `expected_text_policy`: `actual_spoken_phrase`
- `rerecord_reason`: public reason for the expected text rewrite

The sample metadata schema and speech input README were updated to make these
fields explicit public sample attributes.

## Suite Run

Executed run:

```text
run_id: 20260622-cli-option-file-path-rerecord-large-v3-cuda-float16-r2
suite_id: codex-command-accuracy-v1
input_set: speech/v1
model: large-v3
device: cuda
compute_type: float16
language: ko
token_recovery: none
```

Summary:

| Metric | Value |
| --- | ---: |
| total | 24 |
| failed | 16 |
| elapsed_seconds | 33.476 |
| average_case_score | 0.6512 |
| average_text_similarity | 0.7062 |
| average_normalized_char_error_rate | 0.3174 |
| average_critical_token_f1 | 0.2756 |

Category result:

| Category | Total | Failed |
| --- | ---: | ---: |
| `korean_command` | 4 | 1 |
| `code_switch` | 4 | 4 |
| `file_path` | 4 | 3 |
| `cli_option` | 4 | 1 |
| `code_identifier` | 4 | 3 |
| `long_form` | 4 | 4 |

Failure summary:

| Failure type | Count |
| --- | ---: |
| `latin_token_loss` | 9 |
| `hallucination` | 8 |
| `code_identifier_loss` | 3 |
| `korean_command_mismatch` | 2 |

Local source:

```text
evals/stt_accuracy/runs/20260622-cli-option-file-path-rerecord-large-v3-cuda-float16-r2/result.json
```

The run artifact is local-only and ignored by Git.

## Next Evaluation Judgment

The next prompt or decoding experiment should not interpret these eight samples
as final-literal recovery cases. They now measure whether STT can transcribe the
natural spoken wording that the user actually says for CLI options and file paths.

Literal reconstruction from spoken phrases such as "드라이런" to `--dry-run` is a
separate token recovery or command-normalization problem.
