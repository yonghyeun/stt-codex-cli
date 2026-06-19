# Phase 14: Fixed Text Injection

## Scope

- wrapper parent가 child PTY에 고정 텍스트를 삽입한다.
- STT와 녹음은 아직 연결하지 않는다.
- 자동 전송은 하지 않는다.

## Script

- `scripts/stt_codex.py`.

## Behavior

- 기본 injection key는 `ctrl+t`다.
- 기본 injection text는 `hello from stt wrapper`다.
- injection key를 누르면 parent가 child PTY에 text bytes를 쓴다.
- Enter는 삽입하지 않는다.
- 사용자가 삽입된 텍스트를 확인한 뒤 직접 Enter를 누른다.

## Commands

기본 실행:

```bash
scripts/stt_codex.py
```

검증용 child command:

```bash
scripts/stt_codex.py --cmd python3 -- -c 'import sys; print("child:" + sys.stdin.readline().strip())'
```

## Decision

- 기본 trigger는 `ctrl+t`로 둔다.
- `t` 단독키는 일반 타이핑과 충돌하므로 기본값으로 쓰지 않는다.
- `--inject-key t`처럼 사용자가 직접 바꾸는 것은 허용한다.
- Enter 자동 전송은 하지 않는다.

## Result

- `python3 -m py_compile scripts/stt_codex.py` 성공.
- `scripts/stt_codex.py --help` 성공.
- invalid `--inject-key ctrl+`는 argparse 단계에서 실패.
- `--disable-inject-key` 실행 경로 확인.
- PTY에서 `ctrl+t` 입력 후 Enter를 보내 child command가 `hello from stt wrapper`를 읽는 것 확인.
- parent status line이 injection 시점에 `[stt-parent] injected ...`로 표시되는 것 확인.

## Risk

- parent status line이 child prompt와 같은 terminal에 출력되므로 화면이 다소 섞일 수 있다.
- control key가 사용자의 terminal/tmux 설정과 충돌할 가능성이 있다.
