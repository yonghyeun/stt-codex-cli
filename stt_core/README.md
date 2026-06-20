# STT Core Layer

`stt_core/`는 실행환경과 무관한 순수 판단과 data contract를 둔다.

## Ownership

- Transcript 판정.
- Run outcome 이름과 metadata shape의 순수 구성.
- Token recovery의 순수 변환.
- 설정값을 실제 runtime 호출 전에 검증하는 deterministic helper.
- 같은 입력에 대해 같은 출력을 반환하는 작은 정책 함수.

## Allowed Dependencies

- Python standard library의 순수 계산용 module.
- `dataclasses`, `typing`, `pathlib`처럼 side effect 없이 값 shape를 표현하는 module.
- 같은 `stt_core` 내부 module.

## Forbidden Responsibilities

- `arecord` 실행.
- `transcribe.sh` 또는 faster-whisper subprocess 호출.
- child PTY 생성, read, write.
- terminal raw mode, signal, window-size 제어.
- 실제 파일 생성, 이동, 삭제.
- CLI argument parsing.
- 사용자 status line 출력.
- use-case 순서 조립.

## Dependency Direction

허용:

```text
stt_core -> standard library
```

금지:

```text
stt_core -> scripts
stt_core -> stt_runtime
stt_core -> stt_features
```

## Placement Guide

- `transcript_has_text()` 같은 판정은 `stt_core` 후보다.
- `run_id_from_timestamp()` 같은 이름 생성은 `stt_core` 후보다.
- `save_run_artifacts()`처럼 실제 파일을 쓰는 함수는 `stt_core`가 아니다.
- `subprocess.run(...)`이 필요하면 `stt_runtime` 후보다.
- 녹음부터 삽입까지의 전체 흐름을 말하면 `stt_features` 후보다.

