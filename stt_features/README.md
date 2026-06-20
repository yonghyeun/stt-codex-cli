# STT Features Layer

`stt_features/`는 사용자-facing use-case flow를 조립한다.

## Ownership

- 녹음 시작부터 transcript 삽입까지의 workflow.
- Fixed text injection workflow.
- STT transcript injection workflow.
- Optional run artifact 저장 여부를 포함한 feature-level outcome 조립.
- Runtime adapter 실패를 사용자 flow 결과로 연결하는 orchestration.

## Allowed Dependencies

- `stt_core`.
- `stt_runtime`.
- Python standard library의 flow 제어용 module.

## Forbidden Responsibilities

- CLI argument parser의 source of truth.
- child PTY나 terminal raw mode의 low-level 구현.
- `arecord` command 직접 구성.
- faster-whisper subprocess 직접 호출.
- 순수 transcript/data contract 판단 재정의.
- `scripts` entrypoint import.

## Dependency Direction

허용:

```text
stt_features -> stt_runtime
stt_features -> stt_core
```

금지:

```text
stt_features -> scripts
```

## Placement Guide

- `finish_recording_and_inject()`는 `stt_features` 후보다.
- `handle_stt_ptt_input()`은 runtime input을 feature event로 해석하므로 migration 때 경계 재검토가 필요하다.
- `inject_transcript()`는 low-level PTY write와 feature message가 섞여 있으므로 migration 때 split 후보다.
- `parse_args()`는 `scripts`에 남긴다.
- `transcribe_audio()`의 subprocess 호출은 `stt_runtime`에 둔다.

