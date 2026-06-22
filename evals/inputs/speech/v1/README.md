# Speech Input v1

Codex CLI 입력 보조 평가에서 재사용할 첫 speech input corpus.

이 input version은 특정 test 종류나 suite가 아니라 공유 speech sample snapshot을 소유한다. `stt_accuracy` 같은 평가 트랙은 `speech/v1`과 `sample_id`를 참조한다.

## Structure

```text
evals/
  inputs/
    speech/
      v1/
        README.md
        manifest.schema.json
        manifest.json
        sample.schema.json
        samples/
          cmd-0001/
            audio.wav
            expected.txt
            metadata.json
```

## Sample Contract

각 sample은 폴더 단위로 응집한다.

```text
evals/inputs/speech/v1/samples/<sample_id>/
  audio.wav
  expected.txt
  metadata.json
```

- `audio.wav`: 실제 사용자 발화 audio. local-only이며 Git에 추적하지 않는다.
- `expected.txt`: 사용자가 Codex CLI에 넣고 싶었던 최종 입력문. 공개 가능하면 Git에 추적한다.
- `metadata.json`: sample 자체의 공개 가능한 metadata. 공개 가능하면 Git에 추적한다.

## Metadata Boundary

`metadata.json`은 input sample 자체의 속성만 가진다.

포함:

- `sample_id`
- `prompt_id`
- `category`
- `recording_status`
- `expected_text_policy`
- `rerecord_reason`

포함하지 않음:

- metric list.
- raw transcript.
- recovered transcript.
- transcription status.
- model option.
- run id.
- result summary.

`expected_text_policy`는 `expected.txt`가 어떤 기준의 text인지 설명한다.
기본 정책은 Codex 입력창 최종문인 `codex_final_input`이다. 실제 발화 그대로를
평가해야 하는 재녹음 sample은 `actual_spoken_phrase`를 사용할 수 있다.

metric과 case selection은 평가 트랙의 suite manifest가 소유한다. transcription status와 실행 결과는 평가 트랙의 `runs/<run_id>/`가 소유한다.

## Manifest Contract

`manifest.json`은 `speech/v1`에 포함된 sample id 목록을 소유한다. sample file path나 평가 metric을 직접 소유하지 않는다.

```json
{
  "input_set": "speech/v1",
  "version": 1,
  "sample_ids": ["cmd-0001"]
}
```

## Reuse Rule

- 여러 suite가 같은 `sample_id`를 참조할 수 있다.
- 여러 eval track이 같은 `speech/v1` sample을 참조할 수 있다.
- `speech/v1` sample 내용을 수정하지 않는다.
- sample 내용 변경이 필요하면 `speech/v2` 또는 새 `sample_id`를 만든다.

## Artifact Policy

Git 추적 대상:

- `README.md`.
- `manifest.schema.json`.
- `manifest.json`.
- `sample.schema.json`.
- `samples/**/expected.txt`.
- `samples/**/metadata.json`.

Git 추적 금지:

- `samples/**/audio.wav`.
- raw transcript.
- recovered transcript.
- run result.
