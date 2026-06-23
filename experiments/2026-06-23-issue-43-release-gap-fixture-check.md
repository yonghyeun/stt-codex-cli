# Issue 43 Release Gap Fixture Check

## Scope

- Issue: `#43`.
- Change under review: PTT `accuracy/speed` profile 제거, default `release_gap=0.35s`, default `stt_backend=worker`, default `audio_handoff=auto`.
- Runtime default: 저장/debug option이 꺼진 기본 실행은 worker backend에서 buffer handoff를 사용한다.
- Fixture purpose: PR review에 expected text와 transcribed text를 함께 남기기 위한 전체 legacy fixture 재측정.

## Boundary

- `release_gap`은 live PTT stop timing option이다.
- `worker`/`buffer` 기본값은 wrapper runtime request path option이다.
- 아래 fixture는 이미 녹음된 WAV를 `run_fixture_suite.py`로 전사하므로 live PTT stop timing과 wrapper handoff path를 직접 측정하지 않는다.
- 이 check는 default runtime 계약 변경이 fixed WAV STT 품질을 바꾸지 않았다는 PR evidence다.
- Legacy fixture는 `#9` STT accuracy active baseline이 아니다.

## Commands

Worktree에는 `.venv`와 ignored generated fixture가 없어서 main worktree의 local artifacts를 재사용했다.

```bash
LD_LIBRARY_PATH=/home/yonghyeun/stt-codex-cli/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib:/home/yonghyeun/stt-codex-cli/.venv/lib/python3.12/site-packages/nvidia/cublas/lib \
  /home/yonghyeun/stt-codex-cli/.venv/bin/python scripts/run_fixture_suite.py \
  fixtures/kss-ko-core-v1.json \
  --fixture-root /home/yonghyeun/stt-codex-cli/fixtures/generated/kss-ko-core-v1 \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --output output/suite/issue-43-kss-ko-core-v1-large-v3-cuda-float16.json
```

```bash
LD_LIBRARY_PATH=/home/yonghyeun/stt-codex-cli/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib:/home/yonghyeun/stt-codex-cli/.venv/lib/python3.12/site-packages/nvidia/cublas/lib \
  /home/yonghyeun/stt-codex-cli/.venv/bin/python scripts/run_fixture_suite.py \
  fixtures/hike-code-switch-core-v1.json \
  --fixture-root /home/yonghyeun/stt-codex-cli/fixtures/generated/hike-code-switch-core-v1 \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --require none \
  --output output/suite/issue-43-hike-code-switch-core-v1-large-v3-cuda-float16.json
```

## Summary

| suite | requirement | exact | normalized | note |
| --- | --- | ---: | ---: | --- |
| `kss-ko-core-v1` | normalized | 5/6 | 6/6 | row `00997` punctuation-only difference |
| `hike-code-switch-core-v1` | none | 0/5 | 0/5 | measurement suite; English token preservation remains weak |

## KSS Expected vs Transcribed

| row | label | exact | normalized | expected text | transcribed text |
| --- | --- | --- | --- | --- | --- |
| `00000` | `medium_declarative` | pass | pass | 그는 괜찮은 척하려고 애쓰는 것 같았다. | 그는 괜찮은 척하려고 애쓰는 것 같았다. |
| `00016` | `short_polite_imperative` | pass | pass | 자리에 앉으세요. | 자리에 앉으세요. |
| `00079` | `long_declarative` | pass | pass | 부모가 저지르는 큰 실수 중 하나는 자기 아이를 다른 집 아이와 비교하는 것이다. | 부모가 저지르는 큰 실수 중 하나는 자기 아이를 다른 집 아이와 비교하는 것이다. |
| `00099` | `negative_polite_imperative` | pass | pass | 침으로 편지 봉투에 우표를 붙이지 마세요. | 침으로 편지 봉투에 우표를 붙이지 마세요. |
| `00997` | `short_urgent_imperative` | fail | pass | 걷지 말고 뛰어! | 걷지 말고 뛰어. |
| `01040` | `question` | pass | pass | 여기에서 가까운 곳에 서점이 있나요? | 여기에서 가까운 곳에 서점이 있나요? |

## HiKE Expected vs Transcribed

| row | label | exact | normalized | expected text | transcribed text |
| --- | --- | --- | --- | --- | --- |
| `00000` | `software_bug_session_logic` | fail | fail | 이번 bug는 session management logic에 문제가 있었어 | 이번 버그는 세션 매니지먼트 로직의 문제가 있었어 |
| `00003` | `software_sprint_gateway_migration` | fail | fail | 이번 sprint에서 api gateway migration 작업이 생각보다 complex해서 deadline을 못 맞출 것 같아 | 이번 스프린트에서 API Gateway migration 작업이 생각보다 컴플렉스해서 deadline을 못 맞출 것 같아. |
| `00008` | `business_review_session` | fail | fail | 내일 client presentation이 있으니까 powerpoint slides 다시 한번 review해보고 qa session 준비도 해둬 | 내 클라이언트 프레젠테이션이 있으니까 파워포인트 슬라이드 다시 한 번 리뷰해 보고 큐앤에이 세션 준비도 해둬 |
| `00013` | `word_level_actually` | fail | fail | actually가 들어가면 왜 좀 더 진지해지는 느낌이야 | 액츄리가 들어가면 왜 좀 더 진지해지는 느낌이여 |
| `00015` | `software_database_schema` | fail | fail | we need to update the database schema 특히 user table에 새로운 column 추가된 거 반영해야 해 | We need to update the database schema. 특히 user table에 새로운 column 추가된 것 반영해야 해. |

## PR Note

- KSS 한국어 fixture는 normalized 기준 유지.
- HiKE 한영 혼합 fixture는 여전히 Latin token이 한글 음차로 바뀌는 문제가 있다.
- 이 문제는 `release_gap`과 wrapper handoff runtime setting과 별개다.
- `release_gap=0.35s` 기본 변경은 live PTT truncation risk를 가질 수 있으나 fixed WAV fixture에서는 측정되지 않는다.
- 기본 worker+buffer runtime은 wrapper request latency path를 바꾸지만 이 fixed WAV suite에서는 직접 측정되지 않는다.
