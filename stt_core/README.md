# STT Core Layer

`stt_core/`는 실행환경과 무관한 순수 판단과 data contract를 둔다.

## Ownership

- 실행환경 없이 판단 가능한 data contract.
- 같은 입력에 대해 같은 출력을 반환하는 deterministic transformation.
- Runtime 실행 전에 끝낼 수 있는 값 검증과 분류.
- 외부 상태를 읽지 않는 정책 함수.

## Allowed Dependencies

- Python standard library의 순수 계산용 module.
- Side effect 없이 값 shape를 표현하는 module.
- 같은 `stt_core` 내부 module.

## Forbidden Responsibilities

- 외부 process 실행.
- device, terminal, PTY, signal 제어.
- 실제 파일 생성, 이동, 삭제.
- CLI argument parsing.
- 사용자 입출력.
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

## Placement Rule

- 코드 바깥의 상태를 읽거나 바꾸지 않으면 `stt_core`에 둔다.
- 외부 실행환경이 필요하면 `stt_core`가 아니다.
- 여러 runtime 단계를 사용자 기능으로 엮으면 `stt_core`가 아니다.
