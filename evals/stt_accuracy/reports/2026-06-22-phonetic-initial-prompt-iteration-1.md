# Phonetic Initial Prompt Iteration 1

## Summary

`speech/v1` 한글 음가 transcript contract 위에서 `initial_prompt` 후보 3개를 실행했다.

결론: prompt-only 접근은 이번 기준에서 목표 달성치와 하한을 넘지 못했다.

P1이 가장 좋은 후보였지만 failed count는 줄지 않았고, `average_text_similarity`와
`average_normalized_char_error_rate` 개선 폭도 하한에 부족했다. 다음 iteration은
prompt matrix 확장이 아니라 decoding option 또는 한글 음가 후처리 정규화 쪽으로
분리하는 것이 맞다.

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
| P1 | 한글 음가 전사 직접 지시 | `한국어 음성은 한글 음가로 전사한다. 영어 약어, 파일명, 옵션, 숫자도 들리는 대로 한글로 쓴다.` |
| P2 | 대표 개발 용어 예시 포함 | `한국어 개발 명령을 한글 음가로 전사한다. STT는 에스티티, README.md는 리드미 엠디, v1은 브이원, --dry-run은 드라이런, run_id는 런 아이디로 쓴다.` |
| P3 | 라틴 문자와 숫자 최소화 | `모든 결과를 한글 중심으로 쓴다. 라틴 문자와 아라비아 숫자는 가능한 한 사용하지 않는다. 들린 개발 용어는 한글 음가로 적는다.` |

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
20260622-phonetic-prompt-p1-korean-sound-large-v3-cuda-float16
20260622-phonetic-prompt-p2-examples-large-v3-cuda-float16
20260622-phonetic-prompt-p3-no-latin-large-v3-cuda-float16
```

## Quantitative Results

| Run | failed | case_score | text_similarity | normalized_CER | hallucination |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 19 | 0.5935 | 0.6920 | 0.4127 | 13 |
| P1 | 19 | 0.6311 | 0.7172 | 0.3853 | 11 |
| P2 | 19 | 0.6010 | 0.7075 | 0.3901 | 13 |
| P3 | 19 | 0.6260 | 0.7084 | 0.4189 | 11 |

Delta from baseline:

| Run | failed delta | case_score delta | text_similarity delta | normalized_CER delta | hallucination delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| P1 | 0 | +0.0376 | +0.0252 | -0.0274 | -2 |
| P2 | 0 | +0.0075 | +0.0155 | -0.0226 | 0 |
| P3 | 0 | +0.0325 | +0.0164 | +0.0062 | -2 |

Category failed count:

| Run | korean_command | code_switch | file_path | cli_option | code_identifier | long_form |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1 | 4 | 4 | 2 | 4 | 4 |
| P1 | 1 | 4 | 4 | 2 | 4 | 4 |
| P2 | 1 | 4 | 4 | 2 | 4 | 4 |
| P3 | 1 | 4 | 4 | 2 | 4 | 4 |

## Judgment

목표 달성치:

- failed `<= 14`: 미달. best P1도 19.
- `average_text_similarity >= 0.78`: 미달. best P1 0.7172.
- `average_normalized_char_error_rate <= 0.30`: 미달. best P1 0.3853.
- hallucination `<= 8`: 미달. best P1/P3 11.
- `korean_command` 실패 `<= 1`: 충족.
- `insertion_unsafe = 0`: 충족.

하한:

- failed `<= 17` 또는 text similarity `+0.04`: 미달. best P1은 failed 19, similarity +0.0252.
- normalized CER `<= 0.37`: 미달. best P1 0.3853.
- hallucination `<= 12`: 충족. P1/P3 11.
- `korean_command`, `cli_option` category 악화 없음: 충족.

포기 기준:

- best prompt의 text similarity 개선 `< +0.02`: 해당 없음. P1 +0.0252.
- best prompt의 normalized CER 개선 `< 0.02`: 해당 없음. P1 -0.0274.
- hallucination `>= 16`: 해당 없음.
- `korean_command` 실패 `> 1`: 해당 없음.
- prompt 길이 증가가 개선보다 hallucination 증가를 먼저 유발: 일부 관찰. P2는 P1보다 길고 예시가 많지만 P1보다 약했다.

최종 판정:

- 목표 미달.
- 하한 미달.
- hard abandonment는 아니지만, prompt-only matrix 확장 근거 부족.
- P1은 임시 후보로 보존 가능.
- 다음 leaf는 prompt 확장이 아니라 decoding option 실험 또는 한글 음가 후처리 정규화 실험으로 분리한다.

## Verification

Executed:

```text
scripts/run_stt_accuracy_suite.py --dry-run ...
.venv/bin/python scripts/run_stt_accuracy_suite.py ... P1
.venv/bin/python scripts/run_stt_accuracy_suite.py ... P2
.venv/bin/python scripts/run_stt_accuracy_suite.py ... P3
git check-ignore -v evals/stt_accuracy/runs/<run_id>/result.json
```

Notes:

- 실제 run에는 `.venv`의 CUDA library path를 `LD_LIBRARY_PATH`로 명시했다.
- prompt run result는 ignored local artifact다.
- raw transcript 전문은 이 report에 포함하지 않았다.

## Next Direction

다음 실행 방향은 prompt matrix 확장이 아니다.

추천:

1. v1 한글 음가 후처리 정규화 후보를 별도 leaf로 설계한다.
2. 대상은 raw transcript의 Latin acronym, 숫자, 대표 개발 발화를 한글 음가 expected와 비교 가능한 형태로 정규화하는 것이다.
3. v2 literal 복원과는 분리한다. v1은 여전히 한글 음가 transcript 안정화만 소유한다.
