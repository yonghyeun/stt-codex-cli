# Phonetic Initial Prompt Iteration 1

## Summary

`speech/v1` 한글 음가 transcript contract 위에서 일반화된 `initial_prompt`
후보 3개를 다시 실행했다.

기존 prompt set은 prompt 안에 `STT`, `README.md`, `v1`, `--dry-run`, `run_id`
같은 Latin literal을 직접 노출해 모델이 literal 표기를 유지하도록 유도할 수 있었다.
이번 iteration은 특정 개발 token 예시를 제거하고, 한글 음가 출력 원칙만 일반화해서
검증했다.

결론: P3를 현행 best available prompt로 채택한다. 목표 달성치에는 도달하지 못했고
failed count는 20으로 baseline보다 1건 악화되었지만, `average_case_score`,
`average_normalized_char_error_rate`, Latin hallucination은 baseline보다 개선되었다.
P3의 `average_normalized_char_error_rate`는 하한도 충족했다. 다만
`manifest local json schema validation command`, `run id from timestamp`,
`Codex-Command-Accuracy-V1` 같은 발화에서 literal 복원이 계속 발생했다.

따라서 다음 방향은 prompt를 더 늘리는 것이 아니라 P3를 고정한 뒤 v1 한글 음가
정규화 또는 phrase-level 발음 치환 전략을 별도 leaf로 검증하는 것이다.

## Baseline

| Field | Value |
| --- | --- |
| run_id | `20260622-phonetic-baseline-large-v3-cuda-float16-r2` |
| suite | `codex-command-accuracy-v1` |
| input_set | `speech/v1` |
| model | `large-v3` |
| device | `cuda` |
| compute_type | `float16` |
| language | `ko` |
| beam_size | `5` |
| initial_prompt | none |
| token_recovery | `none` |

Baseline summary:

| Metric | Value |
| --- | ---: |
| total | 24 |
| failed | 19 |
| average_case_score | 0.5935 |
| average_text_similarity | 0.6920 |
| average_normalized_char_error_rate | 0.4127 |
| average_critical_token_f1 | 0.0000 |
| phonetic_transcript_mismatch | 19 |
| hallucination | 13 |

## Prompt Candidates

| ID | Intent | Prompt |
| --- | --- | --- |
| P1 | 한글 음가 only | `들린 말을 한글 음가로만 전사한다. 영어 단어, 약어, 숫자, 기호처럼 들리는 말도 원문 그대로 쓰지 않는다. 뜻을 번역하거나 고치지 말고, 들린 발음을 한국어로 적는다. 최종 출력에는 한글과 띄어쓰기만 사용한다.` |
| P2 | 표기보다 발음 우선 | `출력 표기는 항상 발음을 우선한다. 사용자가 어떤 종류의 단어를 말하더라도 실제로 들린 소리를 한글로 풀어쓴다. 원래 철자, 숫자, 기호, 코드 표기를 추정하지 않는다. 의미 보정 없이 발화 순서대로 적는다.` |
| P3 | 문자 복원 금지 | `음성을 문자 표기로 복원하지 않는다. 들린 소리를 한글 발음대로 적는다. 알파벳, 숫자, 밑줄, 하이픈, 점, 확장자 표기는 출력하지 않는다. 모르는 말도 가능한 한 들린 발음 그대로 한글로 적는다.` |

## Run Commands

공통 조건:

```text
suite: codex-command-accuracy-v1
input_root: /home/yonghyeun/stt-codex-cli/evals/inputs/speech/v1
model: large-v3
device: cuda
compute_type: float16
language: ko
beam_size: 5
token_recovery: none
```

`audio.wav`는 main worktree의 ignored local artifact를 참조했다. prompt run artifact는
이 issue worktree의 `evals/stt_accuracy/runs/<run_id>/` 아래에 생성했다.

Run ids:

```text
20260622-phonetic-generalized-v2-p1-hangul-only-large-v3-cuda-float16
20260622-phonetic-generalized-v2-p2-pronunciation-first-large-v3-cuda-float16
20260622-phonetic-generalized-v2-p3-no-orthographic-restore-large-v3-cuda-float16
```

## Quantitative Results

| Run | failed | case_score | text_similarity | normalized_CER | hallucination |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 19 | 0.5935 | 0.6920 | 0.4127 | 13 |
| P1 | 20 | 0.6273 | 0.7146 | 0.3780 | 11 |
| P2 | 20 | 0.6332 | 0.7221 | 0.3662 | 11 |
| P3 | 20 | 0.6347 | 0.7218 | 0.3600 | 11 |

Delta from baseline:

| Run | failed delta | case_score delta | text_similarity delta | normalized_CER delta | hallucination delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| P1 | +1 | +0.0338 | +0.0226 | -0.0347 | -2 |
| P2 | +1 | +0.0397 | +0.0301 | -0.0465 | -2 |
| P3 | +1 | +0.0412 | +0.0298 | -0.0527 | -2 |

Category failed count:

| Run | korean_command | code_switch | file_path | cli_option | code_identifier | long_form |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1 | 4 | 4 | 2 | 4 | 4 |
| P1 | 2 | 4 | 4 | 2 | 4 | 4 |
| P2 | 2 | 4 | 4 | 2 | 4 | 4 |
| P3 | 2 | 4 | 4 | 2 | 4 | 4 |

## Transcript Inspection

Expected transcript와 P1/P2/P3 raw transcript 비교 전문은 PR comment에 남겼다.
Git-tracked report에는 raw transcript 전문을 복사하지 않는다.

주요 관찰:

- `cmd-0006`은 세 prompt 모두 `manifest local json schema validation command`를 그대로 출력했다.
- `cmd-0019`는 세 prompt 모두 `run, id, from, timestamp`를 그대로 출력했다.
- `cmd-0022`, `cmd-0023`은 `Codex-Command-Accuracy-V1`, `CMD` 같은 literal이 계속 남았다.
- P3는 `cmd-0017`, `cmd-0018`에서 `underbar`, `알파벳` 같은 prompt 영향 흔적이 생겼다.
- 일반화 prompt는 Latin hallucination 수를 줄였지만, 모델의 orthographic restoration을 완전히 막지 못했다.

## Judgment

목표 달성치:

- failed `<= 14`: 미달. best P3도 20.
- `average_text_similarity >= 0.78`: 미달. best P2 0.7221.
- `average_normalized_char_error_rate <= 0.30`: 미달. best P3 0.3600.
- hallucination `<= 8`: 미달. P1/P2/P3 모두 11.
- `korean_command` 실패 `<= 1`: 미달. P1/P2/P3 모두 2.
- `insertion_unsafe = 0`: 충족.

하한:

- failed `<= 17` 또는 text similarity `+0.04`: 미달.
- normalized CER `<= 0.37`: 충족. P2 0.3662, P3 0.3600.
- hallucination `<= 12`: 충족. P1/P2/P3 모두 11.
- `korean_command`, `cli_option` category 악화 없음: 미달. `korean_command`가 1에서 2로 악화.

포기 기준:

- best prompt의 text similarity 개선 `< +0.02`: 해당 없음. P2 +0.0301.
- best prompt의 normalized CER 개선 `< 0.02`: 해당 없음. P3 -0.0527.
- hallucination `>= 16`: 해당 없음.
- `korean_command` 실패가 2 이상으로 증가: 해당. 세 prompt 모두 2.

최종 판정:

- P3를 현행 best available prompt로 채택한다.
- P3는 목표 달성치에는 미달했고 failed count와 `korean_command`가 악화되었다.
- 그러나 P3는 baseline보다 `average_case_score`, `average_normalized_char_error_rate`, hallucination이 개선되었다.
- pass/fail 기준은 strict normalized match라 개선 폭을 충분히 반영하지 못한다.
- 다음 leaf는 prompt 확장이 아니라 P3 고정 후 v1 한글 음가 정규화 또는 phrase-level 발음 치환 실험으로 분리한다.

## Verification

Executed:

```text
scripts/run_stt_accuracy_suite.py --dry-run ... P1
scripts/run_stt_accuracy_suite.py --dry-run ... P2
scripts/run_stt_accuracy_suite.py --dry-run ... P3
.venv/bin/python scripts/run_stt_accuracy_suite.py ... P1
.venv/bin/python scripts/run_stt_accuracy_suite.py ... P2
.venv/bin/python scripts/run_stt_accuracy_suite.py ... P3
scripts/render_stt_accuracy_result.py evals/stt_accuracy/runs/<run_id>/result.json
git check-ignore -v evals/stt_accuracy/runs/<run_id>/result.json
```

Notes:

- 실제 run에는 main worktree `.venv`의 CUDA library path를 `LD_LIBRARY_PATH`로 명시했다.
- prompt run result는 ignored local artifact다.
- raw transcript 전문은 이 report에 포함하지 않았다.

## Next Direction

추천:

1. P3 prompt를 현행 best available prompt로 고정한다.
2. `manifest local json schema validation command` 같은 phrase-level English output을 한글 음가 expected와 비교 가능한 형태로 변환한다.
3. `run_id`, `CMD`, `Codex-Command-Accuracy-V1` 계열은 v2 literal 복원으로 넘기지 말고, v1에서는 먼저 음가 정규화 가능성을 확인한다.
