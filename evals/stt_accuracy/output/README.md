# STT Accuracy Output

정확도 평가 트랙의 sample source와 실행 산출물 위치.

`evals/stt_accuracy/output/` 아래에서 공개 가능한 text source는 Git에 추적한다. 실제 음성 파일과 실행 결과는 Git에 올리지 않는다.

## Ownership

Git 추적 대상:

- expected transcript.
- sample metadata.
- `manifest.local.json`.

Git 추적 금지 대상:

- 실제 사용자 발화 audio.
- raw STT transcript.
- recovered transcript.
- suite raw result.

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
          metadata.json
        cmd-0002/
          audio.wav
          expected.txt
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
- `audio.wav`는 local-only다.
- `expected.txt`와 `metadata.json`은 공개 가능한 baseline source이면 Git에 추적한다.
- v1, v2 suite가 같은 sample을 써도 sample은 한 번만 존재한다.
- sample 내용이 바뀌면 기존 sample id를 수정하지 말고 새 sample id를 만든다.
