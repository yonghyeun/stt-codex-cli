# Scripts

STT 실행 스크립트 위치.

초기 목표:

- 짧은 마이크 녹음.
- 로컬 STT 변환.
- 결과를 클립보드에 복사.
- 수동 memory 기반 token recovery.

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

## Prototype 8: Manual Token Recovery

수동 memory에 등록된 표현만 복원한다.

```bash
scripts/recover_tokens.py --memory memory/manual-aliases.example.json "리드미 수정해"
```

기대 출력:

```text
README.md 수정해
```

Fixture test:

```bash
scripts/recover_tokens.py --fixture fixtures/token-recovery-v1.json
```

- 기본 memory는 `memory/manual-aliases.json`이다.
- 기본 memory가 없으면 `memory/manual-aliases.example.json`을 사용한다.
- `STT_TOKEN_MEMORY`로 memory 파일을 지정할 수 있다.
- 원문 transcript는 보존하고 복원본만 출력한다.
- LLM, GPU, network는 사용하지 않는다.

## Prototype 9: Clipboard Copy

텍스트를 clipboard에 복사한다.

```bash
echo "README.md 수정해" | scripts/copy_text.sh
```

인자로 직접 전달할 수도 있다.

```bash
scripts/copy_text.sh "README.md 수정해"
```

- 기본 backend는 `auto`다.
- 현재 Linux 기준 backend는 `xclip`이다.
- Wayland 환경에서 `wl-copy`와 `wl-paste`가 있으면 `wl-copy` backend도 사용할 수 있다.
- `--backend xclip`처럼 backend를 명시할 수 있다.
- 기본적으로 복사 후 clipboard를 다시 읽어 검증한다.
- `--no-verify`를 주면 복사 검증을 생략한다.
- stdout에는 복사한 텍스트를 출력한다.
- stderr에는 backend와 검증 여부를 출력한다.

## Prototype 10: Audio to Clipboard

기존 audio 파일을 STT로 변환하고, token recovery 후 clipboard에 복사한다.

```bash
scripts/stt_clipboard.sh fixtures/generated/kss-row-00000/audio.wav --model large-v3 --device cuda --compute-type float16
```

작은 CPU 모델로 smoke test:

```bash
scripts/stt_clipboard.sh fixtures/generated/kss-row-00000/audio.wav --model tiny --device cpu --compute-type int8
```

복원 전/후 텍스트를 파일로 남길 수 있다.

```bash
scripts/stt_clipboard.sh \
  --output-transcript output/transcripts/raw.txt \
  --output-recovered output/transcripts/final.txt \
  fixtures/generated/kss-row-00000/audio.wav \
  --model tiny --device cpu --compute-type int8
```

- wrapper option은 audio 파일 앞에 둔다.
- audio 파일 뒤의 option은 `scripts/transcribe.sh`에 전달한다.
- 기본적으로 token recovery를 수행한다.
- `--no-recovery`를 주면 STT 결과를 그대로 복사한다.
- 기본적으로 clipboard readback 검증을 수행한다.
- `--no-copy-verify`를 주면 clipboard 검증을 생략한다.
- STT 결과가 비어 있거나 punctuation-only이면 clipboard에 복사하지 않고 실패한다.

## Prototype 11: Record to Clipboard

마이크를 정해진 시간 녹음하고, STT 변환과 token recovery 후 clipboard에 복사한다.

```bash
scripts/record_clipboard.sh --duration 5 -- --model large-v3 --device cuda --compute-type float16
```

작은 CPU 모델로 짧게 테스트:

```bash
scripts/record_clipboard.sh --duration 3 -- --model tiny --device cpu --compute-type int8
```

녹음 파일 생성만 확인:

```bash
scripts/record_clipboard.sh --record-only --duration 1
```

- `--` 앞의 option은 record/clipboard wrapper가 처리한다.
- `--` 뒤의 option은 `scripts/transcribe.sh`에 전달한다.
- 기본 duration은 5초다.
- 기본적으로 token recovery와 clipboard readback 검증을 수행한다.
- 실제 발화가 없으면 STT 결과가 비어 실패할 수 있다.
- 무발화 환각으로 punctuation-only 결과가 나오면 clipboard에 복사하지 않고 실패한다.

## Prototype 12: Push to Talk

기본 hotkey는 `Alt+T`다. 누르면 녹음이 시작되고, 떼면 녹음이 종료된다.

```bash
scripts/push_to_talk.py -- --model large-v3 --device cuda --compute-type float16
```

녹음 파일 생성만 확인:

```bash
scripts/push_to_talk.py --record-only
```

사용자가 hotkey를 바꿀 수 있다.

```bash
scripts/push_to_talk.py --keycode 74 --no-modifier --record-only
```

현재 `Alt+T` 기본값:

- `t`: keycode `28`
- `Alt_L`: keycode `64`
- `Alt_R`: keycode `108`
- 추가 Alt mapping: keycode `204`

keycode 확인:

```bash
xmodmap -pke | grep -E 'Alt_L|Alt_R| t '
```

- `--keycode`로 trigger keycode를 바꾼다.
- `--modifier-keycodes 64,108`처럼 modifier keycode 목록을 바꾼다.
- `--no-modifier`를 주면 modifier 없이 trigger key만 누른다.
- `--max-duration`은 누른 채로 잊었을 때 녹음을 자동 종료하는 안전장치다.
- `xinput test-xi2 --root` 이벤트를 사용하므로 Wayland/Xwayland 환경에서는 동작 제약이 있을 수 있다.

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
