# Scripts

STT 실행 스크립트 위치.

초기 목표:

- 짧은 마이크 녹음.
- 로컬 STT 변환.
- Codex CLI를 child PTY로 실행.
- STT 결과를 Codex CLI 입력창에 삽입.
- 사용자가 확인 후 직접 전송.

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

분리된 worktree에서 이미 준비된 venv를 재사용해야 하면 환경변수로 Python과
site-packages 위치를 지정할 수 있다. 기본값은 repo root의 `.venv`다.

```bash
STT_PYTHON_BIN=/path/to/.venv/bin/python \
STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \
scripts/transcribe.sh audio.wav --model large-v3 --device cuda --compute-type float16
```

## Codex STT Launcher Command

`codex-stt`를 shell alias가 아니라 PATH에 놓는 launcher command로 설치한다.

```bash
scripts/install_codex_stt_command.sh --dry-run
scripts/install_codex_stt_command.sh
```

기본 설치 위치:

```text
${HOME}/.local/bin/codex-stt
```

기본 repo root:

```text
${HOME}/stt-codex-cli
```

설치 후 실행:

```bash
codex-stt
codex-stt --stt-model large-v3 --stt-device cuda --stt-compute-type float16
codex-stt --stt-backend worker --audio-handoff buffer
```

repo가 기본 위치가 아닌 곳에 있으면 runtime override를 사용한다.

```bash
CODEX_STT_ROOT=/path/to/stt-codex-cli codex-stt --help
```

다른 위치에 설치하려면 `--target`을 지정한다.

```bash
scripts/install_codex_stt_command.sh --target /tmp/codex-stt
```

이미 다른 내용의 target 파일이 있으면 실패한다. 덮어쓰려면 `--force`를 명시한다.

```bash
scripts/install_codex_stt_command.sh --force
```

삭제:

```bash
rm "${HOME}/.local/bin/codex-stt"
```

## STT Accuracy Baseline Harness

`codex-command-accuracy-v1` baseline 실행 전에는 dry-run으로 suite와 input 연결을
검증한다.

```bash
scripts/run_stt_accuracy_suite.py \
  --suite codex-command-accuracy-v1 \
  --input-root evals/inputs/speech/v1 \
  --run-id 20260621-large-v3-cuda-float16-baseline \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --dry-run
```

실제 baseline 실행은 `--dry-run`만 제거한다.

```bash
scripts/run_stt_accuracy_suite.py \
  --suite codex-command-accuracy-v1 \
  --input-root evals/inputs/speech/v1 \
  --run-id 20260621-large-v3-cuda-float16-baseline \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko
```

- dry-run은 모델을 load하지 않는다.
- dry-run은 `audio.wav`, `expected.txt`, `metadata.json`, suite case mapping, run path 계획을 확인한다.
- 실행 결과는 `evals/stt_accuracy/runs/<run_id>/` 아래에 local-only로 남긴다.
- raw transcript는 `raw/<sample_id>.txt`에 쓴다.
- baseline에서는 token recovery를 쓰지 않으며 `recovered/<sample_id>.txt`는 raw와 같은 텍스트를 쓴다.
- `result.json`은 metric 결과, failure taxonomy summary, `expected_text`/`raw_text`/`recovered_text` 비교, 정량 품질 지표를 소유한다.
- v1 suite의 pass 기준 metric은 `phonetic_transcript_match`와 `insertion_safe`다.
- 정량 품질 지표는 `char_error_rate`, `normalized_char_error_rate`, `text_similarity`, `word_error_rate`, `critical_token_precision`, `critical_token_recall`, `critical_token_f1`, `case_score`를 포함한다.
- metric 설명과 renderer routing은 `evals/stt_accuracy/metric_contract.json`이 소유한다.
- Git-tracked report에는 raw transcript 전체를 붙이지 않는다.

`result.json`을 사람이 읽는 Markdown으로 확인한다.

```bash
scripts/render_stt_accuracy_result.py \
  evals/stt_accuracy/runs/20260621-large-v3-cuda-float16-baseline/result.json
```

case별 full text 비교가 필요하면 local inspection 용도로만 `--show-text`를 사용한다.

```bash
scripts/render_stt_accuracy_result.py \
  evals/stt_accuracy/runs/20260621-large-v3-cuda-float16-baseline/result.json \
  --show-text
```

renderer 출력은 stdout으로만 쓴다. `--show-text` 출력에는 raw transcript 본문이 포함되므로 Git-tracked report에 그대로 붙이지 않는다.

renderer는 기본적으로 `evals/stt_accuracy/metric_contract.json`을 읽어 summary metric,
source metric, direction, failure type 설명을 출력한다. 다른 contract 검증이 필요할 때만
`--metric-contract <path>`를 사용한다.

## Audio Handoff Latency Harness

`#32` buffer handoff는 persistent worker의 file handoff와 buffer handoff를 같은 fixed
smoke input으로 비교한다.

```bash
STT_PYTHON_BIN=/path/to/.venv/bin/python \
STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \
scripts/measure_audio_handoff_latency.py \
  --run-id 20260623-buffer-handoff-large-v3-cuda-float16 \
  --input-root /path/to/stt-codex-cli/evals/inputs/speech/v1 \
  --model large-v3 \
  --device cuda \
  --compute-type float16 \
  --language ko \
  --report-output evals/stt_accuracy/reports/2026-06-23-buffer-handoff.md
```

Dry-run은 model load 없이 suite/input 연결과 비교 대상 mode만 검증한다.

```bash
scripts/measure_audio_handoff_latency.py \
  --input-root /path/to/stt-codex-cli/evals/inputs/speech/v1 \
  --dry-run
```

- `file`: persistent worker에 WAV path를 전달한다.
- `buffer`: persistent worker에 base64 WAV bytes를 전달한다.
- 실행 결과는 `evals/stt_accuracy/runs/<run_id>/` 아래 local-only artifact로 남긴다.
- report는 `#29` fixed smoke latency baseline과 case score를 prior value로 표시한다.

## Speech Sample Recording

sample id 목록에서 아직 `audio.wav`가 없는 다음 sample 하나를 선택해 녹음한다.
배치 duration 녹음이 아니라 generator처럼 한 번 호출할 때 한 sample만 처리한다.

```bash
scripts/record_speech_samples.sh \
  cmd-0009 cmd-0010 cmd-0011 cmd-0012 cmd-0013 cmd-0014 cmd-0015 cmd-0016
```

- 각 sample마다 `expected.txt` 첫 줄을 보여준다.
- 기본 동작은 목록 중 첫 번째 missing `audio.wav` sample 하나를 녹음하는 것이다.
- 녹음은 `scripts/push_to_talk.py --record-only`를 재사용한다.
- 기본 stdin-repeat backend에서는 `t`를 누르고 있는 동안 녹음하고, 떼면 종료한다.
- 녹음 결과는 `evals/inputs/speech/v1/samples/<sample_id>/audio.wav`에 쓴다.
- 특정 sample을 다시 녹음하려면 `--sample-id <id> --force`를 사용한다.
- `--print-next` 또는 `--dry-run`은 녹음 없이 다음 대상만 출력한다.

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

기본 backend는 `stdin-repeat`다. 터미널이 받는 `t` 반복 입력을 이용한다.

`t`를 누르면 녹음이 시작되고, `t` 반복 입력이 끊기면 녹음이 종료된다.

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

현재 기본값:

- `t`: keycode `28`
- terminal trigger key: `t`
- release gap: `0.75s`

XInput backend에서 `Alt+T`로 실행:

```bash
scripts/push_to_talk.py --backend xinput --keycode 28 --require-modifier --modifier-keycodes 64,108,204 --record-only
```

Alt keycode:

- `Alt_L`: keycode `64`
- `Alt_R`: keycode `108`
- 추가 Alt mapping: keycode `204`

keycode 확인:

```bash
xmodmap -pke | grep -E 'Alt_L|Alt_R| t '
```

- `--trigger-key`로 terminal trigger key를 바꾼다.
- `--release-gap`으로 terminal key release 판정 시간을 바꾼다.
- `--backend xinput`에서 `--keycode`로 trigger keycode를 바꾼다.
- `--backend xinput`에서 기본은 modifier 없이 trigger key만 누른다.
- `--backend xinput --require-modifier`를 주면 modifier와 trigger key 조합을 요구한다.
- `--backend xinput --modifier-keycodes 64,108`처럼 modifier keycode 목록을 바꾼다.
- `--max-duration`은 누른 채로 잊었을 때 녹음을 자동 종료하는 안전장치다.
- `stdin-repeat` backend는 terminal focus와 key repeat 설정에 의존한다.
- `xinput test-xi2 --root` 이벤트를 사용하므로 Wayland/Xwayland 환경에서는 동작 제약이 있을 수 있다.

## Prototype 13: Codex PTY Wrapper

Codex CLI를 child PTY로 실행하고 입출력을 그대로 전달한다.

```bash
scripts/stt_codex.py
```

다른 command로 passthrough를 검증할 수 있다.

```bash
scripts/stt_codex.py --cmd python3 -- -q
```

- 기본 command는 `codex`다.
- `STT_CODEX_CMD`로 기본 command를 바꿀 수 있다.
- `--cmd` 뒤의 command가 child PTY 안에서 실행된다.
- `--` 뒤의 argument는 child command에 전달된다.
- parent wrapper status line은 `[stt-parent]` prefix로 표시된다.
- 기본 Codex 실행에는 `--no-alt-screen`을 추가해 parent/child 경계가 scrollback에 남게 한다.
- `--codex-alt-screen`을 주면 Codex 기본 alternate screen 동작을 유지한다.
- `--quiet-parent`를 주면 parent status line을 숨긴다.
- `--no-color`를 주면 parent status line 색상을 끈다.
- 기본 injection mode는 `stt`다.
- `stt` mode의 기본 injection key는 `ctrl+t`다.
- `fixed-text` mode의 기본 injection key는 `ctrl+t`다.
- `--inject-mode fixed-text`로 고정 텍스트 injection을 테스트할 수 있다.
- `--inject-text`로 child PTY에 삽입할 고정 텍스트를 바꾼다.
- `--inject-key`로 삽입 trigger key를 바꾼다.
- `--disable-inject-key`를 주면 모든 stdin을 child PTY로 그대로 전달한다.
- injection은 텍스트만 삽입하며 Enter는 보내지 않는다.
- Codex CLI 자동 전송은 하지 않는다.

## Prototype 14: Fixed Text Injection

STT 연결 전에 parent가 child PTY 입력창에 텍스트를 삽입할 수 있는지 검증한다.

```bash
scripts/stt_codex.py --inject-mode fixed-text
```

실행 후 `Ctrl+T`를 누르면 기본 문장이 Codex 입력창에 삽입된다.

```text
hello from stt wrapper
```

사용자는 내용을 확인한 뒤 직접 Enter를 누른다.

검증용 child command:

```bash
scripts/stt_codex.py --inject-mode fixed-text --cmd python3 -- -c 'import sys; print("child:" + sys.stdin.readline().strip())'
```

위 command에서 `Ctrl+T`를 누르고 Enter를 누르면 child가 삽입된 텍스트를 출력한다.

## Prototype 15: STT Transcript Injection

기본 mode다. `Ctrl+T`를 누르고 말하면 녹음하고, `Ctrl+T` 반복 입력이 끊긴 뒤 STT raw transcript를 child PTY 입력창에 삽입한다.

```bash
scripts/stt_codex.py
```

정확도 기준 모델을 명시:

```bash
scripts/stt_codex.py --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

짧은 smoke test:

```bash
scripts/stt_codex.py --stt-model tiny --stt-device cpu --stt-compute-type int8 --cmd python3 -- -q
```

PTT speed profile:

```bash
scripts/stt_codex.py --ptt-profile speed
```

- STT mode 기본 trigger는 `ctrl+t`다.
- `ctrl+t`는 child PTY로 전달되지 않고 parent가 소비한다.
- `--inject-key t`처럼 trigger를 바꿀 수 있다.
- `--ptt-profile`은 release gap profile이다. 기본값은 `accuracy`다.
- `accuracy` profile release gap은 `0.75s`다.
- `speed` profile release gap은 `0.35s`다.
- `STT_PTT_PROFILE=speed`로 speed profile을 기본 선택할 수 있다.
- `--release-gap`은 trigger 반복 입력이 끊긴 뒤 녹음을 종료할 때까지 기다리는 시간을 직접 지정한다.
- 우선순위는 `--release-gap` / `STT_PTT_RELEASE_GAP` > `--ptt-profile` / `STT_PTT_PROFILE` > `accuracy` default다.
- `speed` profile의 deterministic wait delta는 `0.75s -> 0.35s`, 즉 `-0.40s`다.
- release gap을 낮추면 말 끝 truncation risk가 커질 수 있다.
- `--min-duration`보다 짧은 녹음은 STT 없이 버린다.
- `--max-duration`을 넘으면 자동으로 녹음을 종료한다.
- 녹음 파일은 system temp directory에 임시 WAV로 만든다.
- 기본적으로 STT 후 임시 WAV를 삭제한다.
- `--keep-audio`를 주면 임시 WAV를 삭제하지 않는다.
- `--save-run`을 주면 `output/runs/` 아래에 audio, transcript, metadata를 저장한다.
- transcript가 비어 있거나 punctuation-only이면 child PTY에 삽입하지 않는다.
- token recovery는 수행하지 않는다.
- Enter는 사용자가 직접 누른다.

## Prototype 16: Optional Run Artifact Save

기본적으로 녹음본과 transcript는 영구 저장하지 않는다. 디버깅이나 정확도 비교가 필요할 때만 `--save-run`을 켠다.

```bash
scripts/stt_codex.py --save-run
```

정확도 기준 모델과 함께 저장:

```bash
scripts/stt_codex.py --save-run --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

저장 위치를 바꿀 수 있다.

```bash
scripts/stt_codex.py --save-run --run-output-dir output/runs
```

Run directory 구조:

```text
output/runs/20260620-153012-427-stt-codex/
  audio.wav
  transcript.txt
  metadata.json
```

- directory 이름은 `YYYYMMDD-HHMMSS-mmm-stt-codex` 형식이다.
- 같은 millisecond에 충돌하면 `-001` suffix를 붙인다.
- `metadata.json`에는 recording config, STT option, elapsed time, outcome, injected 여부를 기록한다.
- 가능한 outcome은 `injected`, `empty_transcript`, `skipped_short_recording`, `stt_error`, `interrupted_recording`이다.
- `--keep-audio`는 system temp directory의 임시 WAV도 함께 남기는 debug option이다.

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
- 기본 initial prompt는 한국어 음가 우선 전사 정책이다.
- `--initial-prompt` 또는 `STT_INITIAL_PROMPT`로 faster-whisper initial prompt를 덮어쓸 수 있다.
- fixture 비교는 기본적으로 공백과 문장부호를 제거한 normalized match를 사용한다.
- suite 검증은 단어 추가, 누락, 치환을 실패로 본다.
- KSS fixture는 `cc-by-nc-sa-4.0`이므로 비상업 실험용으로만 사용한다.

Wrapper session에서 model load를 한 번만 수행하려면 persistent worker backend를
명시한다. audio handoff는 여전히 임시 WAV path다.

```bash
scripts/stt_codex.py --stt-backend worker --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

- 기본 backend는 `subprocess`다.
- `worker` backend는 `scripts/transcribe_worker.sh`가 CUDA library path를 준비한 뒤
  `scripts/transcribe_worker.py`를 long-lived process로 실행한다.
- worker protocol은 stdin/stdout newline-delimited JSON이다.
- worker status와 model load log는 stderr에 출력한다.
