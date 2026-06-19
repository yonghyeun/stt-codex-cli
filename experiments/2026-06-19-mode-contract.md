# Phase 7: Input Mode Contract

## Scope

- 도구를 repo 전용이 아닌 일반 Linux 데스크탑 STT 입력기로 유지한다.
- Codex CLI와 repo 작업에서는 선택적 context 보정 mode를 둔다.
- 한영 혼합 STT 결과를 무조건 Latin-script로 강제하지 않는다.

## Problem

한국어에서는 `session`, `bug`, `logic` 같은 단어가 `세션`, `버그`, `로직`으로 표기되는 것이 자연스럽다.

따라서 한영 혼합 STT 결과에서 외래어가 한글로 표기됐다는 이유만으로 오인식으로 판단하면 기준이 과도하다.

다만 Codex CLI 입력에서는 다음 토큰이 의미뿐 아니라 문자열 자체로 중요하다.

- 파일명: `README.md`, `transcribe.py`.
- 디렉터리명: `scripts/`, `fixtures/`.
- CLI 옵션: `--initial-prompt`, `--compute-type`.
- 코드 식별자: `initial_prompt_arg`, `run_fixture_suite`.
- 패키지명과 모델명: `faster-whisper`, `large-v3`.

이 문맥에서는 `트랜스크라이브 파이`를 `transcribe.py`로 복원해야 한다.

## Modes

### General Mode

- 기본 mode.
- repo context를 읽지 않는다.
- STT 결과를 최대한 그대로 둔다.
- 자연스러운 한국어 외래어 표기를 허용한다.
- 범용 메모, 검색, 일반 채팅 입력에 적합하다.

### Workspace Mode

- 사용자가 repo 또는 작업 디렉터리 안에서 켠다.
- 현재 디렉터리 기준으로 후보를 자동 수집한다.
- 필수 설정 파일 없이 동작해야 한다.
- 후보 예시:
  - `rg --files` 파일 목록.
  - 디렉터리명.
  - 실행 스크립트명.
  - CLI 옵션명.
  - 코드 식별자.
- 확신 높은 복원만 적용한다.
- 확신 낮은 복원은 사용자 확인 대상으로 남긴다.

### Personal Vocabulary Mode

- 선택 mode.
- 사용자가 자주 쓰는 프로젝트명, 도구명, 약어를 추가한다.
- Workspace mode와 독립적으로 사용할 수 있다.
- 과도한 설정 의존을 피하기 위해 작은 사전으로 시작한다.

## Correction Policy

- 원문 STT transcript는 항상 보존한다.
- 복원된 Codex용 transcript는 별도 값으로 만든다.
- 일반 문장은 자동 수정하지 않는다.
- 파일명, 옵션명, 코드 식별자 후보는 confidence score를 계산한다.
- confidence가 낮으면 원문을 유지한다.
- 자동 Codex CLI 전송은 하지 않는다.

## Decision

- 제품 기본값은 General mode다.
- Workspace token recovery는 opt-in 또는 context 감지형 보조 기능으로 둔다.
- `initial_prompt`는 보조 실험 도구로 유지하되 핵심 해결책으로 보지 않는다.
- 파일명/옵션명 문제는 STT 모델 정확도 문제가 아니라 context-aware token recovery 문제로 다룬다.

## Next Prototype

- STT 없이 fixture 텍스트로 token recovery를 먼저 만든다.
- 입력 예시:
  - `리드미 수정해`.
  - `스크립트 트랜스크라이브 파이 열어`.
  - `이니셜 프롬프트 옵션 추가해`.
- 기대 출력:
  - `README.md 수정해`.
  - `scripts/transcribe.py 열어`.
  - `--initial-prompt 옵션 추가해`.
- 첫 구현은 CPU-only deterministic matching으로 제한한다.
