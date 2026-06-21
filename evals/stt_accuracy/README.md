# STT Accuracy Eval

Codex CLI 입력 보조 목적의 STT 정확도 평가 트랙.

이 문서가 `#9` 정확도 개선 트랙의 STT accuracy architecture contract다.

## Goal

일반 받아쓰기 정확도가 아니라 Codex CLI 입력에 필요한 정확도를 측정한다.

주요 관심사:

- 한국어 명령 인식.
- 한영 혼합 명령 인식.
- 파일명과 경로 보존.
- CLI option 보존.
- 모듈명, 함수명, 코드 식별자 보존.
- hallucination 방어.
- insertion-safe 여부.

## Folder Architecture

`stt_accuracy/`는 평가 트랙의 suite, run, report 계약만 소유한다. 공유 speech input은 `evals/inputs/speech/v1/`이 소유한다.

```text
evals/
  inputs/
    speech/
      v1/
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
    runs/
      .gitkeep
      <run_id>/
        raw/
          cmd-0001.txt
        recovered/
          cmd-0001.txt
        result.json
        metadata.json
    reports/
      README.md
      2026-06-21-governance.md
      2026-06-21-corpus-collection.md
```

## Source of Truth

- `evals/inputs/README.md`: 공유 input root contract.
- `evals/inputs/speech/v1/README.md`: speech input v1 sample contract.
- 이 문서: STT accuracy 평가 트랙 contract.
- `suites/README.md`: suite와 manifest 공통 계약.
- `suites/codex-command-accuracy-v1/README.md`: 첫 active suite 계약.
- `reports/`: 결정, baseline, closeout 요약.
- GitHub issue: 작업 순서와 진행 상태.

issue comment는 결정 로그와 handoff다. 오래 유지되는 contract는 repo 문서에 반영한다.

## Ownership Rules

- `stt_accuracy`는 WAV, expected transcript, sample metadata를 소유하지 않는다.
- 공유 speech sample은 `evals/inputs/speech/v1/samples/<sample_id>/`가 소유한다.
- suite는 `input_set`과 `sample_id`만 참조한다.
- suite는 audio, expected transcript, raw transcript 파일 경로를 직접 소유하지 않는다.
- metric list와 case selection은 suite manifest가 소유한다.
- raw transcript, recovered transcript, result summary는 `runs/<run_id>/`가 소유한다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 input version 또는 새 sample id를 만든다.

## Suite Contract

첫 active suite는 `codex-command-accuracy-v1`이다.

```text
evals/stt_accuracy/suites/codex-command-accuracy-v1/
  README.md
  manifest.schema.json
  manifest.example.json
  manifest.json
```

`manifest.json`은 `input_set: "speech/v1"`과 `sample_id`로 입력을 참조한다.

## Run Artifact Contract

실행 결과는 run id 단위로 보존한다.

```text
evals/stt_accuracy/runs/<run_id>/
  raw/
    <sample_id>.txt
  recovered/
    <sample_id>.txt
  result.json
  metadata.json
```

- `raw/`: STT 모델 출력 원문.
- `recovered/`: token recovery나 후처리 적용 결과.
- `result.json`: metric별 결과 summary.
- `metadata.json`: model, prompt, recovery policy, suite id, input set, 실행 시각 같은 run metadata.

run artifact는 local-only다. 같은 speech input을 여러 model, prompt, recovery 정책으로 반복 실행해도 이전 결과를 덮어쓰지 않는다.

## Artifact Policy

Git 추적 대상:

- `evals/stt_accuracy/**/README.md`.
- `evals/stt_accuracy/suites/**/manifest.schema.json`.
- `evals/stt_accuracy/suites/**/manifest.example.json`.
- `evals/stt_accuracy/suites/**/manifest.json`.
- `evals/stt_accuracy/reports/**`.
- `evals/stt_accuracy/runs/.gitkeep`.

Git 추적 금지:

- `evals/stt_accuracy/runs/**`의 실제 run artifact.
- raw transcript.
- recovered transcript.
- suite raw result.
- 실제 사용자 발화 audio.
- 개인 glossary.

## Fixture Policy

새 정확도 트랙에서는 top-level `fixtures/generated/`를 사용하지 않는다.

top-level `fixtures/`의 KSS, HiKE, token-recovery suite는 legacy/reference surface다. 새 active baseline으로 사용하지 않는다.

## Transcript Policy

transcript는 세 종류로 분리한다.

- `raw transcript`: STT 모델 출력 원문.
- `expected transcript`: 사용자가 원래 의도한 최종 Codex 입력문.
- `recovered transcript`: token recovery나 후처리 적용 결과.

정확도 비교의 기준은 `expected transcript`다. raw와 recovered를 섞어 성공으로 계산하지 않는다.

## Measurement Axes

정확도는 하나의 pass/fail로 판단하지 않는다.

- Korean command match.
- Latin token preservation.
- file/path token preservation.
- CLI option preservation.
- code identifier preservation.
- hallucination count.
- insertion-safe decision.

## Non-Ownership

이 문서가 소유하지 않는 일:

- 실제 audio 수집.
- 공유 input corpus versioning.
- raw transcript 작성.
- model option 실험.
- token recovery 구현.
- 기존 fixture migration.
- suite runner 구현.
