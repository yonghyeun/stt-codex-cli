# Phase 9: Clipboard Copy

## Scope

- 텍스트를 system clipboard에 복사한다.
- 입력은 command argument 또는 stdin으로 받는다.
- 복사 후 clipboard를 다시 읽어 검증한다.
- STT, token recovery, push-to-talk UX와는 아직 통합하지 않는다.

## Script

- `scripts/copy_text.sh`.

## Backend

- Default: `auto`.
- Current local backend: `xclip`.
- Wayland 환경에서는 `wl-copy`와 `wl-paste`가 모두 있으면 `wl-copy` backend를 사용할 수 있다.

## Commands

stdin 입력:

```bash
echo "README.md 수정해" | scripts/copy_text.sh
```

argument 입력:

```bash
scripts/copy_text.sh "README.md 수정해"
```

backend 명시:

```bash
scripts/copy_text.sh --backend xclip "README.md 수정해"
```

검증 생략:

```bash
scripts/copy_text.sh --no-verify "README.md 수정해"
```

## Result

- `scripts/copy_text.sh --help` 성공.
- stdin 입력 복사 성공.
- argument 입력 복사 성공.
- `auto` backend가 local 환경에서 `xclip`로 resolve됨.
- `--no-verify` 복사 성공.
- `xclip -selection clipboard -out` 검증 성공.
- invalid backend는 exit 2로 실패.
- 빈 stdin은 exit 2로 실패.

## Decision

- clipboard primitive는 `xclip` 기반으로 사용 가능하다.
- script stdout에는 복사된 텍스트를 출력한다.
- script stderr에는 backend와 검증 여부를 출력한다.
- `xclip` 쓰기 단계는 stdout/stderr를 닫아 command substitution에서 반환이 막히지 않게 한다.
- Codex CLI 자동 전송은 여전히 하지 않는다.

## Follow-up

- STT, token recovery, clipboard copy를 하나의 명령으로 묶는다.
- clipboard test가 사용자 clipboard를 변경하므로 통합 검증 시 이전 clipboard 복원 방식을 둔다.
