# Phase 4: large-v3 CUDA Verification

## Scope

- KSS fixture를 `large-v3`로 변환한다.
- CUDA 실행 가능 여부를 확인한다.
- `tiny` smoke result와 비교한다.

## Fixture

- Audio: `fixtures/generated/kss-row-00000/audio.wav`.
- Expected: `그는 괜찮은 척하려고 애쓰는 것 같았다.`
- Format: PCM 16-bit, stereo, 44100 Hz.
- Duration: 3.53s.

## Environment

- GPU: NVIDIA GeForce RTX 3050 Mobile, 4GiB VRAM.
- Driver: 535.309.01.
- CUDA driver capability: 12.2.
- Runtime package:
  - `faster-whisper==1.2.1`
  - `nvidia-cublas-cu12==12.9.2.10`
  - `nvidia-cudnn-cu12==9.23.2.1`

## Attempt 1

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model large-v3 --device cuda --compute-type float16 --output output/transcripts/kss-row-00000-large-v3-cuda-float16.txt
```

Result:

- Model download: success.
- Model cache: `~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3`.
- Cache size: about 2.9GiB.
- Failure: `RuntimeError: Library libcublas.so.12 is not found or cannot be loaded`.

Decision:

- CUDA driver만으로는 부족하다.
- venv에 CUDA user-space libraries를 설치한다.

## Fix

```bash
.venv/bin/pip install -r requirements-cuda.txt
```

`scripts/transcribe.sh`가 venv의 NVIDIA library path를 `LD_LIBRARY_PATH`에 추가한다.

## Attempt 2

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model large-v3 --device cuda --compute-type float16 --output output/transcripts/kss-row-00000-large-v3-cuda-float16.txt
scripts/compare_transcript.py fixtures/generated/kss-row-00000/expected.txt output/transcripts/kss-row-00000-large-v3-cuda-float16.txt --exact
```

Result:

- Device: `cuda`.
- Compute type: `float16`.
- Transcript: `그는 괜찮은 척하려고 애쓰는 것 같았다.`
- Elapsed: 11.99s.
- Exact match: pass.
- Normalized match: pass.

## Default Option Check

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --output output/transcripts/kss-row-00000-default-large-v3.txt
scripts/compare_transcript.py fixtures/generated/kss-row-00000/expected.txt output/transcripts/kss-row-00000-default-large-v3.txt --exact
```

Result:

- Resolved model: `large-v3`.
- Resolved device: `cuda`.
- Resolved compute type: `float16`.
- Elapsed: 10.76s.
- Exact match: pass.

## Decision

- `large-v3` CUDA `float16` is viable on this machine for short Korean fixture input.
- Accuracy baseline for Korean fixture is exact match.
- `requirements-cuda.txt` is optional but required for local CUDA execution in this repo.

## Follow-up

- Add multiple Korean fixtures.
- Add command-shaped Korean fixtures.
- Add Korean-English mixed fixtures.
- Measure longer input memory and latency.
