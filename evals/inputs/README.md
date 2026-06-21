# Eval Inputs

여러 eval track이 재사용하는 입력 데이터 위치.

`evals/inputs/`는 특정 test 종류, suite, run에 종속되지 않는 input corpus를 소유한다. 평가 트랙은 여기 있는 input version을 참조만 한다.

## Ownership

- input modality별 versioned corpus.
- input version README.
- input manifest와 schema.
- 공개 가능한 sample source.
- local-only 실제 media 파일의 경로 계약.

## Non-Ownership

- suite case selection.
- metric 정의.
- model option.
- raw STT transcript.
- recovered transcript.
- result summary.
- run metadata.

위 산출물은 각 평가 트랙의 `suites/`, `runs/`, `reports/`가 소유한다.

## Rules

- input은 `evals/inputs/<modality>/<version>/` 아래에 둔다.
- sample은 `samples/<sample_id>/` 폴더 단위로 둔다.
- test 종류 아래에 input file을 두지 않는다.
- suite는 input file path를 직접 소유하지 않고 input version과 sample id를 참조한다.
- run은 input을 수정하지 않고 실행 산출물만 기록한다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 input version 또는 새 sample id를 만든다.

## Current Inputs

- `speech/v1/`: Codex CLI 입력 보조 평가를 위한 첫 speech sample snapshot.
