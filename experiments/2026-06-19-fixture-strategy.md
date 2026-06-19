# Fixture Strategy

## Decision

실제 마이크 발화 대신, 정답 transcript가 있는 외부 음성 샘플을 fixture로 사용한다.

## Reason

- 녹음 환경, 마이크 감도, 발화 속도 변수를 줄인다.
- STT 변환 스크립트의 회귀 검증이 쉬워진다.
- 모델별 정확도 비교에 같은 입력을 반복 사용할 수 있다.

## Selected Fixture Source

- Dataset: `Bingsu/KSS_Dataset`.
- Source: <https://huggingface.co/datasets/Bingsu/KSS_Dataset>.
- License: `cc-by-nc-sa-4.0`.
- Row: `train[0]`.
- Expected transcript: `그는 괜찮은 척하려고 애쓰는 것 같았다.`

## Constraint

- KSS는 비상업 라이선스다.
- WAV와 생성 metadata는 `fixtures/generated/`에만 생성하고 Git에 넣지 않는다.
- 상업 사용 가능성이 생기면 CC0 fixture로 교체한다.

## Verification Command

```bash
scripts/fetch_kss_fixture.py --row-idx 0
scripts/transcribe.sh fixtures/generated/kss-row-00000/audio.wav --model tiny --device cpu --compute-type int8 --output output/transcripts/kss-row-00000-tiny.txt
scripts/compare_transcript.py fixtures/generated/kss-row-00000/expected.txt output/transcripts/kss-row-00000-tiny.txt
```

## Observed Result

- Audio format: PCM 16-bit, stereo, 44100 Hz.
- Duration: 3.53s.
- Expected: `그는 괜찮은 척하려고 애쓰는 것 같았다.`
- Tiny transcript: `그는 괜찮은 척하려고, 애쓰는 것 같았다.`
- Normalized comparison: pass.
