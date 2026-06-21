# STT Accuracy Governance

## Context

이 문서는 `#9` STT 정확도 개선 트랙의 Phase 0 산출물이다.

Phase 0는 정확도를 직접 올리는 단계가 아니다. 정확도 실험을 어디에 기록하고, 어떤 artifact를 남기며, 어떤 기준으로 성공을 판단할지 먼저 닫는 단계다.

## Architecture Decision

정확도 평가 트랙은 `evals/stt_accuracy/` 안에서 source contract와 local artifact를 함께 소유한다.

이유:

- 정확도 개선은 fixture만의 문제가 아니다.
- suite, metric, report, local artifact 정책이 함께 필요하다.
- `fixtures/`가 전체 평가 contract를 소유하면 책임이 과해진다.
- sample은 suite version이 아니라 corpus가 소유해야 한다.
- 새 generated artifact는 `fixtures/generated/`가 아니라 `evals/stt_accuracy/output/**`에 둔다.

## Folder Contract

```text
evals/
  stt_accuracy/
    README.md
    suites/
      README.md
      codex-command-accuracy-v1/
        README.md
        manifest.schema.json
        manifest.example.json
    reports/
      README.md
      2026-06-21-governance.md
    output/
      README.md
      corpus/
        cmd-0001/
          audio.wav
          expected.txt
          raw.txt
          metadata.json
      suites/
        codex-command-accuracy-v1/
          manifest.local.json
      runs/
        20260621-120000-large-v3-cuda-float16/
          result.json
          metadata.json
```

## Source of Truth

- `evals/stt_accuracy/README.md`: 정확도 평가 트랙 contract.
- `evals/stt_accuracy/suites/README.md`: suite와 manifest contract.
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/README.md`: 첫 active suite contract.
- `evals/stt_accuracy/reports/`: local evidence와 결정 요약.
- `evals/stt_accuracy/output/README.md`: local-only artifact tree contract.
- `fixtures/README.md`: legacy/reference fixture 경계.
- GitHub issue: 진행 상태, sequencing, handoff projection.

## Artifact Ownership

| 위치 | 책임 | Git 추적 |
| --- | --- | --- |
| `evals/stt_accuracy/` | 정확도 평가 contract, suite, report | 가능 |
| `evals/stt_accuracy/suites/**` | 공개 가능한 suite 정의와 manifest schema/example | 가능 |
| `evals/stt_accuracy/reports/**` | 요약 report와 결정 기록 | 가능 |
| `fixtures/**` | legacy/reference fixture | 가능 |
| `fixtures/generated/**` | 기존 legacy 생성물 | 금지 |
| `evals/stt_accuracy/output/corpus/**` | 실제 sample audio/transcript/metadata | 금지 |
| `evals/stt_accuracy/output/suites/**/manifest.local.json` | 실제 sample id를 참조하는 local manifest | 금지 |
| `evals/stt_accuracy/output/runs/**` | suite 실행 결과 | 금지 |
| `output/runs/**` | wrapper run artifact | 금지 |
| `memory/*.local.json` | 개인 token memory | 금지 |

## Ownership Rules

- WAV는 suite가 소유하지 않는다.
- expected transcript도 suite가 소유하지 않는다.
- raw transcript도 suite가 소유하지 않는다.
- sample data는 `evals/stt_accuracy/output/corpus/<sample_id>/`가 소유한다.
- suite는 `sample_id`만 참조한다.
- v1, v2 suite가 같은 sample을 써도 sample은 한 번만 존재한다.
- suite version 간에는 파일 경로 의존성을 만들지 않는다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 sample id를 만든다.

## Active Suite

새 정확도 트랙의 첫 active suite는 `codex-command-accuracy-v1`이다.

이 suite가 생성되기 전까지 새 정확도 트랙의 active baseline은 없다.

기존 KSS, HiKE, token-recovery fixture는 active baseline이 아니다. 기존 fixture는 historical reference 또는 runner smoke 용도로만 사용한다.

## Local Closeout Questions

Phase 0가 끝나면 아래 질문에 답할 수 있어야 한다.

- 정확도 트랙의 폴더 구조는 어디인가.
- 각 README는 어떤 contract를 소유하는가.
- 무엇을 Git에 남기는가.
- 무엇을 local-only로 두는가.
- 기존 fixture는 어떤 지위를 가지는가.
- 새 active suite 이름은 무엇인가.
- sample은 누가 소유하는가.
- suite는 sample을 어떻게 참조하는가.
- output과 suite contract는 어떻게 분리되는가.

## Remote Projection Boundary

이 report는 다음 작업 queue를 소유하지 않는다.

다음 phase, leaf 순서, handoff, closeout receipt는 GitHub issue graph와 issue comment가 소유한다. local 문서는 remote 상태 없이도 eval architecture를 이해할 수 있어야 한다.
