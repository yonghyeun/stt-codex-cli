# Evals

평가 트랙의 계약, suite 정의, report 위치.

`evals/`는 반복 실행 가능한 평가 작업의 source tree다. 단순 실험 기록은 `experiments/`에 둘 수 있지만, baseline, suite, metric, report처럼 후속 작업이 계속 소비하는 표면은 `evals/`에 둔다.

## Ownership

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
- 다음 작업 queue.
- remote handoff projection.

local artifact는 각 eval track의 `output/` 또는 `memory/*.local.json`에 둔다. 다음 작업 queue와 handoff projection은 GitHub issue graph가 소유한다.

## Tracks

- `stt_accuracy/`: Codex CLI 입력 보조 목적의 STT 정확도 평가 트랙.
