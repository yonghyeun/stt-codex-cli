# STT Features Layer

`stt_features/`는 사용자-facing use-case flow를 조립한다.

## Ownership

- 사용자가 인식하는 기능 단위의 workflow.
- Core 판단과 runtime adapter를 조합한 feature outcome.
- Runtime 실패를 사용자 flow의 결과로 연결하는 orchestration.
- 기능 정책과 실행 순서.

## Allowed Dependencies

- `stt_core`.
- `stt_runtime`.
- Python standard library의 flow 제어용 module.

## Forbidden Responsibilities

- CLI argument parser의 source of truth.
- Runtime adapter의 low-level 구현.
- 외부 process, device, terminal, PTY, filesystem 직접 제어.
- 순수 data contract 판단 재정의.
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

## Placement Rule

- 여러 core/runtime 동작을 사용자 기능으로 묶으면 `stt_features`에 둔다.
- CLI option parsing은 `stt_features`에 두지 않는다.
- 외부 resource를 직접 조작하는 low-level adapter는 `stt_features`에 두지 않는다.
