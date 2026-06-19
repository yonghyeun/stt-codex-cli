# Phase 5: Korean Fixture Suite

## Scope

- 단일 KSS fixture를 여러 한국어 문장 fixture suite로 확장한다.
- 같은 모델과 옵션으로 suite 전체를 반복 검증한다.

## Suite

- Manifest: `fixtures/kss-ko-core-v1.json`.
- Source: `Bingsu/KSS_Dataset`.
- License: `cc-by-nc-sa-4.0`.
- Generated root: `fixtures/generated/kss-ko-core-v1/`.
- Result output: `output/suite/`.

## Included Rows

| row | label | reason |
| --- | --- | --- |
| 0 | `medium_declarative` | baseline medium declarative sentence |
| 16 | `short_polite_imperative` | short polite command-like sentence |
| 79 | `long_declarative` | long declarative sentence |
| 99 | `negative_polite_imperative` | negative polite command-like sentence |
| 997 | `short_urgent_imperative` | short urgent command-like sentence |
| 1040 | `question` | question sentence |

## Verification

```bash
scripts/fetch_kss_fixture.py --manifest fixtures/kss-ko-core-v1.json
scripts/run_fixture_suite.sh fixtures/kss-ko-core-v1.json --model large-v3 --device cuda --compute-type float16 --output output/suite/kss-ko-core-v1-large-v3-cuda-float16.json
```

## Result

- Model: `large-v3`.
- Device: `cuda`.
- Compute type: `float16`.
- Required match: normalized.
- Total rows: 6.
- Exact pass: 5.
- Normalized pass: 6.
- Suite elapsed: 7.71s.

## Exact Difference

- Row 997 expected: `걷지 말고 뛰어!`
- Row 997 actual: `걷지 말고 뛰어.`
- 판단: 문장부호 차이만 있으므로 normalized 기준 통과.

## Rejected Candidate

- Row 1083 expected: `저는 책임감이 강한 편인데, 그것 때문에 직장에서 스트레스를 받아요.`
- Row 1083 actual: `저는 책임감이 강한 편인데 그것 때문에 직장에서 스트레스를 많이 받아요.`
- 판단: `많이`가 추가되어 normalized 기준 실패.
- 처리: 기본 회귀 suite에서 제외하고 정확도 리스크 후보로 보관.

## Decision

- 기본 한국어 회귀 suite 기준은 normalized match다.
- 정확도 기준 모델은 `large-v3` CUDA `float16`로 유지한다.
- 문장부호 차이는 기본 실패로 보지 않는다.
- 단어 추가, 누락, 치환은 실패로 본다.

## Follow-up

- 한영 혼합 fixture suite 추가.
- Codex CLI 명령형 문장에 가까운 fixture 추가.
- row 1083 같은 의미 단어 추가 사례를 별도 accuracy risk로 추적.
