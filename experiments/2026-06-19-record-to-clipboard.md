# Phase 11: Record to Clipboard

## Scope

- 마이크 입력을 정해진 시간 녹음한다.
- 생성된 WAV 파일을 `scripts/stt_clipboard.sh`로 넘긴다.
- STT, token recovery, clipboard copy를 한 명령에서 실행한다.
- push-to-talk UX는 아직 구현하지 않는다.

## Script

- `scripts/record_clipboard.sh`.

## Interface

```bash
scripts/record_clipboard.sh [options] [duration_seconds] [-- transcribe options...]
```

`--` 앞의 option은 record/clipboard wrapper가 처리한다.

- `--duration SECONDS`
- `--record-only`
- `--no-recovery`
- `--memory PATH`
- `--min-confidence VALUE`
- `--clipboard-backend BACKEND`
- `--no-copy-verify`
- `--output-transcript PATH`
- `--output-recovered PATH`

`--` 뒤의 option은 `scripts/transcribe.sh`에 전달한다.

## Commands

정확도 기준 모델:

```bash
scripts/record_clipboard.sh --duration 5 -- --model large-v3 --device cuda --compute-type float16
```

짧은 CPU smoke path:

```bash
scripts/record_clipboard.sh --duration 3 -- --model tiny --device cpu --compute-type int8
```

녹음 파일 생성만 확인:

```bash
scripts/record_clipboard.sh --record-only --duration 1
```

## Result

- `scripts/record_clipboard.sh --help` 성공.
- invalid duration은 exit 2로 실패.
- transcribe option을 `--` 앞에 두면 exit 2로 실패.
- `--record-only --duration 1`로 16kHz mono WAV 생성 확인.
- 무발화 1초 녹음은 punctuation-only transcript로 환각될 수 있었다.
- `stt_clipboard.sh`에 Python `str.isalnum()` 기반 meaningful text guard를 추가해 punctuation-only transcript를 실패 처리했다.
- 기존 KSS fixture audio로 Phase 10 하위 통합 경로가 동작하는 것을 확인했다.

## Verification Note

자동 검증 환경에서는 내가 실제로 말할 수 없어서 full live recording path의 transcript 품질은 검증하지 않았다.

1초 무발화 녹음은 모델에 따라 빈 transcript 또는 punctuation-only transcript가 될 수 있다. 실제 사용 검증은 사용자가 명령 실행 중 말해야 한다.

## Decision

- 녹음부터 clipboard까지 이어지는 첫 통합 명령을 추가했다.
- 생성된 녹음 파일은 기존 `record.sh` 계약대로 `output/recordings/`에 남긴다.
- STT 결과가 비거나 의미 있는 문자를 포함하지 않으면 clipboard에 복사하지 않고 실패한다.
- Codex CLI 자동 전송은 하지 않는다.

## Follow-up

- push-to-talk 방식으로 녹음 시작/종료를 제어한다.
- 실제 발화 샘플로 end-to-end 정확도와 latency를 기록한다.
