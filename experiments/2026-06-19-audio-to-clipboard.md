# Phase 10: Audio to Clipboard

## Scope

- 기존 audio 파일을 입력으로 받는다.
- STT 변환을 수행한다.
- token recovery를 적용한다.
- 최종 텍스트를 clipboard에 복사한다.
- 녹음과 push-to-talk UX는 아직 통합하지 않는다.

## Script

- `scripts/stt_clipboard.sh`.

## Interface

```bash
scripts/stt_clipboard.sh [wrapper options] audio_file [transcribe options...]
```

Wrapper option은 `audio_file` 앞에 둔다.

- `--no-recovery`
- `--memory PATH`
- `--min-confidence VALUE`
- `--clipboard-backend BACKEND`
- `--no-copy-verify`
- `--output-transcript PATH`
- `--output-recovered PATH`

`audio_file` 뒤의 option은 `scripts/transcribe.sh`에 전달한다.

## Commands

Smoke test:

```bash
scripts/stt_clipboard.sh fixtures/generated/kss-row-00000/audio.wav --model tiny --device cpu --compute-type int8
```

정확도 기준 모델:

```bash
scripts/stt_clipboard.sh fixtures/generated/kss-row-00000/audio.wav --model large-v3 --device cuda --compute-type float16
```

복원 전/후 텍스트 저장:

```bash
scripts/stt_clipboard.sh \
  --output-transcript output/transcripts/kss-row-00000-raw.txt \
  --output-recovered output/transcripts/kss-row-00000-final.txt \
  fixtures/generated/kss-row-00000/audio.wav \
  --model tiny --device cpu --compute-type int8
```

## Result

- `scripts/stt_clipboard.sh --help` 성공.
- missing audio file은 exit 2로 실패.
- transcribe option을 audio file 뒤에 전달하는 흐름 확인.
- KSS row 0 audio로 tiny CPU smoke test 성공.
- smoke test raw transcript: `그는 괜찮은 척하려고, 애쓰는 것 같았다.`
- smoke test final text: `그는 괜찮은 척하려고, 애쓰는 것 같았다.`
- 최종 텍스트가 clipboard에 복사됨.
- `--no-recovery --no-copy-verify` 경로 성공.
- 테스트 중 기존 clipboard는 복원했다.

## Decision

- 통합 명령의 첫 형태는 기존 audio 파일 입력으로 제한한다.
- 최종 stdout은 clipboard에 복사된 텍스트다.
- 단계 로그는 stderr에 출력한다.
- Codex CLI 자동 전송은 하지 않는다.

## Follow-up

- `record.sh`와 `stt_clipboard.sh`를 묶어 녹음부터 clipboard까지 실행한다.
- 이후 push-to-talk UX를 추가한다.
