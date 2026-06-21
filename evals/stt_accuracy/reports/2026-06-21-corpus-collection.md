# STT Accuracy Corpus Collection

## Context

이 문서는 `#9` STT 정확도 개선 트랙의 Phase 1 수집 요약이다.

실제 sample artifact는 local-only다. 이 report는 Git에 남길 수 있는 익명화된 evidence만 기록한다.

## Collection Summary

- Suite: `codex-command-accuracy-v1`
- Source issue: `#12`
- Sample count: 24
- Audio files: 24
- Manifest cases: 24
- Raw STT output: not generated in this phase
- Run artifact owner for raw output: `evals/stt_accuracy/output/runs/<run_id>/`

## Category Coverage

| Category | Count |
| --- | ---: |
| `korean_command` | 4 |
| `code_switch` | 4 |
| `file_path` | 4 |
| `cli_option` | 4 |
| `code_identifier` | 4 |
| `long_form` | 4 |

## Local Artifact Layout

각 sample은 local-only로 아래 파일을 가진다.

```text
evals/stt_accuracy/output/corpus/<sample_id>/
  audio.wav
  expected.txt
  metadata.json
```

Local suite manifest:

```text
evals/stt_accuracy/output/suites/codex-command-accuracy-v1/manifest.local.json
```

`corpus/<sample_id>/raw.txt`는 사용하지 않는다. 같은 audio를 여러 model, prompt, recovery 정책으로 반복 실행해야 하므로 raw STT output은 실행별 run artifact로 둔다.

## Validation

Executed checks:

```text
find evals/stt_accuracy/output/corpus -mindepth 2 -maxdepth 2 -name audio.wav | sort | wc -l
python3 -m json.tool evals/stt_accuracy/output/suites/codex-command-accuracy-v1/manifest.local.json
jsonschema validation against evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.schema.json
ffprobe duration check for every audio.wav
git check-ignore for audio, expected transcript, metadata, and manifest.local.json
```

Results:

- Audio count: 24/24
- WAV readability: 24/24 passed
- Manifest JSON: passed
- Manifest schema: passed
- Required local source files: passed
- Ignored artifact check: passed
- `raw.txt` placeholder count: 0

Duration summary:

- Total duration: 147.24 seconds
- Average duration: 6.14 seconds
- Shortest sample: `cmd-0005`, 2.77 seconds
- Longest sample: `cmd-0014`, 15.49 seconds

## Privacy

Git-tracked report는 실제 발화 원문, 음성 파일, local manifest 내용을 포함하지 않는다.

Git 추적 금지 대상:

- `evals/stt_accuracy/output/corpus/**/audio.wav`
- `evals/stt_accuracy/output/corpus/**/expected.txt`
- `evals/stt_accuracy/output/corpus/**/metadata.json`
- `evals/stt_accuracy/output/suites/**/manifest.local.json`
- `evals/stt_accuracy/output/runs/**`

## Phase 2 Input

Phase 2는 이 corpus와 local manifest를 입력으로 사용한다.

Baseline raw STT output은 sample folder가 아니라 실행별 run folder에 저장한다.

예상 구조:

```text
evals/stt_accuracy/output/runs/<run_id>/
  raw/
    cmd-0001.txt
  result.json
  metadata.json
```

## Notes

- 기존 KSS, HiKE, token-recovery fixture는 이 corpus의 active baseline을 대체하지 않는다.
- `cmd-0005`는 가장 짧은 sample이지만 WAV 파일은 정상이다.
- `#13`에서 raw output ownership과 run artifact contract를 문서 수준으로 재정렬한다.
