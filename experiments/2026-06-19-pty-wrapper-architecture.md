# Phase 13+: PTY Wrapper Architecture

## Scope

- 이 프로젝트의 다음 목표는 clipboard 보조 도구가 아니라 Codex CLI wrapper다.
- wrapper는 Codex CLI를 child PTY로 실행한다.
- 사용자는 wrapper 안에서 Codex CLI output을 그대로 본다.
- 사용자가 말하면 로컬 STT 결과가 Codex CLI 입력창에 삽입된다.
- Enter 전송은 사용자가 직접 한다.

## Non-Scope

- Codex CLI 수정.
- STT 결과 자동 전송.
- token recovery 기본 적용.
- workspace metadata 기반 파일명/옵션명 복원.
- OpenCode 지원.
- 음성 명령.

## Architecture

```text
terminal
  -> stt-codex wrapper
    -> child PTY: codex cli
    -> terminal input passthrough
    -> codex output passthrough
    -> push-to-talk controller
    -> recorder
    -> local STT transcriber
    -> prompt injector
```

## Data Flow

```text
speech
  -> temp wav
  -> local STT
  -> raw transcript
  -> child PTY input buffer
  -> user review
  -> user Enter
```

## Storage Policy

- 기본값은 저장하지 않는다.
- 녹음 중에는 임시 WAV 파일을 사용할 수 있다.
- STT가 끝나면 임시 WAV 파일을 삭제한다.
- transcript도 기본적으로 저장하지 않는다.
- 사용자가 명시적으로 저장 옵션을 켠 경우에만 run artifact를 남긴다.

저장 옵션 예시:

```text
--save-audio
--save-transcript
--save-run
```

저장 위치 예시:

```text
output/runs/<timestamp>/
  audio.wav
  transcript.txt
  metadata.json
```

## Phase Plan

1. PTY wrapper를 추가한다.
2. Codex CLI 입출력 passthrough를 검증한다.
3. wrapper에서 고정 텍스트 injection을 검증한다.
4. push-to-talk 녹음을 wrapper에 연결한다.
5. STT raw transcript를 Codex CLI 입력창에 삽입한다.
6. 임시 audio 기본 삭제와 선택 저장 옵션을 적용한다.

## Decision

- 다음 구현 대상은 PTY wrapper다.
- token recovery는 후속 기능으로 뺀다.
- 정확도 개선 전까지 자동 전송은 하지 않는다.
- audio와 transcript는 기본 삭제한다.
