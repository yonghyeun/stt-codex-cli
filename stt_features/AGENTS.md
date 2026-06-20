# Feature Agent Routing

`stt_features/**` 변경 전에는 `stt_features/README.md`를 먼저 읽는다.

## Routing Rule

- `stt_features`는 사용자가 얻는 STT 입력 보조 flow를 소유한다.
- `stt_features`는 `stt_core`와 `stt_runtime`을 조합할 수 있다.
- `stt_features`는 `scripts`를 import하지 않는다.
- CLI option parsing과 command compatibility는 `scripts` 소유다.

