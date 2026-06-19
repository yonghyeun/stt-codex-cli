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

## Source

- Dataset: `Bingsu/KSS_Dataset`
- Source: <https://huggingface.co/datasets/Bingsu/KSS_Dataset>
- License: `cc-by-nc-sa-4.0`

이 fixture는 비상업 실험용으로만 사용한다. 상업 사용 가능 fixture가 필요하면 CC0 또는 별도 사용 허가가 있는 데이터셋으로 교체한다.
