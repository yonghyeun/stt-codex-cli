# STT Accuracy Governance

## Context

이 문서는 `#9` STT 정확도 개선 트랙의 Phase 0 결정 기록이다.

Phase 0는 정확도를 직접 올리는 단계가 아니다. 정확도 실험을 어디에 기록하고, 어떤 artifact를 남기며, 어떤 기준으로 성공을 판단할지 먼저 닫는 단계다.

`#13`에서 Phase 0의 initial output tree 결정은 공유 input architecture로 재정렬됐다.

## Architecture Decision

공유 speech input과 STT accuracy 평가 트랙을 분리한다.

이유:

- 정확도 개선은 fixture만의 문제가 아니다.
- suite, metric, report, run artifact 정책이 함께 필요하다.
- `fixtures/`가 전체 평가 contract를 소유하면 책임이 과해진다.
- sample은 suite version이나 test 종류가 아니라 shared input corpus가 소유해야 한다.
- 같은 speech sample은 여러 eval track에서 재사용될 수 있어야 한다.
- run artifact는 model, prompt, recovery policy별로 달라지므로 run id 아래에 보존해야 한다.

## Folder Contract

```text
evals/
  inputs/
    speech/
      v1/
        README.md
        manifest.schema.json
        manifest.json
        sample.schema.json
        samples/
          cmd-0001/
            audio.wav
            expected.txt
            metadata.json
  stt_accuracy/
    README.md
    suites/
      README.md
      codex-command-accuracy-v1/
        README.md
        manifest.schema.json
        manifest.example.json
        manifest.json
    reports/
      README.md
      2026-06-21-governance.md
      2026-06-21-corpus-collection.md
    runs/
      <run_id>/
        raw/
        recovered/
        result.json
        metadata.json
```

## Source of Truth

- `evals/inputs/README.md`: shared input root contract.
- `evals/inputs/speech/v1/README.md`: speech input v1 contract.
- `evals/stt_accuracy/README.md`: 정확도 평가 트랙 contract.
- `evals/stt_accuracy/suites/README.md`: suite와 manifest contract.
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/README.md`: 첫 active suite contract.
- `evals/stt_accuracy/reports/`: local evidence와 결정 요약.
- `fixtures/README.md`: legacy/reference fixture 경계.
- GitHub issue: 진행 상태, sequencing, handoff projection.

## Artifact Ownership

| 위치 | 책임 | Git 추적 |
| --- | --- | --- |
| `evals/inputs/**/README.md` | input contract | 가능 |
| `evals/inputs/speech/v1/manifest.schema.json` | input manifest schema | 가능 |
| `evals/inputs/speech/v1/manifest.json` | input sample inventory | 가능 |
| `evals/inputs/speech/v1/sample.schema.json` | sample metadata schema | 가능 |
| `evals/inputs/speech/v1/samples/**/expected.txt` | 공개 가능한 expected transcript | 가능 |
| `evals/inputs/speech/v1/samples/**/metadata.json` | 공개 가능한 sample metadata | 가능 |
| `evals/inputs/speech/v1/samples/**/audio.wav` | 실제 사용자 음성 | 금지 |
| `evals/stt_accuracy/suites/**` | suite 정의와 manifest | 가능 |
| `evals/stt_accuracy/reports/**` | 요약 report와 결정 기록 | 가능 |
| `evals/stt_accuracy/runs/**` | suite 실행 결과 | 금지 |
| `fixtures/**` | legacy/reference fixture | 가능 |
| `fixtures/generated/**` | 기존 legacy 생성물 | 금지 |
| `memory/*.local.json` | 개인 token memory | 금지 |

## Ownership Rules

- WAV는 suite가 소유하지 않는다.
- expected transcript는 shared input sample이 소유한다.
- sample metadata는 shared input sample이 소유한다.
- raw transcript는 suite가 소유하지 않는다.
- sample data는 `evals/inputs/speech/v1/samples/<sample_id>/`가 소유한다.
- suite는 `input_set`과 `sample_id`만 참조한다.
- v1, v2 suite가 같은 sample을 써도 sample은 한 번만 존재한다.
- suite version 간에는 파일 경로 의존성을 만들지 않는다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 input version 또는 새 sample id를 만든다.

## Active Suite

새 정확도 트랙의 첫 active suite는 `codex-command-accuracy-v1`이다.

이 suite가 생성되기 전까지 새 정확도 트랙의 active baseline은 없다.

기존 KSS, HiKE, token-recovery fixture는 active baseline이 아니다. 기존 fixture는 historical reference 또는 runner smoke 용도로만 사용한다.

## Local Closeout Questions

이 결정이 끝나면 아래 질문에 답할 수 있어야 한다.

- shared input root는 어디인가.
- speech input v1의 sample 구조는 무엇인가.
- STT accuracy track은 무엇을 소유하는가.
- 각 README는 어떤 contract를 소유하는가.
- 무엇을 Git에 남기는가.
- 무엇을 local-only로 두는가.
- 기존 fixture는 어떤 지위를 가지는가.
- 새 active suite 이름은 무엇인가.
- sample은 누가 소유하는가.
- suite는 sample을 어떻게 참조하는가.
- run artifact는 어디에 보존되는가.

## Remote Projection Boundary

이 report는 다음 작업 queue를 소유하지 않는다.

다음 phase, leaf 순서, handoff, closeout receipt는 GitHub issue graph와 issue comment가 소유한다. local 문서는 remote 상태 없이도 eval architecture를 이해할 수 있어야 한다.
