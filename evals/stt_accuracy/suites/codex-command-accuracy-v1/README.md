# codex-command-accuracy-v1

Codex 명령형 발화 정확도 평가의 첫 active baseline suite.

## Goal

실제 Codex CLI 입력 보조에 가까운 사용자 발화를 선택해 STT 정확도를 측정한다.

이 suite의 v1 통과 기준은 최종 Codex literal 복원이 아니라 한글 음가 transcript match다.

## Input Set

- `input_set`: `speech/v1`
- input owner: `evals/inputs/speech/v1/`
- sample owner: `evals/inputs/speech/v1/samples/<sample_id>/`

suite는 input을 복사하지 않는다. `manifest.json`에서 `input_set`과 `sample_id`만 참조한다.

## Categories

- 순수 한국어 명령.
- 한영 혼합 발화.
- 파일명과 경로를 읽은 발화.
- CLI option을 읽은 발화.
- 모듈명, 함수명, 식별자를 읽은 발화.
- 긴 설명형 발화.

## Minimum Set

- 최소 20개 발화.
- 각 category가 최소 2개 이상 포함되어야 한다.
- 실제 사용자 발화에서 출발한다.
- v1 `expected.txt`는 한글 음가 transcript로 쓴다.

## Example Prompts

- `README 수정해`
- `스크립츠 트랜스크라이브 파이 열어줘`
- `세이브런 옵션 추가해`
- `에스티티 런타임 레코딩 쪽 테스트 봐줘`
- `이 변경사항 커밋해줘`

## Artifact Paths

공개 가능한 suite contract:

- `evals/stt_accuracy/suites/codex-command-accuracy-v1/README.md`
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.schema.json`
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.example.json`
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.json`

공유 input source:

- `evals/inputs/speech/v1/manifest.json`
- `evals/inputs/speech/v1/samples/<sample_id>/expected.txt`
- `evals/inputs/speech/v1/samples/<sample_id>/metadata.json`

Local-only artifact:

- `evals/inputs/speech/v1/samples/<sample_id>/audio.wav`
- `evals/stt_accuracy/runs/<run_id>/`

## Manifest Rule

`manifest.json`은 실제 sample id를 참조한다.

suite는 WAV, expected transcript, sample metadata, raw transcript를 소유하지 않는다.

`audio.wav`는 local-only다. `expected.txt`, `metadata.json`, `manifest.json`은 공개 가능한 source로 Git에 추적한다.

sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 input version 또는 새 sample id를 만든다.

단, `speech/v1`의 expected 정책은 한글 음가 transcript로 고정한다. literal 복원 평가는 이 suite의 v1 통과 기준이 아니다.

## Baseline Rule

이 suite가 생성되기 전까지 새 정확도 트랙의 active baseline은 없다.

기존 KSS, HiKE, token-recovery fixture는 이 suite를 대체하지 않는다.
