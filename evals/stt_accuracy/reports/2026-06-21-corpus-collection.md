# STT Accuracy Corpus Collection

## Context

이 문서는 STT accuracy evaluation용 speech input collection 요약이다.

실제 audio는 local-only다. expected transcript, metadata, input manifest, suite manifest는 공개 가능한 baseline source로 Git에 추적한다.

## Collection Summary

- Input set: `speech/v1`
- Suite: `codex-command-accuracy-v1`
- Sample count: 24
- Audio files: 24
- Manifest cases: 24
- Raw STT output: not generated in this collection run
- Run artifact owner for raw output: `evals/stt_accuracy/runs/<run_id>/`
- Ignored input files: `audio.wav` only

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

각 sample은 shared input 아래에 아래 source 파일을 가진다.

```text
evals/inputs/speech/v1/samples/<sample_id>/
  audio.wav
  expected.txt
  metadata.json
```

Input manifest:

```text
evals/inputs/speech/v1/manifest.json
```

STT accuracy suite manifest:

```text
evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.json
```

sample folder에는 raw transcript를 두지 않는다. 같은 audio를 여러 model, prompt, recovery 정책으로 반복 실행해야 하므로 raw STT output은 실행별 run artifact로 둔다.

`audio.wav`만 local-only로 두고, `expected.txt`, `metadata.json`, input manifest, suite manifest는 Git에 추적한다.

## Validation

Executed checks:

```text
find evals/inputs/speech/v1/samples -mindepth 2 -maxdepth 2 -name audio.wav | sort | wc -l
python3 -m json.tool evals/inputs/speech/v1/manifest.json
python3 -m json.tool evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.json
jsonschema validation against evals/inputs/speech/v1/sample.schema.json
jsonschema validation against evals/inputs/speech/v1/manifest.schema.json
jsonschema validation against evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.schema.json
ffprobe duration check for every audio.wav
git check-ignore for audio
git check-ignore negative check for expected transcript, metadata, and manifests
```

Results:

- Audio count: 24/24
- WAV readability: 24/24 passed
- Input manifest JSON: passed
- Suite manifest JSON: passed
- Manifest schema: passed
- Required local source files: passed
- Ignored audio check: passed
- Tracked text source check: passed
- `raw.txt` placeholder count: 0

Duration summary:

- Total duration: 147.24 seconds
- Average duration: 6.14 seconds
- Shortest sample: `cmd-0005`, 2.77 seconds
- Longest sample: `cmd-0014`, 15.49 seconds

## Privacy

Git-tracked source는 실제 음성 파일을 포함하지 않는다.

Git 추적 금지 대상:

- `evals/inputs/speech/v1/samples/**/audio.wav`
- `evals/stt_accuracy/runs/**`

Git 추적 대상:

- `evals/inputs/speech/v1/samples/**/expected.txt`
- `evals/inputs/speech/v1/samples/**/metadata.json`
- `evals/inputs/speech/v1/manifest.json`
- `evals/stt_accuracy/suites/**/manifest.json`

## Baseline Input

Baseline은 `speech/v1` input set과 `codex-command-accuracy-v1` suite manifest를 입력으로 사용한다.

Baseline raw STT output은 sample folder가 아니라 실행별 run folder에 저장한다.

예상 구조:

```text
evals/stt_accuracy/runs/<run_id>/
  raw/
    cmd-0001.txt
  recovered/
    cmd-0001.txt
  result.json
  metadata.json
```

## Notes

- 기존 KSS, HiKE, token-recovery fixture는 이 corpus의 active baseline을 대체하지 않는다.
- `cmd-0005`는 가장 짧은 sample이지만 WAV 파일은 정상이다.
- shared input ownership과 run artifact contract는 repo 문서와 manifest가 소유한다.
