# STT Runtime Layer

`stt_runtime/`은 코드 바깥 세계와 닿는 adapter를 둔다.

## Ownership

- 코드 바깥 세계와 통신하는 adapter.
- 외부 process 실행과 결과 수집.
- Device, terminal, PTY, signal 같은 runtime resource 제어.
- Filesystem persistence와 temporary resource lifecycle.
- Runtime 실패를 호출자가 다룰 수 있는 값이나 예외로 정규화.

## Allowed Dependencies

- `stt_core`.
- Python standard library runtime module.
- OS, subprocess, terminal, filesystem 처리를 위한 standard library module.

## Forbidden Responsibilities

- CLI argument parsing의 source of truth.
- 사용자-facing feature policy 결정.
- 순수 data contract 판단의 source of truth.
- 여러 adapter를 기능 단위로 조립하는 use-case flow.
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

## Placement Rule

- 외부 process, device, terminal, PTY, filesystem을 직접 다루면 `stt_runtime`에 둔다.
- 외부 세계와 닿지 않는 판단은 `stt_runtime`에 두지 않는다.
- 사용자가 인식하는 기능 순서 조립은 `stt_runtime`에 두지 않는다.
