# STT Accuracy Suites

STT accuracy 평가 입력 selection과 metric 적용 계약.

suite는 공유 input corpus를 복사하거나 소유하지 않는다. suite는 어떤 input sample을 어떤 metric으로 평가할지 정한다.

## Ownership

- suite naming.
- manifest schema 설명.
- example manifest.
- active suite manifest.
- 공개 가능 여부 정책.
- input set 참조 규칙.
- sample id 참조 규칙.
- suite별 README.
- metric list와 case selection.

## Non-Ownership

- 실제 audio 저장.
- expected transcript 저장.
- sample metadata 저장.
- raw transcript 저장.
- recovered transcript 저장.
- raw result 저장.
- 개인 glossary 저장.

위 산출물은 `evals/inputs/**`, `evals/stt_accuracy/runs/**`, 또는 `memory/*.local.json`이 소유한다.

## Manifest Rules

Git에 두는 것:

```text
evals/stt_accuracy/suites/codex-command-accuracy-v1/
  manifest.schema.json
  manifest.example.json
  manifest.json
```

local-only로 두는 것:

```text
evals/inputs/speech/v1/samples/<sample_id>/audio.wav
evals/stt_accuracy/runs/<run_id>/
```

`manifest.json`은 `input_set`과 `sample_id`를 참조한다.

예시:

```json
{
  "suite_id": "codex-command-accuracy-v1",
  "input_set": "speech/v1",
  "cases": [
    {
      "case_id": "file-path-001",
      "sample_id": "cmd-0001",
      "category": "file_path",
      "metrics": ["file_path_preservation", "insertion_safe"]
    }
  ]
}
```

manifest는 audio, expected, raw transcript 파일 경로를 직접 소유하지 않는다.

## Expected Transcript Rule

expected transcript는 STT가 들은 결과가 아니다. 사용자가 원래 Codex에 넣고 싶었던 최종 입력문이다.

원칙:

- expected transcript는 `evals/inputs/speech/v1/samples/<sample_id>/expected.txt`가 소유한다.
- 파일명, 경로, CLI option, 코드 식별자는 실제 입력 형태로 쓴다.
- raw transcript 수정본을 expected로 덮어쓰지 않는다.
- 애매한 발화는 core suite에 넣지 않는다.
- 공개하기 어려운 발화는 local-only로 둔다.

## Active Suites

- `codex-command-accuracy-v1/`: 첫 Codex 명령형 발화 정확도 suite.
