# Phase 12: Push to Talk

## Scope

- 키를 누르면 녹음을 시작한다.
- 키를 떼면 녹음을 종료한다.
- 녹음된 WAV를 기존 `stt_clipboard.sh` 흐름으로 보낸다.
- 기본 hotkey는 `t` 단독키다.
- 사용자가 keycode와 modifier keycode를 바꿀 수 있다.

## Script

- `scripts/push_to_talk.py`.

## Default Hotkey

- Trigger: `t`, keycode `28`.
- Modifier: 없음.
- Alt 조합을 쓰려면 `--require-modifier --modifier-keycodes 64,108,204`를 지정한다.

확인 명령:

```bash
xmodmap -pke | grep -E 'Alt_L|Alt_R| t '
```

## Commands

정확도 기준 모델:

```bash
scripts/push_to_talk.py -- --model large-v3 --device cuda --compute-type float16
```

녹음 파일 생성만 확인:

```bash
scripts/push_to_talk.py --record-only
```

hotkey 변경:

```bash
scripts/push_to_talk.py --keycode 74 --no-modifier --record-only
```

Alt+T:

```bash
scripts/push_to_talk.py --keycode 28 --require-modifier --modifier-keycodes 64,108,204 --record-only
```

## Result

- `xinput test-xi2 --root`에서 key press/release event 확인.
- `xdotool`로 `Alt+T` keydown/keyup 시뮬레이션 가능 확인.
- `scripts/push_to_talk.py --help` 성공.
- invalid keycode는 argparse 단계에서 실패.
- `--record-only`와 `xdotool keydown Alt_L keydown t ... keyup t keyup Alt_L` 조합으로 WAV 생성 확인.
- 생성 WAV는 16kHz mono로 확인했다.
- `--modifier-keycodes 64`처럼 modifier 목록을 바꿔도 동작 확인했다.
- `--listen-timeout 2`는 hotkey 입력이 없으면 실패한다.

## Decision

- Phase 12는 XInput 기반 prototype으로 둔다.
- default는 `t` 단독키다.
- keycode와 modifier keycode는 사용자 설정 가능하다.
- STT 결과는 여전히 clipboard 복사까지만 수행한다.
- Codex CLI 자동 전송은 하지 않는다.

## Risk

- 현재 세션은 Wayland + Xwayland다.
- `xinput`은 Xwayland server에 대해 실행된다는 경고를 출력한다.
- 일부 Wayland compositor 또는 app focus 상태에서는 전역 key event 감지가 제한될 수 있다.
- XInput 방식은 key event를 감지할 뿐 입력을 grab하지 않는다.
- terminal/tmux focus 상태에서는 `t` 문자가 같이 입력될 수 있다.

## Follow-up

- 실제 사용자 발화로 end-to-end latency와 정확도를 기록한다.
- 필요하면 desktop shortcut 또는 전역 hotkey daemon 방식을 별도 검토한다.
