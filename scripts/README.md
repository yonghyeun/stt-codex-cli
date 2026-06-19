# Scripts

STT 실행 스크립트 위치.

초기 목표:

- 짧은 마이크 녹음.
- 로컬 STT 변환.
- 결과를 클립보드에 복사.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

CUDA 실행이 필요하면 추가 설치한다.

```bash
.venv/bin/pip install -r requirements-cuda.txt
```

`scripts/transcribe.sh`는 venv에 설치된 CUDA library path를 자동으로 `LD_LIBRARY_PATH`에 추가한다.

## Prototype 1: Record Only

```bash
scripts/record.sh 5
```

- 기본 출력 위치는 `output/recordings/`다.
- 기본 녹음 설정은 16kHz, mono, `S16_LE`, WAV다.
- 기본 ALSA device는 `default`다.
- 장치 문제가 있으면 `STT_RECORD_DEVICE=plughw:CARD=Generic_1,DEV=0`처럼 지정한다.

## Prototype 2: Transcribe Existing Audio

재현 fixture를 먼저 생성한다.

```bash
scripts/fetch_kss_fixture.py --row-idx 0
```

Smoke test는 작은 모델을 명시한다.

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model tiny --device cpu --compute-type int8
```

Fixture transcript를 비교한다.

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model tiny --device cpu --compute-type int8 --output output/transcripts/kss-row-00000-tiny.txt
scripts/compare_transcript.py fixtures/generated/kss-row-00000/expected.txt output/transcripts/kss-row-00000-tiny.txt
```

여러 한국어 fixture를 한 번에 검증한다.

```bash
scripts/fetch_kss_fixture.py --manifest fixtures/kss-ko-core-v1.json
scripts/run_fixture_suite.sh fixtures/kss-ko-core-v1.json --model large-v3 --device cuda --compute-type float16
```

한영 혼합 fixture를 측정한다.

```bash
scripts/fetch_hike_fixture.py --manifest fixtures/hike-code-switch-core-v1.json
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
```

Prompt가 Latin-script token 보존에 도움이 되는지 측정할 수 있다.

```bash
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none --initial-prompt "Preserve English technical terms in Latin letters."
```

정확도 실험은 큰 모델을 우선한다.

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model large-v3
```

CUDA를 명시하려면 다음처럼 실행한다.

```bash
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model large-v3 --device cuda --compute-type float16
```

- 기본 모델은 정확도 우선 기준에 맞춰 `large-v3`다.
- 기본 언어는 `ko`다.
- 기본 device는 CUDA가 있으면 `cuda`, 없으면 `cpu`다.
- 기본 compute type은 CUDA에서 `float16`, CPU에서 `float32`다.
- 무음 환각을 줄이기 위해 VAD filter는 기본 활성화한다.
- 변환 결과는 stdout으로 출력한다.
- `--output output/transcripts/example.txt`를 주면 텍스트 파일도 저장한다.
- `--initial-prompt` 또는 `STT_INITIAL_PROMPT`로 faster-whisper initial prompt를 지정할 수 있다.
- fixture 비교는 기본적으로 공백과 문장부호를 제거한 normalized match를 사용한다.
- suite 검증은 단어 추가, 누락, 치환을 실패로 본다.
- KSS fixture는 `cc-by-nc-sa-4.0`이므로 비상업 실험용으로만 사용한다.
