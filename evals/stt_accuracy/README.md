# STT Accuracy Eval

Codex CLI 입력 보조 목적의 STT 정확도 평가 트랙.

이 문서가 STT accuracy evaluation architecture contract다.

## Goal

일반 받아쓰기 정확도가 아니라 Codex CLI 입력에 필요한 정확도를 측정한다.

주요 관심사:

- 한국어 명령 인식.
- 한영 혼합 명령 인식.
- 파일명과 경로 보존.
- CLI option 보존.
- 모듈명, 함수명, 코드 식별자 보존.
- hallucination 방어.
- insertion-safe 여부.

## Folder Architecture

`stt_accuracy/`는 평가 트랙의 suite, run, report 계약만 소유한다. 공유 speech input은 `evals/inputs/speech/v1/`이 소유한다.

```text
evals/
  inputs/
    speech/
      v1/
        samples/
          cmd-0001/
            audio.wav
            expected.txt
            metadata.json
  stt_accuracy/
    README.md
    metric_contract.json
    suites/
      README.md
      codex-command-accuracy-v1/
        README.md
        manifest.schema.json
        manifest.example.json
        manifest.json
    runs/
      .gitkeep
      <run_id>/
        raw/
          cmd-0001.txt
        recovered/
          cmd-0001.txt
        result.json
        metadata.json
    reports/
      README.md
      2026-06-21-governance.md
      2026-06-21-corpus-collection.md
```

## Source of Truth

- `evals/inputs/README.md`: 공유 input root contract.
- `evals/inputs/speech/v1/README.md`: speech input v1 sample contract.
- 이 문서: STT accuracy 평가 트랙 contract.
- `suites/README.md`: suite와 manifest 공통 계약.
- `suites/codex-command-accuracy-v1/README.md`: 첫 active suite 계약.
- `metric_contract.json`: metric id, summary route, failure type 설명 계약.
- `reports/`: 결정, baseline, closeout 요약.

이 문서는 local file state만으로 읽혀야 한다. 작업 순서, 리뷰 상태, 외부 전달 상태 같은 진행 정보는 이 계약의 입력값이 아니다.

## Ownership Rules

- `stt_accuracy`는 WAV, expected transcript, sample metadata를 소유하지 않는다.
- 공유 speech sample은 `evals/inputs/speech/v1/samples/<sample_id>/`가 소유한다.
- suite는 `input_set`과 `sample_id`만 참조한다.
- suite는 audio, expected transcript, raw transcript 파일 경로를 직접 소유하지 않는다.
- metric list와 case selection은 suite manifest가 소유한다.
- raw transcript, recovered transcript, result summary는 `runs/<run_id>/`가 소유한다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 input version 또는 새 sample id를 만든다.

## Suite Contract

첫 active suite는 `codex-command-accuracy-v1`이다.

```text
evals/stt_accuracy/suites/codex-command-accuracy-v1/
  README.md
  manifest.schema.json
  manifest.example.json
  manifest.json
```

`manifest.json`은 `input_set: "speech/v1"`과 `sample_id`로 입력을 참조한다.

## Baseline Harness Contract

Baseline 실행은 하네스 계약을 먼저 따른다.

Canonical dry-run:

```bash
scripts/run_stt_accuracy_suite.py \
  --suite codex-command-accuracy-v1 \
  --input-root evals/inputs/speech/v1 \
  --run-id 20260621-large-v3-cuda-float16-baseline \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --dry-run
```

Canonical baseline config:

- `suite_id`: `codex-command-accuracy-v1`.
- `input_set`: `speech/v1`.
- `model`: `large-v3`.
- `device`: `cuda`.
- `compute_type`: `float16`.
- `language`: `ko`.
- `initial_prompt`: 없음.
- `token_recovery`: `none`.

`--dry-run`은 모델을 load하지 않는다. dry-run은 suite manifest, input manifest,
sample folder, `audio.wav`, `expected.txt`, `metadata.json`, case 순서, run output
path 계획만 검증하고 JSON plan을 stdout에 출력한다.

새 worktree에 ignored `audio.wav`가 없으면 `--input-root`로 실제 local audio가 있는
input root를 명시한다. tracked suite manifest와 local audio artifact는 분리될 수
있지만, `sample_id` 계약은 같아야 한다.

## Run Artifact Contract

실행 결과는 run id 단위로 보존한다.

```text
evals/stt_accuracy/runs/<run_id>/
  raw/
    <sample_id>.txt
  recovered/
    <sample_id>.txt
  result.json
  metadata.json
```

- `raw/`: STT 모델 출력 원문.
- `recovered/`: token recovery나 후처리 적용 결과.
- `result.json`: metric별 결과 summary, case별 transcript 비교, 정량 품질 지표.
- `metadata.json`: model, prompt, recovery policy, suite id, input set, 실행 시각 같은 run metadata.

run artifact는 local-only다. 같은 speech input을 여러 model, prompt, recovery 정책으로 반복 실행해도 이전 결과를 덮어쓰지 않는다.

Baseline run의 `result.json` 최소 field:

- `schema_version`
- `suite_id`
- `input_set`
- `run_id`
- `config`
- `elapsed_seconds`
- `total`
- `failed`
- `category_summary`
- `failure_summary`
- `quality_summary`
- `cases`

`cases[]`의 각 항목은 inspection을 위해 다음 field를 가진다.

- `text_comparison.expected_text`: 사용자가 의도한 최종 입력문.
- `text_comparison.raw_text`: STT 모델 출력 원문.
- `text_comparison.recovered_text`: 후처리 이후 텍스트. baseline에서는 raw와 같다.
- `text_comparison.normalized_expected`
- `text_comparison.normalized_raw`
- `text_comparison.normalized_recovered`
- `quality.edit_distance`
- `quality.char_error_rate`
- `quality.normalized_edit_distance`
- `quality.normalized_char_error_rate`
- `quality.text_similarity`
- `quality.word_error_rate`
- `quality.critical_token_precision`
- `quality.critical_token_recall`
- `quality.critical_token_f1`
- `quality.case_score`
- `quality.critical_tokens`

`quality_summary`는 case별 `quality` 값을 suite 단위로 평균낸다.

- `average_case_score`
- `average_text_similarity`
- `average_normalized_char_error_rate`
- `average_critical_token_f1`

Baseline run의 `metadata.json` 최소 field:

- `schema_version`
- `run_id`
- `suite_id`
- `input_set`
- `started_at_utc`
- `completed_at_utc`
- `config`
- `artifact_contract`

Baseline은 token recovery를 적용하지 않는다. `recovered/<sample_id>.txt`는 같은 run
schema를 유지하기 위한 후처리 산출물 위치이며, baseline에서는 raw와 동일한 텍스트를
쓴다. baseline report는 raw transcript 전체를 Git-tracked report에 복사하지 않는다.

## Quantitative Quality Metrics

pass/fail은 유지한다. 단, `result.json`은 실패 정도를 판단할 수 있도록 정량 지표를
함께 기록한다.

Metric 설명과 사람이 읽는 출력 routing의 canonical source는
`evals/stt_accuracy/metric_contract.json`이다. README의 설명은 사람이 빠르게 읽기
위한 요약이며, renderer는 `metric_contract.json`의 id와 route를 읽어 summary metric,
source metric, direction, failure type 설명을 출력한다.

`metric_contract.json` 최소 field:

- `schema_version`
- `contract_id`
- `quality_metrics`
- `summary_routes`
- `failure_types`
- `metric_routes`

`quality_metrics`는 metric id별 `label`, `direction`, `unit`, `description`을 가진다.
`summary_routes`는 `quality_summary` field가 어떤 case-level metric의 평균인지
연결한다. `failure_types`는 result의 failure id 설명을 소유한다. `metric_routes`는
suite manifest의 pass/fail metric이 어떤 quality metric과 failure type으로 해석되는지
연결한다.

- `char_error_rate`: 원문 기준 character edit distance / expected character count.
- `normalized_char_error_rate`: 공백과 문장부호를 제거한 normalized text 기준 CER.
- `text_similarity`: normalized edit distance 기반 `0.0`에서 `1.0` 사이 유사도.
- `word_error_rate`: 공백 기준 word edit distance / expected word count. 한국어에서는 보조 지표다.
- `critical_token_precision`: transcript의 Latin-script token 중 expected에 있던 비율.
- `critical_token_recall`: expected의 Latin-script token 중 transcript에 보존된 비율.
- `critical_token_f1`: critical token precision과 recall의 F1.
- `case_score`: `text_similarity`, `critical_token_f1`, insertion-safe 여부, hallucination penalty를 조합한 `0.0`에서 `1.0` 사이 점수.

한국어 명령은 `normalized_char_error_rate`와 `text_similarity`를 우선 본다. 파일 경로,
CLI option, 코드 식별자, 한영 혼합 발화는 `critical_token_recall`과
`critical_token_f1`을 우선 본다.

## Human-Readable Result View

`result.json`은 machine-readable source다. 사람이 읽는 view는 script로 생성한다.

```bash
scripts/render_stt_accuracy_result.py \
  evals/stt_accuracy/runs/<run_id>/result.json
```

기본 출력은 Markdown summary, metric contract 설명, case table이다. `--show-text`를 주면 case별
`expected_text`, `raw_text`, `recovered_text` 전체를 Markdown code block으로 출력한다.
이 출력은 local inspection 용도다. raw transcript 전체가 포함된 출력은 Git-tracked
report에 그대로 복사하지 않는다.

기본 metric contract 경로는 `evals/stt_accuracy/metric_contract.json`이다. 다른 contract를
검증할 때만 `--metric-contract <path>`로 명시한다.

## Failure Taxonomy

하네스는 case별 `failure_types`를 같은 이름으로 기록한다.

- `korean_command_mismatch`: 한국어 명령의 normalized match 실패.
- `latin_token_loss`: expected의 Latin-script token 보존 실패.
- `file_path_loss`: 파일명 또는 경로 token 보존 실패.
- `cli_option_loss`: `--option` 형태 CLI option 보존 실패.
- `code_identifier_loss`: 함수명, 모듈명, snake_case, dotted identifier 보존 실패.
- `hallucination`: expected에 없는 Latin-script token이 raw transcript에 추가됨.
- `empty_transcript`: raw transcript가 비어 있음.
- `punctuation_only`: raw transcript가 문장부호뿐임.
- `insertion_unsafe`: Codex CLI 입력창에 삽입할 최소 텍스트 조건을 만족하지 못함.

## Artifact Policy

Git 추적 대상:

- `evals/stt_accuracy/**/README.md`.
- `evals/stt_accuracy/metric_contract.json`.
- `evals/stt_accuracy/suites/**/manifest.schema.json`.
- `evals/stt_accuracy/suites/**/manifest.example.json`.
- `evals/stt_accuracy/suites/**/manifest.json`.
- `evals/stt_accuracy/reports/**`.
- `evals/stt_accuracy/runs/.gitkeep`.

Git 추적 금지:

- `evals/stt_accuracy/runs/**`의 실제 run artifact.
- raw transcript.
- recovered transcript.
- suite raw result.
- 실제 사용자 발화 audio.
- 개인 glossary.

## Fixture Policy

새 정확도 트랙에서는 top-level `fixtures/generated/`를 사용하지 않는다.

top-level `fixtures/`의 KSS, HiKE, token-recovery suite는 legacy/reference surface다. 새 active baseline으로 사용하지 않는다.

## Transcript Policy

transcript는 세 종류로 분리한다.

- `raw transcript`: STT 모델 출력 원문.
- `expected transcript`: 사용자가 원래 의도한 최종 Codex 입력문.
- `recovered transcript`: token recovery나 후처리 적용 결과.

정확도 비교의 기준은 `expected transcript`다. raw와 recovered를 섞어 성공으로 계산하지 않는다.

## Measurement Axes

정확도는 하나의 pass/fail로 판단하지 않는다.

- Korean command match.
- Latin token preservation.
- file/path token preservation.
- CLI option preservation.
- code identifier preservation.
- hallucination count.
- insertion-safe decision.

## Non-Ownership

이 문서가 소유하지 않는 일:

- 실제 audio 수집.
- 공유 input corpus versioning.
- raw transcript 작성.
- model option 실험.
- token recovery 구현.
- 기존 fixture migration.
- suite runner 구현.
