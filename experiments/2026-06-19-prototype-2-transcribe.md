# Prototype 2: Transcribe Existing Audio

## Scope

- 이미 생성된 WAV 파일을 로컬 STT 런타임으로 텍스트 변환한다.
- 녹음과 클립보드 복사는 이 실험 범위가 아니다.

## Runtime

- Package: `faster-whisper==1.2.1`.
- Smoke model: `tiny`.
- Smoke device: `cpu`.
- Smoke compute type: `int8`.
- Cache: `~/.cache/huggingface/hub/models--Systran--faster-whisper-tiny`.
- Model cache size: 약 75MiB.

## Input

- File: `output/recordings/recording-20260619-114042.wav`.
- Format: PCM 16-bit, mono, 16000 Hz.
- Duration: 1.0s.
- Note: 실제 발화 검증용 샘플이 아니라 녹음 경로 확인용 짧은 파일이다.

## Result

```bash
scripts/transcribe.sh output/recordings/recording-20260619-114042.wav --model tiny --device cpu --compute-type int8 --no-vad-filter
```

- First run elapsed: 14.12s.
- Transcript without VAD: `너,,,,,,,,,,,,,,.`
- 판단: 무음 또는 무의미 입력에서 환각 가능.

```bash
scripts/transcribe.sh output/recordings/recording-20260619-114042.wav --model tiny --device cpu --compute-type int8 --vad-filter
```

- Warm run elapsed: 1.44s.
- Transcript with VAD: empty.
- 판단: VAD filter를 기본 활성화한다.

## Decision

- Prototype 2 런타임은 `faster-whisper`로 시작한다.
- 정확도 실험 기본 후보는 `large-v3`다.
- `tiny`는 기능 smoke test 전용이다.
- 무음 환각 방지를 위해 VAD filter를 기본 활성화한다.

## Follow-up

- 실제 한국어 발화 샘플로 정확도 실험 필요.
- 한영 혼합 명령 샘플 필요.
- `large-v3` CUDA 실행 가능성 확인 필요.
