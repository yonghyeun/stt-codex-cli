# Speech Input v1

Codex CLI 입력 보조 평가에서 재사용할 첫 speech input corpus.

이 input version은 특정 test 종류나 suite가 아니라 공유 speech sample snapshot을 소유한다. `stt_accuracy` 같은 평가 트랙은 `speech/v1`과 `sample_id`를 참조한다.

## Version Contract

`speech/v1`은 한글 음가 transcript 평가 세트다.

v1에서는 STT가 개발 literal을 보존하거나 복원하지 않아도 된다. 사용자가 실제로 말한 소리를 한글 음가로 안정적으로 적는지 먼저 본다.

예시:

- `v1`: `브이원`
- `Ctrl+T`: `컨트롤 티`
- `README.md`: `리드미 엠디`
- `--dry-run`: `드라이런`
- `stt_runtime`: `에스티티 런타임`

literal mapping, ranking, token recovery, command normalization은 v2 이후 평가 축이 소유한다.

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
- `expected.txt`: v1에서 기대하는 STT transcript. 한글 음가 기준이며 공개 가능하면 Git에 추적한다.
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
`speech/v1`의 기본 정책은 `korean_phonetic_transcript`다.

이전 정책값인 `codex_final_input`과 `actual_spoken_phrase`는 과거 수집 맥락을 설명할 수는 있지만, 새 v1 sample의 통과 기준으로 쓰지 않는다.

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
- `speech/v1`은 한글 음가 transcript contract 안에서 재사용한다.
- 새 발화 의도나 새 audio가 필요하면 `speech/v2` 또는 새 `sample_id`를 만든다.
- v1 contract 재정렬 이후에는 기존 sample의 의미를 다시 final literal 입력문으로 바꾸지 않는다.

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
