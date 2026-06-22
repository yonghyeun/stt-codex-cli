# Evals

평가 입력 데이터와 평가 트랙의 계약, suite 정의, report 위치.

`evals/`는 반복 실행 가능한 평가 작업의 source tree다. 단순 실험 기록은 `experiments/`에 둘 수 있지만, baseline, suite, metric, report처럼 후속 작업이 계속 소비하는 표면은 `evals/`에 둔다.

## Ownership

- 여러 평가 트랙이 재사용할 수 있는 versioned input corpus.
- 평가 트랙별 canonical contract.
- 공개 가능한 suite manifest와 schema 설명.
- metric 정의.
- report와 결정 요약.

## Non-Ownership

- 실제 사용자 발화 audio.
- raw STT transcript.
- raw suite output.
- 개인 token memory.
- 일회성 실험 메모.
- 작업 queue.
- 외부 전달 상태.

local artifact는 각 eval track의 `runs/` 또는 `memory/*.local.json`에 둔다. `evals/` 아래 계약과 report는 local file state만으로 해석 가능해야 하며, 작업 순서나 외부 진행 상태에 의존하지 않는다.

## Inputs

- `inputs/`: 특정 평가 트랙에 종속되지 않는 공유 입력 데이터.
- `inputs/speech/v1/`: 첫 speech input corpus snapshot.

입력 데이터는 test 종류, suite version, run id 아래에 두지 않는다. 같은 speech sample은 STT accuracy, token recovery, model option eval 같은 여러 평가 트랙에서 재사용할 수 있어야 한다.

## Tracks

- `stt_accuracy/`: Codex CLI 입력 보조 목적의 STT 정확도 평가 트랙.
