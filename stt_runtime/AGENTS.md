# Runtime Agent Routing

`stt_runtime/**` 변경 전에는 `stt_runtime/README.md`를 먼저 읽는다.

## Routing Rule

- `stt_runtime`은 OS, subprocess, PTY, terminal, filesystem side effect adapter를 소유한다.
- `stt_runtime`은 `stt_core`의 순수 data contract를 사용할 수 있다.
- `stt_runtime`은 `scripts`나 `stt_features`를 import하지 않는다.
- 사용자 use-case 순서 조립은 `stt_features` 소유로 둔다.

