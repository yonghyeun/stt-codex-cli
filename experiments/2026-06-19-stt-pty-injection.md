# Phase 15: STT PTY Injection

## Scope

- wrapper parent가 push-to-talk 녹음을 수행한다.
- 녹음된 임시 WAV를 로컬 STT로 변환한다.
- STT raw transcript를 child PTY 입력창에 삽입한다.
- Enter 자동 전송은 하지 않는다.
- token recovery는 하지 않는다.

## Script

- `scripts/stt_codex.py`.

## Behavior

- 기본 injection mode는 `stt`다.
- 기본 trigger는 `ctrl+t`다.
- trigger 반복 입력이 시작되면 recording을 시작한다.
- trigger 반복 입력이 `--release-gap` 동안 끊기면 recording을 종료한다.
- recording이 `--min-duration`보다 짧으면 STT 없이 버린다.
- recording이 `--max-duration`을 넘으면 자동 종료한다.
- STT가 끝나면 raw transcript를 child PTY에 쓴다.
- transcript가 비어 있거나 punctuation-only이면 삽입하지 않는다.
- 임시 WAV는 기본 삭제한다.
- `--keep-audio`를 주면 임시 WAV를 남긴다.

## Commands

기본 실행:

```bash
scripts/stt_codex.py
```

정확도 기준 모델:

```bash
scripts/stt_codex.py --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

검증용 small model:

```bash
scripts/stt_codex.py --stt-model tiny --stt-device cpu --stt-compute-type int8 --cmd python3 -- -q
```

## Decision

- STT mode를 기본 mode로 둔다.
- STT mode의 기본 trigger는 `ctrl+t`다.
- `ctrl+t`는 child PTY로 전달하지 않고 parent가 소비한다.
- fixed-text injection은 `--inject-mode fixed-text`로 유지한다.
- 자동 전송은 하지 않는다.
- token recovery는 후속 기능으로 둔다.

## Result

- `python3 -m py_compile scripts/stt_codex.py` 성공.
- `scripts/stt_codex.py --help` 성공.
- invalid `--inject-mode`는 argparse 단계에서 실패.
- invalid duration은 argparse 단계에서 실패.
- `--inject-mode fixed-text`는 기존 방식대로 동작 확인.
- `tiny/cpu/int8` STT smoke test에서 recording start/stop, STT 호출, empty transcript skip, temporary audio deletion 확인.

## Verification Gap

- 실제 발화 transcript가 child PTY에 삽입되는 end-to-end 검증은 사용자 마이크 품질에 의존한다.
- 자동 검증에서는 무발화였기 때문에 transcript가 비어 삽입을 생략했다.
- non-empty injection 경로는 fixed-text injection 검증과 같은 child PTY write path를 사용한다.

## Risk

- `ctrl+t`가 terminal/tmux 설정과 충돌할 수 있다.
- terminal key repeat가 꺼져 있으면 release 추정이 빨리 끝날 수 있다.
- STT 수행 중 wrapper event loop가 잠시 block된다.
