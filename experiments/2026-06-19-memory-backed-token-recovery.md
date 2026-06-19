# Phase 8: Memory-Backed Token Recovery

## Scope

- STT 없이 텍스트 transcript만 입력한다.
- LLM, GPU, network는 사용하지 않는다.
- 수동 memory 파일을 읽어 Codex/workspace token을 복원한다.
- Codex skill 기반 memory 업데이트는 후속 phase로 둔다.

## Files

- Script: `scripts/recover_tokens.py`.
- Memory contract: `memory/README.md`.
- Example memory: `memory/manual-aliases.example.json`.
- Fixture: `fixtures/token-recovery-v1.json`.

## Memory Format

```json
{
  "version": 1,
  "entries": [
    {
      "spoken": "리드미",
      "target": "README.md",
      "scope": "workspace",
      "confidence": 0.99,
      "source": "manual"
    }
  ]
}
```

## Commands

단일 transcript 복원:

```bash
scripts/recover_tokens.py --memory memory/manual-aliases.example.json "리드미 수정해"
```

Fixture 검증:

```bash
scripts/recover_tokens.py --fixture fixtures/token-recovery-v1.json
```

JSON 출력:

```bash
scripts/recover_tokens.py --json --memory memory/manual-aliases.example.json "이니셜 프롬프트 옵션 추가해"
```

## Result

- Fixture total: 8.
- Passed: 8.
- Failed: 0.

검증된 예:

| input | output |
| --- | --- |
| `리드미 수정해` | `README.md 수정해` |
| `리드미 파일 열어` | `README.md 열어` |
| `스크립트 트랜스크라이브 파이 열어` | `scripts/transcribe.py 열어` |
| `이니셜 프롬프트 옵션 추가해` | `--initial-prompt 옵션 추가해` |
| `이니셜프롬프트 옵션 추가해` | `--initial-prompt 옵션 추가해` |
| `컴퓨트 타입 인자 검증해` | `--compute-type 인자 검증해` |
| `라지 브이 쓰리로 테스트해` | `large-v3로 테스트해` |
| `그냥 세션 설명해` | `그냥 세션 설명해` |

## Decision

- 수동 memory 기반 token recovery는 작은 범위에서 동작한다.
- 일반 한국어 문장을 건드리지 않는 기준을 유지한다.
- phrase 단위 수동 memory는 정확하지만 확장성은 제한된다.
- 다음 phase에서는 자동 후보 수집 또는 Codex skill 기반 memory update 후보 생성을 검토한다.

## Follow-up

- `STT_TOKEN_MEMORY`를 실제 개인 memory 파일로 지정하는 사용 흐름 추가.
- workspace 파일명/옵션명 후보 자동 수집.
- Codex skill이 작업 context를 보고 memory update 후보를 제안하는 phase 추가.
