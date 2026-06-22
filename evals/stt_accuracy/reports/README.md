# STT Accuracy Reports

정확도 평가 report 위치.

## Ownership

- governance report.
- baseline report.
- option experiment report.
- token recovery evaluation report.
- closeout evidence summary.

## Rule

report는 local evidence와 결정 근거를 남긴다.

raw output을 그대로 붙이지 않는다. 재현 명령, 요약 지표, 관찰, 결정만 남긴다.

민감한 발화나 개인 audio 정보는 report에 직접 쓰지 않는다.

## Baseline Report Contract

Baseline report는 다음 항목을 남긴다.

- 실행한 canonical command.
- `run_id`.
- suite id와 input set.
- model config.
- 전체 case 수와 실패 case 수.
- category별 요약.
- failure taxonomy별 요약.
- quality summary.
- 대표 mismatch 관찰. 단, raw transcript 전체 덤프는 제외.
- 후속 실험 판단.

baseline report는 `evals/stt_accuracy/runs/<run_id>/result.json`을 요약한다.
`result.json`의 case별 `text_comparison`과 `quality`는 local inspection source다.
run artifact 자체는 Git에 추적하지 않는다.

## Non-Ownership

- 작업 queue.
- sequencing.
- 외부 전달 상태.
- closeout receipt.

위 항목은 report가 소유하지 않는다. report는 local evidence와 결정 근거만으로 완결되어야 한다.
