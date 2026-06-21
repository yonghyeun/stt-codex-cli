# codex-command-accuracy-v1

`#9` 정확도 개선 트랙의 첫 active baseline suite.

## Goal

실제 Codex CLI 입력 보조에 가까운 사용자 발화를 수집해 STT 정확도를 측정한다.

## Categories

- 순수 한국어 명령.
- 한영 혼합 명령.
- 파일명과 경로 포함 명령.
- CLI option 포함 명령.
- 모듈명, 함수명, 식별자 포함 명령.
- 긴 설명형 발화.

## Minimum Set

- 최소 20개 발화.
- 각 category가 최소 2개 이상 포함되어야 한다.
- 실제 사용자 발화에서 출발한다.

## Example Prompts

- `README 수정해`
- `scripts/transcribe.py 열어줘`
- `--save-run 옵션 추가해`
- `stt_runtime recording 쪽 테스트 봐줘`
- `이 변경사항 커밋해줘`

## Artifact Paths

공개 가능한 suite contract:

- `evals/stt_accuracy/suites/codex-command-accuracy-v1/README.md`
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.schema.json`
- `evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.example.json`

Tracked collected source:

- `evals/stt_accuracy/output/corpus/<sample_id>/`
- `evals/stt_accuracy/output/suites/codex-command-accuracy-v1/manifest.local.json`

Local-only execution artifact:

- `evals/stt_accuracy/output/corpus/<sample_id>/audio.wav`
- `evals/stt_accuracy/output/runs/<run_id>/`

## Manifest Rule

`manifest.local.json`은 실제 sample id를 참조한다.

suite는 WAV, expected transcript, raw transcript를 소유하지 않는다. 해당 파일들은 `evals/stt_accuracy/output/corpus/<sample_id>/`가 소유한다.

`audio.wav`는 local-only다. `expected.txt`, `metadata.json`, `manifest.local.json`은 공개 가능한 baseline source로 Git에 추적한다.

sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 sample id를 만든다.

## Baseline Rule

이 suite가 생성되기 전까지 새 정확도 트랙의 active baseline은 없다.

기존 KSS, HiKE, token-recovery fixture는 이 suite를 대체하지 않는다.
