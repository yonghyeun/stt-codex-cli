# Core Agent Routing

`stt_core/**` 변경 전에는 `stt_core/README.md`를 먼저 읽는다.

## Routing Rule

- `stt_core`는 실행환경과 무관한 순수 판단과 data contract를 소유한다.
- `stt_core`는 `scripts`, `stt_runtime`, `stt_features`를 import하지 않는다.
- OS, subprocess, PTY, terminal, filesystem write가 필요하면 `stt_runtime` 소유로 돌린다.
- 사용자 use-case flow 조립이 필요하면 `stt_features` 소유로 돌린다.

