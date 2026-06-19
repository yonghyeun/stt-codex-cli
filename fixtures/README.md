# Fixtures

재현 가능한 STT 검증용 로컬 fixture 위치.

## Generated KSS Fixture

```bash
scripts/fetch_kss_fixture.py --row-idx 0
```

생성 위치:

- `fixtures/generated/kss-row-00000/audio.wav`
- `fixtures/generated/kss-row-00000/expected.txt`
- `fixtures/generated/kss-row-00000/metadata.local.json`

`fixtures/generated/`는 Git 추적 제외다.

## KSS Korean Core Suite

```bash
scripts/fetch_kss_fixture.py --manifest fixtures/kss-ko-core-v1.json
scripts/run_fixture_suite.sh fixtures/kss-ko-core-v1.json --model large-v3 --device cuda --compute-type float16
```

- Manifest: `fixtures/kss-ko-core-v1.json`
- Generated root: `fixtures/generated/kss-ko-core-v1/`
- Result output: `output/suite/`
- Pass 기준 기본값은 normalized match다.
- 단어 추가, 누락, 치환은 실패로 본다.
- 문장부호 차이는 기본 실패로 보지 않는다.

## Source

- Dataset: `Bingsu/KSS_Dataset`
- Source: <https://huggingface.co/datasets/Bingsu/KSS_Dataset>
- License: `cc-by-nc-sa-4.0`

이 fixture는 비상업 실험용으로만 사용한다. 상업 사용 가능 fixture가 필요하면 CC0 또는 별도 사용 허가가 있는 데이터셋으로 교체한다.

## HiKE Code-Switch Suite

```bash
scripts/fetch_hike_fixture.py --manifest fixtures/hike-code-switch-core-v1.json
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
```

- Manifest: `fixtures/hike-code-switch-core-v1.json`
- Generated root: `fixtures/generated/hike-code-switch-core-v1/`
- Result output: `output/suite/`
- Source: <https://huggingface.co/datasets/thetaone-ai/HiKE>
- License: `apache-2.0`
- Code-switching suite는 우선 측정용이다.
- 통과 기준은 별도 실험 후 정한다.
- Latin-script token 보존율을 별도로 확인한다.
- 외래어의 한글 표기는 일반 한국어 입력에서는 자연스러울 수 있다.
- 파일명, 옵션명, 코드 식별자 문맥에서는 별도 token recovery 기준이 필요하다.
