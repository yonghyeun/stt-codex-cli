# STT Runtime Layer

`stt_runtime/`은 코드 바깥 세계와 닿는 adapter를 둔다.

## Ownership

- ALSA `arecord` 녹음 시작과 종료.
- Temporary audio file 생성과 삭제.
- `scripts/transcribe.sh` subprocess 호출.
- child PTY 생성, read, write.
- terminal raw mode 설정과 복구.
- window-size sync.
- signal handling.
- run artifact의 실제 파일 write, move, copy.

## Allowed Dependencies

- `stt_core`.
- Python standard library runtime module.
- `os`, `pty`, `termios`, `tty`, `signal`, `selectors`, `subprocess`, `tempfile`, `shutil`.

## Forbidden Responsibilities

- CLI argument parsing의 source of truth.
- 사용자-facing feature policy 결정.
- transcript 의미 판정의 source of truth.
- token recovery 정책 소유.
- 전체 use-case 순서 조립.
- `scripts` entrypoint import.

## Dependency Direction

허용:

```text
stt_runtime -> stt_core
stt_runtime -> standard library
```

금지:

```text
stt_runtime -> scripts
stt_runtime -> stt_features
```

## Placement Guide

- `start_recording()`과 `stop_recording()`은 `stt_runtime`에 둔다.
- `transcribe_audio()`의 subprocess adapter는 `stt_runtime`에 둔다.
- `spawn_child()`와 `TerminalMode`는 `stt_runtime`에 둔다.
- `transcript_has_text()`는 `stt_runtime`이 아니라 `stt_core`에 둔다.
- `finish_recording_and_inject()`처럼 흐름을 조립하는 함수는 `stt_features`에 둔다.
