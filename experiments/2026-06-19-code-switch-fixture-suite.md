# Phase 6: Korean-English Code-Switch Fixture Suite

## Scope

- 한영 혼합 실제 음성 fixture suite를 추가한다.
- Codex CLI 사용에 중요한 Latin-script token 보존 여부를 측정한다.
- 이 phase는 pass/fail 기준 확정보다 baseline 측정이 목적이다.

## Source

- Dataset: `thetaone-ai/HiKE`.
- Source: <https://huggingface.co/datasets/thetaone-ai/HiKE>.
- Paper/repo: <https://github.com/ThetaOne-AI/HiKE>.
- License: `apache-2.0`.
- Split: `test`.

HiKE는 Korean-English code-switching ASR benchmark다. 소프트웨어 개발, 비즈니스, 언어 교육 등 다양한 주제의 실제 code-switching 음성을 포함한다.

## Suite

- Manifest: `fixtures/hike-code-switch-core-v1.json`.
- Generated root: `fixtures/generated/hike-code-switch-core-v1/`.
- Result output: `output/suite/`.

## Included Rows

| row | label | category | cs_level |
| --- | --- | --- | --- |
| 0 | `software_bug_session_logic` | software development | phrase |
| 3 | `software_sprint_gateway_migration` | software development | phrase |
| 8 | `business_review_session` | business | phrase |
| 13 | `word_level_actually` | language education | word |
| 15 | `software_database_schema` | software development | phrase |

## Commands

```bash
scripts/fetch_hike_fixture.py --manifest fixtures/hike-code-switch-core-v1.json
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none --output output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json --output output/suite/hike-code-switch-core-v1-large-v3-cuda-float16-analysis.json
```

`language=auto`도 추가 측정했다.

```bash
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --language auto --device cuda --compute-type float16 --require none --output output/suite/hike-code-switch-core-v1-large-v3-auto-cuda-float16.json
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-auto-cuda-float16.json --output output/suite/hike-code-switch-core-v1-large-v3-auto-cuda-float16-analysis.json
```

## Result

- Model: `large-v3`.
- Device: `cuda`.
- Compute type: `float16`.
- Rows: 5.
- Exact pass: 0/5.
- Normalized pass: 0/5.
- Latin-script token preservation: 14/28, 50%.
- `language=ko` and `language=auto` produced the same transcripts.

## Observations

| row | expected Latin tokens | preserved | issue |
| --- | --- | --- | --- |
| 0 | 4 | 0 | `bug`, `session`, `management`, `logic`이 자연스러운 한글 외래어 표기로 변환됨 |
| 3 | 6 | 4 | `sprint`, `complex`가 한글 음차로 변환됨 |
| 8 | 7 | 0 | 전체 업무 토큰이 한글 외래어 표기로 변환됨 |
| 13 | 1 | 0 | `actually`가 한글 음차로 변환됨 |
| 15 | 10 | 10 | 영어 토큰은 보존됐지만 한국어 `거`가 `것`으로 변환됨 |

## Decision

- `large-v3`는 한국어 단일 언어 fixture에는 강하지만, 한영 혼합에서는 영어권 단어를 자연스러운 한글 외래어 표기로 바꾸는 경향이 있다.
- 일반 입력에서는 이 동작이 틀렸다고 볼 수 없다.
- Codex CLI 입력 보조 도구에서는 파일명, 옵션명, 코드 식별자 같은 Latin-script token 보존이 중요하므로 별도 token recovery 기준이 필요하다.
- HiKE suite는 regression pass suite가 아니라 accuracy risk measurement suite로 둔다.

## Follow-up

- `initial_prompt` 또는 prompt 옵션으로 Latin-script token 보존이 개선되는지 실험한다.
- 자주 쓰는 개발 용어 glossary 기반 후처리 가능성을 검토한다.
- 사용자가 Codex CLI에 말할 실제 문장에 가까운 자체 녹음 fixture가 필요하다.
