# Phase 7 Auxiliary: Initial Prompt Token Preservation

## Scope

- `faster-whisper`의 `initial_prompt`가 한영 혼합 음성에서 Latin-script token 보존을 개선하는지 측정한다.
- 이 실험은 mode contract의 보조 실험이다.
- 핵심 해결책 여부를 판단한다.

## Prompt Support

스크립트에 다음 옵션을 추가했다.

```bash
--initial-prompt "..."
```

환경 변수도 지원한다.

```bash
STT_INITIAL_PROMPT="..."
```

## Generic Prompt

```text
Preserve English technical terms in Latin letters. The audio contains Korean-English mixed software engineering commands. Do not translate or transliterate English words into Korean.
```

검증 명령:

```bash
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none --initial-prompt "Preserve English technical terms in Latin letters. The audio contains Korean-English mixed software engineering commands. Do not translate or transliterate English words into Korean." --output output/suite/hike-code-switch-core-v1-large-v3-cuda-float16-prompt.json
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16-prompt.json --output output/suite/hike-code-switch-core-v1-large-v3-cuda-float16-prompt-analysis.json
```

결과:

- `language=ko`: 15/28, 53.57%.
- `language=auto`: 15/28, 53.57%.
- Exact pass: 0/5.
- Normalized pass: 0/5.

## Glossary Prompt

```text
Korean-English mixed transcript. Keep spoken English terms in Latin letters. Common terms include bug, session, management, logic, sprint, API, gateway, migration, complex, deadline, client, presentation, PowerPoint, slides, review, QA, actually, database, schema, user, table, column.
```

결과:

- `language=ko`: 15/28, 53.57%.
- `language=auto`: 15/28, 53.57%.
- Exact pass: 0/5.
- Normalized pass: 0/5.

## Observations

- Baseline은 14/28, 50%.
- Prompt 적용 후 `actually`는 Latin-script로 보존됐다.
- `bug`, `session`, `management`, `logic`은 계속 `버그`, `세션`, `매니지먼트`, `로직` 계열로 변환됐다.
- `client presentation`, `PowerPoint slides`, `review`, `QA session`도 한글 외래어 표기로 변환됐다.
- `language=ko`와 `language=auto`의 보존율 차이는 없었다.

## Decision

- `initial_prompt`는 작은 개선만 보였다.
- Codex CLI 입력의 파일명, 옵션명, 코드 식별자 문제를 해결할 핵심 수단으로 보기 어렵다.
- `initial_prompt` 옵션은 실험 도구로 유지한다.
- 다음 핵심 prototype은 deterministic workspace token recovery다.
