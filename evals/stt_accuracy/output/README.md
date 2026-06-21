# STT Accuracy Output

정확도 평가 트랙의 local-only 실행 산출물 위치.

`evals/stt_accuracy/output/` 아래에서 README와 `.gitkeep`만 Git에 추적한다. 실제 sample과 실행 결과는 Git에 올리지 않는다.

## Ownership

- 실제 사용자 발화 audio.
- expected transcript.
- raw STT transcript.
- recovered transcript.
- suite raw result.
- local-only manifest.
- sample metadata.

## Structure

```text
evals/
  stt_accuracy/
    output/
      corpus/
        .gitkeep
        cmd-0001/
          audio.wav
          expected.txt
          raw.txt
          metadata.json
        cmd-0002/
          audio.wav
          expected.txt
          raw.txt
          metadata.json
      suites/
        codex-command-accuracy-v1/
          .gitkeep
          manifest.local.json
      runs/
        .gitkeep
        20260621-120000-large-v3-cuda-float16/
          result.json
          metadata.json
```

기본 scaffold로 아래 폴더는 Git에 유지한다.

- `evals/stt_accuracy/output/corpus/`
- `evals/stt_accuracy/output/suites/codex-command-accuracy-v1/`
- `evals/stt_accuracy/output/runs/`

## Sample Folder Rule

sample은 flat하게 나열한다.

```text
evals/stt_accuracy/output/corpus/<sample_id>/
  audio.wav
  expected.txt
  raw.txt
  metadata.json
```

suite version 아래에 audio를 넣지 않는다.

금지 구조:

```text
evals/stt_accuracy/output/codex-command-accuracy-v1/audio.wav
evals/stt_accuracy/output/codex-command-accuracy-v2/audio.wav
```

이 구조는 suite version별 WAV 중복과 version 간 의존성을 만든다.

## Ownership Rules

- sample data는 `corpus/<sample_id>/`가 소유한다.
- suite는 `sample_id`만 참조한다.
- v1, v2 suite가 같은 sample을 써도 sample은 한 번만 존재한다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 sample id를 만든다.
