# Phase 13.5: Parent Child Terminal Boundary

## Scope

- wrapper parent와 child PTY output의 시각적 경계를 만든다.
- parent가 직접 출력하는 status line은 prefix로 표시한다.
- child output은 그대로 둔다.
- STT와 prompt injection은 아직 다루지 않는다.

## Script

- `scripts/stt_codex.py`.

## Behavior

- parent status prefix는 `[stt-parent]`다.
- TTY에서는 parent prefix를 cyan으로 표시한다.
- `--no-color`로 색상을 끌 수 있다.
- `--quiet-parent`로 parent status line을 숨길 수 있다.
- 기본 Codex 실행에는 `--no-alt-screen`을 자동 추가한다.
- `--codex-alt-screen`을 주면 Codex alternate screen을 유지한다.

## Example

```text
[stt-parent] starting child: codex --no-alt-screen
[stt-parent] cwd: /home/yonghyeun/stt-codex-cli
[stt-parent] child output follows
------------------------------------------------
[stt-parent] child pid: 12345

<child output>
```

## Decision

- parent output은 명확한 prefix를 붙인다.
- child output은 변형하지 않는다.
- Codex TUI가 화면을 덮어 parent 표시를 숨기지 않도록 `--no-alt-screen`을 기본 적용한다.
- 자동 전송은 여전히 하지 않는다.

## Result

- `python3 -m py_compile scripts/stt_codex.py` 성공.
- `scripts/stt_codex.py --help` 성공.
- 기본 parent status line 출력 확인.
- `--quiet-parent`가 parent status line을 숨기는 것 확인.
- `scripts/stt_codex.py --cmd codex -- --help`에서 `codex --no-alt-screen --help`로 실행되는 것 확인.
- `--codex-alt-screen` 사용 시 `--no-alt-screen` 자동 추가가 꺼지는 것 확인.
- `--no-color` option이 argparse와 실행 경로에서 동작하는 것 확인.

## Risk

- child TUI가 직접 화면을 제어하면 parent status line이 가려질 수 있다.
- `--codex-alt-screen`을 사용하면 parent/child 경계가 scrollback에 남지 않을 수 있다.
