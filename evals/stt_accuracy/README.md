# STT Accuracy Eval

Codex CLI 입력 보조 목적의 STT 정확도 평가 트랙.

이 문서가 `#9` 정확도 개선 트랙의 평가 architecture contract다.

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

정확도 평가 트랙은 `evals/stt_accuracy/` 안에서 source contract와 local artifact를 함께 소유한다.

- `evals/stt_accuracy/`는 평가 source tree다.
- `evals/stt_accuracy/output/`는 평가 sample source와 실행 결과를 담는 artifact tree다.
- `evals/stt_accuracy/output/corpus/**/audio.wav`와 `evals/stt_accuracy/output/runs/**`는 local-only다.
- `expected.txt`, `metadata.json`, `manifest.local.json`은 공개 가능한 baseline 계약이면 Git에 추적한다.
- `fixtures/`는 기존 KSS/HiKE/token-recovery 같은 legacy/reference fixture 위치다.
- 새 정확도 트랙의 active baseline은 `fixtures/`가 아니라 `evals/stt_accuracy/` contract와 `evals/stt_accuracy/output/` local data 조합으로 관리한다.

## Source Contract

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
```

`evals/stt_accuracy/README.md`는 정확도 평가 트랙의 canonical contract다.

`suites/`는 suite contract, manifest schema, example manifest를 소유한다. 실제 수집된 suite case manifest는 `evals/stt_accuracy/output/suites/<suite_id>/manifest.local.json`에 둔다.

## Local Artifact Contract

```text
evals/
  stt_accuracy/
    output/
      corpus/
        cmd-0001/
          audio.wav
          expected.txt
          metadata.json
        cmd-0002/
          audio.wav
          expected.txt
          metadata.json
      suites/
        codex-command-accuracy-v1/
          manifest.local.json
      runs/
        20260621-120000-large-v3-cuda-float16/
          result.json
          metadata.json
```

`corpus/`는 실제 평가 sample 저장소다. sample은 폴더 단위로 응집한다.

```text
evals/stt_accuracy/output/corpus/<sample_id>/
  audio.wav
  expected.txt
  metadata.json
```

sample folder는 flat하게 나열한다. suite version 아래에 audio를 넣지 않는다.

금지 구조:

```text
evals/stt_accuracy/output/codex-command-accuracy-v1/audio.wav
evals/stt_accuracy/output/codex-command-accuracy-v2/audio.wav
```

이 구조는 suite version별 WAV 중복과 version 간 의존성을 만든다.

## Source of Truth

- 이 문서: 정확도 평가 트랙의 최상위 contract.
- `suites/README.md`: suite와 manifest 계약.
- `suites/codex-command-accuracy-v1/README.md`: 첫 active suite 계약.
- `reports/`: 결정, baseline, closeout 요약.
- GitHub issue: 작업 순서와 진행 상태.

issue comment는 결정 로그와 handoff다. 오래 유지되는 contract는 repo 문서에 반영한다.

## Ownership Rules

- WAV는 suite가 소유하지 않는다.
- expected transcript는 corpus sample source가 소유한다.
- sample metadata는 corpus sample source가 소유한다.
- raw transcript도 suite가 소유하지 않는다.
- sample data는 `evals/stt_accuracy/output/corpus/<sample_id>/`가 소유한다.
- suite는 `sample_id`만 참조한다.
- v1, v2 suite가 같은 sample을 써도 sample은 한 번만 존재한다.
- suite version 간에는 파일 경로 의존성을 만들지 않는다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 sample id를 만든다.

## Artifact Policy

Git 추적 대상:

- `evals/stt_accuracy/**/README.md`.
- `manifest.schema.json`.
- `manifest.example.json`.
- `evals/stt_accuracy/output/corpus/**/expected.txt`.
- `evals/stt_accuracy/output/corpus/**/metadata.json`.
- `evals/stt_accuracy/output/suites/**/manifest.local.json`.
- 익명화된 report summary.
- metric 정의.

Git 추적 금지:

- `evals/stt_accuracy/output/corpus/**/audio.wav`.
- `evals/stt_accuracy/output/runs/**`.
- 실제 사용자 발화 audio.
- raw transcript.
- recovered transcript.
- 개인 glossary.

## Fixture Policy

새 정확도 트랙에서는 top-level `fixtures/generated/`를 사용하지 않는다.

평가 입력 계약은 `evals/stt_accuracy/suites/**`와 `evals/stt_accuracy/output/suites/**/manifest.local.json`가 소유한다. 실행 중 생성되는 raw/recovered/result는 `evals/stt_accuracy/output/runs/**`에 둔다.

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

## Scaffold State

이 폴더 구조는 평가 contract와 local artifact tree를 함께 제공한다.

이 문서가 소유하지 않는 일:

- 실제 audio 수집.
- raw transcript 작성.
- model option 실험.
- token recovery 구현.
- 기존 fixture migration.
- suite runner 구현.

## Corpus Collection Contract

실제 sample 수집은 `evals/stt_accuracy/output/corpus/`에 저장하고, suite manifest는 `evals/stt_accuracy/output/suites/<suite_id>/manifest.local.json`에서 sample id만 참조한다.

- suite 이름: `codex-command-accuracy-v1`.
- 최소 발화 수: 20개.
- 실제 Codex 명령형 발화만 포함.
- sample은 `evals/stt_accuracy/output/corpus/`에 저장.
- suite manifest는 sample id만 참조.
- audio는 local-only로 둔다.
- expected transcript와 metadata는 공개 가능한 baseline source로 Git에 추적한다.
- 민감 발화는 local-only 또는 익명화.
- 기존 KSS/HiKE/token-recovery fixture는 active baseline으로 재사용하지 않음.
