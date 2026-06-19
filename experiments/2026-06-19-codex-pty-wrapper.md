# Phase 13: Codex PTY Wrapper

## Scope

- Codex CLI를 child PTY로 실행한다.
- 사용자 stdin을 child PTY로 전달한다.
- child PTY output을 현재 terminal stdout으로 전달한다.
- STT, 녹음, prompt injection은 아직 연결하지 않는다.

## Script

- `scripts/stt_codex.py`.

## Commands

기본 실행:

```bash
scripts/stt_codex.py
```

검증용 child command:

```bash
scripts/stt_codex.py --cmd python3 -- -q
```

## Behavior

- 기본 command는 `codex`다.
- `--cmd`로 child command를 바꿀 수 있다.
- `--` 뒤의 argument는 child command에 전달한다.
- terminal이 TTY이면 raw mode로 전환해 key 입력을 child PTY에 직접 전달한다.
- child process exit code를 wrapper exit code로 반환한다.

## Result

- `python3 -m py_compile scripts/stt_codex.py` 성공.
- `scripts/stt_codex.py --help` 성공.
- 존재하지 않는 `--cwd`는 실패한다.
- child process exit code passthrough 확인.
- PTY에서 `hello` 입력이 child command로 전달되는 것 확인.
- `scripts/stt_codex.py --cmd codex -- --help` 성공.

## Decision

- Phase 13은 PTY passthrough까지만 다룬다.
- STT raw transcript injection은 다음 phase에서 다룬다.
- Codex CLI 자동 전송은 하지 않는다.

## Risk

- terminal raw mode를 사용하므로 wrapper crash 시 terminal 상태 복구가 중요하다.
- child PTY와 terminal resize 동기화는 `SIGWINCH`에서 처리한다.
- 자동화 검증은 실제 Codex CLI 대신 작은 child command로 수행한다.
