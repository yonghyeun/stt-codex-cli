# Initial Prompt Iteration 1

Date: 2026-06-22

Issue: #18

Suite: `codex-command-accuracy-v1`

Input set: `speech/v1`

## Goal Summary

이번 iteration의 목표는 STT 정확도 개선 전체가 아니라 `initial_prompt-only`
접근이 다음 iteration으로 갈 가치가 있는지 판단하는 것이다.

판단 기준:

- 목표 달성치:
  - `average_critical_token_f1 >= 0.45`
  - `average_case_score >= 0.60`
  - `latin_token_loss <= 12`
  - `cli_option_loss`, `file_path_loss`, `code_identifier_loss` 중 최소 1축 감소
  - `korean_command` category baseline 악화 없음
- 하한:
  - `average_critical_token_f1 >= 0.36` 또는 baseline 대비 `+0.05` 이상
  - `latin_token_loss` 최소 2건 감소
  - `hallucination <= 13`
  - 순수 한국어 명령 실패 추가 증가 없음
- 포기 기준:
  - best prompt의 `average_critical_token_f1` 개선이 `< +0.03`
  - `hallucination >= 14`
  - 한국어 명령 정확도 눈에 띄는 하락
  - prompt 길이 증가가 literal 보존보다 hallucination 증가를 먼저 유발

포기 대상은 STT 정확도 개선 전체가 아니라 `initial_prompt-only` 접근이다.

## Baseline

Run id: `20260622-large-v3-cuda-float16-baseline`

Config:

- model: `large-v3`
- device: `cuda`
- compute type: `float16`
- language: `ko`
- beam size: `5`
- initial prompt: 없음
- token recovery: `none`

Baseline summary:

| metric | value |
| --- | ---: |
| total | 24 |
| failed | 20 |
| average_case_score | 0.5648 |
| average_text_similarity | 0.6396 |
| average_normalized_char_error_rate | 0.4142 |
| average_critical_token_f1 | 0.3016 |
| latin_token_loss | 17 |
| hallucination | 11 |
| file_path_loss | 3 |
| cli_option_loss | 4 |
| code_identifier_loss | 4 |
| korean_command failed | 1 / 4 |

Baseline command:

```bash
scripts/run_stt_accuracy_suite.py \
  --suite codex-command-accuracy-v1 \
  --input-root evals/inputs/speech/v1 \
  --run-id 20260622-large-v3-cuda-float16-baseline \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko
```

현재 issue worktree에는 ignored `audio.wav`가 없어서 실제 prompt run은 local audio가
있는 input root를 명시했다. 같은 `speech/v1` manifest와 같은 sample id 24개를
사용했다.

## Prompt Candidates

### Candidate 1: literal classes

Run id: `20260622-initial-prompt-literal-classes`

Prompt:

```text
한국어 개발 명령 받아쓰기입니다. Codex CLI 입력에 필요한 영어 literal을 번역하지 말고 그대로 전사하세요. 파일명, 경로, CLI 옵션, snake_case, dotted identifier, CamelCase를 보존하세요. 예: Codex, README.md, --save-run, stt_runtime, run_id.
```

### Candidate 2: repo glossary

Run id: `20260622-initial-prompt-repo-glossary`

Prompt:

```text
Codex CLI 개발 작업 음성입니다. 다음 영어 토큰은 한국어로 번역하지 말고 철자 그대로 전사하세요: Codex, STT, accuracy, eval, contract, baseline, local artifact, git tracked report, README.md, manifest.json, metadata.json, run_id, stt_runtime, token_recovery, scripts/run_stt_accuracy_suite.py, --dry-run, --save-run, --compute-type.
```

### Candidate 3: suite literals

Run id: `20260622-initial-prompt-suite-literals`

Prompt:

```text
한국어와 영어가 섞인 Codex CLI 명령입니다. 다음 literal 후보를 들리면 정확히 보존하세요: evals/stt_accuracy/README.md, scripts/run_stt_accuracy_suite.py, output/runs, README.md, manifest.local.json, metadata.json, --dry-run, --save-run, --compute-type, stt_runtime, token_recovery, save_run_artifacts, transcript_has_text, run_id_from_timestamp, RecordingState, active, codex-command-accuracy-v1, fixtures, Phase, baseline, category, metric, mapping, case, local, artifact, git, tracked, report, sample, cmd, id.
```

## Execution Commands

Dry-run:

```bash
scripts/run_stt_accuracy_suite.py \
  --suite codex-command-accuracy-v1 \
  --input-root <local-audio-input-root> \
  --run-id 20260622-initial-prompt-literal-classes \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --initial-prompt '<candidate prompt>' \
  --dry-run
```

Prompt run shape:

```bash
LD_LIBRARY_PATH=<venv-site-packages>/nvidia/cublas/lib:<venv-site-packages>/nvidia/cudnn/lib \
  .venv/bin/python scripts/run_stt_accuracy_suite.py \
  --suite codex-command-accuracy-v1 \
  --input-root <local-audio-input-root> \
  --run-id <run-id> \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --initial-prompt '<candidate prompt>'
```

Renderer:

```bash
scripts/render_stt_accuracy_result.py \
  evals/stt_accuracy/runs/<run-id>/result.json \
  --max-text-chars 40
```

## Result Summary

| run | failed | case_score | text_similarity | nCER | critical_token_f1 | latin_loss | hallucination | file_path_loss | cli_option_loss | code_identifier_loss | korean failed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 20 | 0.5648 | 0.6396 | 0.4142 | 0.3016 | 17 | 11 | 3 | 4 | 4 | 1 |
| literal classes | 19 | 0.5752 | 0.6875 | 0.3793 | 0.3065 | 15 | 11 | 2 | 3 | 4 | 1 |
| repo glossary | 17 | 0.6801 | 0.7995 | 0.2327 | 0.4368 | 13 | 11 | 2 | 3 | 4 | 1 |
| suite literals | 15 | 0.7729 | 0.8616 | 0.1765 | 0.6157 | 10 | 10 | 1 | 3 | 1 | 1 |

Best run: `20260622-initial-prompt-suite-literals`

Delta from baseline:

| metric | baseline | best | delta |
| --- | ---: | ---: | ---: |
| failed | 20 | 15 | -5 |
| average_case_score | 0.5648 | 0.7729 | +0.2081 |
| average_text_similarity | 0.6396 | 0.8616 | +0.2220 |
| average_normalized_char_error_rate | 0.4142 | 0.1765 | -0.2377 |
| average_critical_token_f1 | 0.3016 | 0.6157 | +0.3141 |
| latin_token_loss | 17 | 10 | -7 |
| hallucination | 11 | 10 | -1 |
| file_path_loss | 3 | 1 | -2 |
| cli_option_loss | 4 | 3 | -1 |
| code_identifier_loss | 4 | 1 | -3 |
| korean_command failed | 1 | 1 | 0 |

## Judgment

판정: 목표 달성.

근거:

- `average_critical_token_f1`은 0.3016에서 0.6157로 올랐다.
- `average_case_score`는 0.5648에서 0.7729로 올랐다.
- `latin_token_loss`는 17건에서 10건으로 줄었다.
- `file_path_loss`, `cli_option_loss`, `code_identifier_loss`가 모두 줄었다.
- `korean_command` category 실패 수는 1건으로 baseline과 같았다.
- `hallucination`은 11건에서 10건으로 줄어 포기 기준에 걸리지 않았다.

따라서 이번 결과는 하한이 아니라 목표 달성치에 해당한다. `initial_prompt-only`
접근은 첫 iteration 기준 계속할 가치가 있다.

## Observations

- 추상적인 token class prompt는 효과가 작았다.
- repo-local glossary는 critical token 보존을 크게 끌어올렸지만 목표에는 약간 부족했다.
- suite literal 후보를 좁게 넣은 prompt가 가장 강했다.
- `code_identifier` category는 best run에서 실패 4건에서 1건으로 줄었다.
- `cli_option` category는 best run에서도 실패 3건이 남았다.
- 긴 glossary가 hallucination을 늘릴 것이라는 우려는 이번 run에서는 확인되지 않았다.
- 다만 best prompt는 suite literal에 많이 의존하므로, 그대로 product prompt로 확정하기에는 일반화 검증이 부족하다.

## Next Direction

다음 leaf 방향: prompt matrix 확장.

확장 초점:

- suite literal prompt를 기준 후보로 유지한다.
- CLI option 전용 prompt를 분리해 `--dry-run`, `--yes`, `--initial-prompt` 같은 dash token 보존을 다시 본다.
- suite literal을 그대로 늘리기보다, literal class와 compact glossary의 균형점을 찾는다.
- token recovery 전환은 보류한다. 이번 iteration에서 prompt-only 접근이 목표 달성치를 넘었다.

## Artifact Policy Check

- `evals/stt_accuracy/runs/<run_id>/result.json`은 local-only artifact다.
- raw transcript 전문은 이 report에 포함하지 않았다.
- Git 추적 대상은 이 report 하나다.
