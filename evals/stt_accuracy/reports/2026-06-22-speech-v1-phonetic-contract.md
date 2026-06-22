# speech/v1 한글 음가 contract 재정렬

## Summary

`speech/v1`의 expected text 기준을 한글 음가 transcript로 고정했다.

이제 active v1 suite는 개발 literal을 보존하거나 복원하는 능력을 통과 기준으로 보지 않는다. 먼저 사용자가 말한 소리를 한글 음가로 안정적으로 전사하는지 확인한다.

## Contract Decision

- `expected.txt`는 v1에서 기대하는 STT transcript다.
- `expected_text_policy`는 `korean_phonetic_transcript`다.
- active suite metric은 `phonetic_transcript_match`와 `insertion_safe`다.
- `latin_token_preservation`, `file_path_preservation`, `cli_option_preservation`, `code_identifier_preservation`은 v2 literal 복원 평가에서 다시 다룬다.
- token recovery, command normalization, ranking은 v1 통과 기준이 아니다.

## Sample Alignment

기존 `speech/v1` sample 24개를 같은 정책으로 정렬했다.

- 24개 metadata에 `expected_text_policy: korean_phonetic_transcript`를 기록했다.
- Latin literal이 남아 있던 expected text를 한글 음가로 바꿨다.
- 이미 자연 발화에 가깝게 재정렬된 file path와 CLI option sample은 같은 정책값으로 통일했다.
- 실제 audio는 계속 local-only이며 Git에 추적하지 않는다.

## Suite Alignment

`codex-command-accuracy-v1`은 v1에서 한글 음가 transcript match를 측정한다.

모든 case는 다음 metric만 사용한다.

- `phonetic_transcript_match`
- `insertion_safe`

literal 보존 metric은 삭제한 것이 아니라 v1 active pass 기준에서 제외했다. 후속 literal 복원 suite나 token recovery 평가에서 다시 사용할 수 있다.

## Initial Prompt Iteration Impact

기존 `initial_prompt` iteration report는 final literal 보존 기준에서 작성된 historical evidence다.

새 v1 contract에서는 그 결과를 현재 active suite의 성공 판단으로 바로 사용하지 않는다. prompt 실험을 이어가려면 한글 음가 expected text와 `phonetic_transcript_match` metric 위에서 baseline 또는 prompt run을 다시 실행해야 한다.

## Verification Summary

- `phonetic_transcript_match` unit test 통과.
- active suite metric contract test 통과.
- sample metadata policy와 expected text Latin 제거 test 통과.
- JSON syntax validation 통과.
- sample metadata와 suite manifest jsonschema validation 통과.
- `scripts/run_stt_accuracy_suite.py --dry-run` 통과.
- `audio.wav` ignore rule 확인.
