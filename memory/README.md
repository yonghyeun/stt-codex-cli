# Memory

수동 token recovery memory 위치.

## Contract

- STT 원문 transcript를 직접 수정하지 않는다.
- Codex/workspace 입력에 필요한 복원본만 별도로 만든다.
- memory는 JSON object다.
- `version`은 `1`이다.
- `entries`는 수동 alias 목록이다.
- entry의 `confidence`는 `0` 이상 `1` 이하다.
- 낮은 confidence entry는 `scripts/recover_tokens.py --min-confidence` 기준에 따라 무시된다.

## Entry

```json
{
  "spoken": "리드미",
  "target": "README.md",
  "scope": "workspace",
  "confidence": 0.99,
  "source": "manual"
}
```

- `spoken`: STT 결과에 나타날 수 있는 한국어 발음 또는 표현.
- `target`: Codex 입력에 필요한 실제 token.
- `scope`: `global`, `workspace`, `personal` 중 하나.
- `confidence`: 자동 복원에 사용할 신뢰도.
- `source`: `manual` 같은 출처 문자열.

## Example

```bash
scripts/recover_tokens.py --memory memory/manual-aliases.example.json "리드미 수정해"
```

기대 출력:

```text
README.md 수정해
```

개인 memory는 `memory/*.local.json`에 둔다. 이 파일들은 Git 추적 대상이 아니다.
