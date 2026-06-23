# STT Codex CLI

Linux에서 Codex CLI 입력을 보조하기 위한 로컬 STT 실험 workspace.

## Root

- 이 repo의 기준 경로는 `.`이다.
- 모든 명령과 문서 경로는 repo root `.` 기준으로 작성한다.
- 특정 parent directory 이름에 의존하지 않는다.

## Goal

- 마이크 입력을 텍스트로 변환한다.
- wrapper 안에서 Codex CLI를 실행한다.
- 변환 결과를 Codex CLI 입력창에 자동 삽입한다.
- 사용자가 입력 내용을 확인한 뒤 직접 전송한다.

## Product Contract

최종 산출물은 Linux 데스크탑에서 사용자가 wrapper를 실행하면 그 안에서 Codex CLI가 child PTY로 구동되고, 사용자가 키로 녹음을 시작/종료하면 로컬 STT 모델이 음성을 텍스트로 변환해 Codex CLI 입력창에 삽입하는 입력 보조 도구다.

사용자는 삽입된 텍스트를 직접 확인하고 필요한 경우 수정한 뒤 Enter로 전송한다.

이 도구는 repo 전용 도구가 아니라 일반 terminal coding agent 입력 보조 도구로 확장 가능해야 한다. 초기 구현 대상은 Codex CLI다.

녹음본과 transcript는 기본적으로 영구 저장하지 않는다. STT 처리에는 임시 WAV 파일 또는 in-memory WAV buffer를 사용할 수 있다. 임시 WAV를 만들면 처리가 끝난 뒤 삭제한다. 사용자가 명시적으로 저장 옵션을 켠 경우에만 `output/runs/` 아래에 audio, transcript, metadata를 남긴다.

## Architecture

이 section은 현재 구조의 기준 문서다. 앞으로 아키텍처 변화나 주요 구조 업데이트가 생기면 이 section을 함께 수정한다.

현재 핵심 구조:

```text
terminal
  -> scripts/stt_codex.py thin CLI entrypoint
    -> stt_features.codex_input
      -> stt_runtime child PTY / terminal / recorder / STT subprocess / artifact adapters
      -> stt_core command policy / key parsing / transcript policy / metadata contract
        -> local STT: scripts/transcribe.sh -> scripts/transcribe.py -> faster-whisper
        -> shared STT daemon: scripts/stt_daemon.sh -> scripts/stt_daemon.py -> faster-whisper
```

Runtime flow:

```text
사용자 실행
  -> scripts/stt_codex.py
  -> Codex CLI child PTY 시작
  -> 사용자가 Ctrl+T를 한 번 눌러 녹음 시작
  -> parent wrapper가 audio를 file 또는 buffer handoff로 녹음
  -> 사용자가 Ctrl+T를 다시 한 번 눌러 녹음 종료
  -> faster-whisper로 STT 변환
  -> raw transcript를 Codex 입력창에 삽입
  -> 사용자가 확인 후 Enter
```

Boundary:

- Parent wrapper는 기본 실행에서 terminal 최상단 ASCII parent panel과 하단 1줄 STT status bar를 사용한다.
- 기본 parent panel은 parent terminal 식별용 ASCII marker이며, `--parent-panel none`으로 끌 수 있다.
- Child PTY window size는 parent panel과 status bar를 제외한 크기로 동기화한다.
- Parent wrapper의 raw `[stt-parent]` diagnostic line은 `--debug-stt`에서만 출력한다.
- Child Codex output은 변형하지 않는다.
- 기본 Codex 실행에는 `--no-alt-screen`을 붙여 parent/child 경계가 scrollback에 남게 한다.
- STT 결과는 child PTY에 텍스트로만 삽입한다.
- Enter는 자동으로 보내지 않는다.

Storage:

- 녹음은 STT 처리를 위해 임시 WAV 파일 또는 in-memory WAV buffer로 만든다.
- 기본 runtime은 shared daemon backend와 `--audio-handoff auto`다.
- 기본 실행에서 `--save-run`/`--keep-audio`가 꺼져 있으면 buffer handoff를 사용한다.
- `--save-run`/`--keep-audio` 또는 `--audio-handoff file`을 명시하면 file handoff를 사용한다.
- `--stt-backend subprocess`를 명시하면 file handoff를 사용한다.
- 임시 WAV는 기본 삭제한다.
- `--save-run`을 명시한 경우에만 `output/runs/YYYYMMDD-HHMMSS-mmm-stt-codex/` 아래에 audio, transcript, metadata를 보존한다.
- `--keep-audio`는 임시 WAV 자체를 남기는 debug option이다.
- `output/`은 명시 저장 결과만 담는 위치다.

Current core scripts:

- `scripts/stt_codex.py`: 현재 메인 entrypoint. CLI option과 backward-compatible wrapper surface를 담당한다.
- `scripts/transcribe.sh`: 현재 또는 main worktree venv와 CUDA library path를 준비하고 `transcribe.py`를 subprocess로 실행한다.
- `scripts/transcribe.py`: faster-whisper STT 실행을 담당한다.
- `scripts/transcribe_worker.sh`, `scripts/transcribe_worker.py`: wrapper session 안에서 faster-whisper model을 한 번 load하고 WAV path 또는 in-memory WAV buffer request를 반복 처리하는 persistent worker를 담당한다.
- `scripts/stt_daemon.sh`, `scripts/stt_daemon.py`: load-time config 단위로 faster-whisper model을 한 번 load하고 여러 wrapper request를 Unix domain socket으로 순차 처리하는 shared daemon을 담당한다.
- `scripts/run_fixture_suite.sh`, `scripts/run_fixture_suite.py`: fixture regression을 담당한다.
- `scripts/measure_audio_handoff_latency.py`: persistent worker file handoff와 buffer handoff의 fixed smoke latency/accuracy 비교를 담당한다.
- `scripts/record.sh`, `scripts/push_to_talk.py`, `scripts/stt_clipboard.sh`, `scripts/record_clipboard.sh`, `scripts/copy_text.sh`: 보조 실행 흐름이다.

Current mini-layer modules:

- `stt_core/command.py`: Codex child command policy와 display formatting.
- `stt_core/keyboard.py`: inject key sequence parsing.
- `stt_core/transcript.py`: transcript text 여부 판단.
- `stt_core/run_metadata.py`: run id와 metadata shape.
- `stt_runtime/terminal.py`: terminal raw mode, cwd validation, window-size sync.
- `stt_runtime/child_process.py`: child PTY spawn과 wait status 처리.
- `stt_runtime/recording.py`: temporary WAV와 `arecord` recording lifecycle.
- `stt_runtime/transcription.py`: `scripts/transcribe.sh` subprocess adapter, `scripts/transcribe_worker.sh` persistent worker adapter, shared daemon client adapter.
- `stt_runtime/run_artifacts.py`: `--save-run` artifact persistence.
- `stt_features/codex_input.py`: fixed-text injection과 Ctrl+T STT injection flow.

Mini-layer architecture contract:

- 이 repo의 source ownership은 `scripts`, `stt_core`, `stt_runtime`, `stt_features`로 나눈다.
- 이 계약은 로컬 source tree 안의 문서와 코드 배치 기준이다.
- 이 계약은 로컬 파일만 source of truth로 사용한다.
- 코드가 계약과 다르면 코드가 drift 상태다.
- drift 판단은 이 로컬 문서 계약을 기준으로 한다.

Mini-layer structure:

```text
terminal
  -> scripts/stt_codex.py thin CLI entrypoint
    -> stt_features: user-facing flow
      -> stt_runtime: OS/process/PTY/file adapters
      -> stt_core: pure policy and data contract
```

Layer ownership:

- `scripts/`: 사용자가 실행하는 command surface, CLI option, backward-compatible entrypoint.
- `stt_core/`: 실행환경과 무관한 순수 판단, data contract, deterministic transformation.
- `stt_runtime/`: process, device, terminal, filesystem 같은 외부 실행환경 adapter.
- `stt_features/`: 사용자가 얻는 기능 단위의 flow와 outcome 조립.

Allowed dependency direction:

```text
scripts -> stt_features
scripts -> stt_runtime
scripts -> stt_core
stt_features -> stt_runtime
stt_features -> stt_core
stt_runtime -> stt_core
stt_core -> nothing in this repo
```

Forbidden dependency direction:

- `stt_core -> stt_runtime`
- `stt_core -> stt_features`
- `stt_core -> scripts`
- `stt_runtime -> stt_features`
- `stt_runtime -> scripts`
- `stt_features -> scripts`

Current exclusion:

- token recovery는 wrapper 기본 흐름의 소유 책임이 아니다.
- workspace metadata 기반 복원은 wrapper 기본 흐름의 소유 책임이 아니다.
- clipboard 전달 흐름은 child PTY injection 계약과 별도 실행 흐름이다.
- 다른 terminal coding agent 지원은 현재 Codex CLI wrapper 계약의 소유 책임이 아니다.

## Priority

1. 정확도.
2. Linux 데스크탑에서의 반복 사용 안정성.
3. 입력 UX 단순성.
4. 처리 속도.
5. 설치와 유지보수 난이도.

정확도는 항상 1순위다. 속도나 설치 편의성을 위해 한국어와 한영 혼합 문장의 인식 품질을 크게 낮추지 않는다.

## Interaction Contract

- 실행 환경은 Linux 데스크탑으로 우선 고정한다.
- STT 방식은 로컬 모델 first로 진행한다.
- 입력 방식은 `Ctrl+T` tap-to-record 방식으로 진행한다.
- 결과 전달은 child PTY에 텍스트를 삽입하는 방식으로 진행한다.
- Codex CLI 자동 전송은 하지 않는다. Enter는 사용자가 직접 입력한다.

## Current Usage

PATH command 설치:

```bash
scripts/install_codex_stt_command.sh
```

설치 후 실행:

```bash
codex-stt
```

`codex-stt` launcher의 기본 repo root는 `${HOME}/stt-codex-cli`다.
다른 위치에서 실행해야 하면 `CODEX_STT_ROOT`로 repo root를 지정한다.

```bash
CODEX_STT_ROOT=/path/to/stt-codex-cli codex-stt --help
```

기본 실행:

```bash
scripts/stt_codex.py
```

정확도 기준 모델을 명시:

```bash
scripts/stt_codex.py --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

기본 runtime은 shared daemon과 buffer handoff다:

```bash
scripts/stt_codex.py
```

`--stt-backend daemon`이 기본값이고, `--audio-handoff auto`는 저장/debug audio option이 꺼진 경우 buffer를 사용한다. `--save-run` 또는 `--keep-audio`가 켜지면 file handoff로 돌아가 audio 보존 계약을 우선한다. wrapper-local persistent worker fallback이 필요하면 `--stt-backend worker`를 명시한다. subprocess fallback이 필요하면 `--stt-backend subprocess`를 명시한다.

daemon backend를 명시해도 같은 기본 경로를 사용한다:

```bash
scripts/stt_codex.py --stt-backend daemon --stt-model large-v3 --stt-device cuda --stt-compute-type int8_float16
```

Daemon backend는 `model`, `device`, `compute_type`으로 정의되는 load-time config 단위로 socket을 나눈다. 같은 load-time config는 같은 daemon을 재사용하고, `language`, `beam_size`, `initial_prompt`, `vad_filter`는 request마다 전달한다. 한 daemon 안의 STT request는 GPU VRAM 중복 점유를 피하기 위해 명시 FIFO queue로 순차 처리한다.

Daemon request는 `request_id`, queue rank, queued/running/done/error 상태 metadata를 가진다. `type=stats` control-plane request는 transcription queue에 들어가지 않고 현재 running request, queued request count, active request count, own queue rank, idle timeout remaining을 반환한다. Wrapper는 daemon transcription 응답을 기다리는 동안에만 stats를 polling하고, idle/녹음 중/삽입 완료 상태에서는 polling하지 않는다.

Daemon backend 사용 중 하단 status bar는 queue 상태를 사용자-facing 문구로 표시한다.

```text
STT daemon starting | wait
STT queued 2/4 | wait
STT queued 1/3 | next
STT running | wait
STT transcribing | queue unknown
```

Daemon은 active transcription request가 없고 마지막 transcription request 완료 후 기본 `600s`가 지나면 종료한다. Stats request는 transcription queue에 들어가지 않고 idle timeout 기준도 연장하지 않는다. 종료하면 socket이 제거되고 loaded model과 VRAM 점유도 해제된다.

STT launcher는 `STT_PYTHON_BIN`을 명시하면 그 Python을 최우선으로 사용한다. 명시값이 없으면 현재 worktree의 `.venv`를 먼저 찾고, 없으면 `git worktree` 기준 main/primary worktree의 `.venv`를 fallback으로 사용한다. 따라서 issue worktree에서 실행해도 main workspace의 준비된 venv를 재사용할 수 있다.

legacy hold trigger mode와 release gap을 직접 지정:

```bash
scripts/stt_codex.py --trigger-mode hold --release-gap 0.75
```

기본 trigger mode는 `tap`이다. `Ctrl+T` 첫 tap은 녹음을 시작하고, 다음 tap은 녹음을 종료한다. `--release-gap`은 `--trigger-mode hold`에서만 trigger 반복 입력 종료 판정에 사용한다.

우선순위는 CLI 인자, 환경변수, 기본값 순서다.

```bash
scripts/stt_codex.py --trigger-mode hold --release-gap 0.5
STT_TRIGGER_MODE=hold STT_PTT_RELEASE_GAP=0.5 scripts/stt_codex.py
```

Migration note: `--ptt-profile`과 `STT_PTT_PROFILE`은 더 이상 설정 surface가 아니다. 이전 hold/repeat UX가 필요하면 `--trigger-mode hold`를 명시한다. 이전 `speed` 값은 hold mode 기본값 `0.35s`와 같다. 이전 `accuracy` 값이 필요하면 `--trigger-mode hold --release-gap 0.75` 또는 `STT_TRIGGER_MODE=hold STT_PTT_RELEASE_GAP=0.75`를 사용한다.

### Speed/Accuracy Decision Surface

기본값은 `--trigger-mode tap`, `--stt-backend daemon`, `--audio-handoff auto`,
`--stt-beam-size 5`, VAD on 기준이다. 기본 실행은 load-time config 단위 daemon에서 model을
공유하고, 저장/debug option이 꺼진 경우 buffer handoff를 사용한다. legacy hold
mode가 필요할 때만 `--trigger-mode hold`와 `--release-gap`을 명시한다.

| 선택 | 현재 command/config | latency evidence | accuracy evidence | 결정 |
| --- | --- | ---: | ---: | --- |
| 기본 runtime | 생략 | tap stop, #49 CUDA smoke cold `8.043s`, warm `1.035s` | transcript 품질은 backend 변경으로 직접 개선하지 않음 | 기본값 |
| legacy hold wait | `--trigger-mode hold --release-gap 0.75` | stop-wait `0.35s -> 0.75s`, deterministic delta `+0.40s` | live truncation 미측정 | opt-in |
| worker file | `--stt-backend worker --audio-handoff file` | fixed smoke avg `2.619s`, #29 subprocess `5.956s` 대비 `-3.337s` | score `0.6423`, normalized CER `0.3156` | worker fallback |
| worker buffer | `--stt-backend worker --audio-handoff buffer` | fixed smoke avg `2.536s`, #29 대비 `-3.420s`, worker file 대비 `-0.083s` | score `0.6423`, normalized CER `0.3156` | worker fallback |
| beam5 VAD on | `--stt-beam-size 5`, VAD on | fixed smoke avg `5.191s` | score `0.6423`, normalized CER `0.3156` | beam/VAD 기본값 |
| beam1 VAD on | `--stt-beam-size 1` | avg `5.173s`, `beam5-vad-on` `5.191s` 대비 `-0.018s`, #29 대비 `-0.783s` | score `0.6423`, normalized CER `0.3156` | fixed-smoke-only 후보 |
| VAD off | `--stt-no-vad-filter` | avg `5.334s`/`5.111s` | score `0.6233`, normalized CER `0.3394`, `cmd-0002` floor 실패 | 제외 |

Fixed smoke latency input은 `evals/inputs/speech/v1`의 `cmd-0002`, `cmd-0018`,
`cmd-0021`, `cmd-0024`다. 이 결과는 full suite 측정이 아니다. Worker file/buffer
latency는 persistent worker request wall time이며 live `arecord` stop latency,
child PTY injection latency, terminal render latency를 포함하지 않는다.

### Option Taxonomy

STT wrapper option은 profile로 묶지 않는다. 각 option은 바꾸는 계층이 다르다.

| 분류 | options | 의미 |
| --- | --- | --- |
| load-time | `--stt-model`, `--stt-device`, `--stt-compute-type`, `--stt-backend`, `--stt-daemon-socket-dir`, `--stt-daemon-idle-timeout`, `--stt-daemon-start-timeout` | model load와 실행 process 수명에 영향을 준다. 기본 backend는 `daemon`이다. |
| decode-time | `--stt-beam-size`, `--stt-no-vad-filter`, `--stt-initial-prompt`, `--stt-language` | 같은 audio를 transcript로 바꾸는 STT decoding 정책이다. |
| runtime/backend | `--trigger-mode`, `--release-gap`, `--min-duration`, `--max-duration`, `--audio-handoff` | 녹음 stop 판정, 녹음 길이 guard, audio 전달 방식을 바꾼다. |
| artifact/debug | `--save-run`, `--keep-audio`, `--run-output-dir`, `--temp-dir` | 저장과 debugging 산출물 정책이다. |

`--trigger-mode tap`이 기본 stop timing 정책이다. `--release-gap`은 legacy hold mode의 runtime stop timing option이다. daemon backend와 buffer handoff는
공통 runtime 기본값이다. beam/VAD와 model option은 별도 decode/load-time 정책이다.

#28 closeout의 최종 latency/accuracy 요약 위치는 이 section과
`scripts/README.md`의 `Speed/Accuracy Tradeoff Summary`다. 세부 evidence report는
`evals/stt_accuracy/reports/2026-06-23-buffer-handoff.md`,
`evals/stt_accuracy/reports/2026-06-23-release-gap-speed-profile.md`,
`evals/stt_accuracy/reports/2026-06-23-beam-vad-tradeoff.md`에 둔다. Report와
local-only run artifact의 소유권은 `evals/stt_accuracy/reports/2026-06-21-governance.md`
와 `evals/stt_accuracy/reports/README.md`를 따른다.

실행 후 사용자는 `Ctrl+T`를 한 번 눌러 녹음을 시작하고, 말을 끝낸 뒤 `Ctrl+T`를 다시 한 번 눌러 녹음을 종료한다. wrapper는 STT raw transcript를 Codex CLI 입력창에 삽입한다. Enter는 사용자가 직접 누른다.

실제 발화 audio와 transcript를 남겨 비교해야 할 때만 저장 option을 켠다.

```bash
scripts/stt_codex.py --save-run --stt-model large-v3 --stt-device cuda --stt-compute-type float16
```

저장 결과는 `output/runs/YYYYMMDD-HHMMSS-mmm-stt-codex/` 아래에 남는다.

## Pre-E2E Verification

E2E 전에 확인할 수 있는 비마이크 검증:

```bash
python3 -m py_compile scripts/stt_codex.py
scripts/stt_codex.py --help
```

한국어 fixture regression:

```bash
scripts/run_fixture_suite.sh fixtures/kss-ko-core-v1.json --model large-v3 --device cuda --compute-type float16
```

현재 기준 결과:

- PASS 6/6.
- exact 5/6.
- normalized 6/6.
- output: `output/suite/kss-ko-core-v1-large-v3-cuda-float16.json`.

한영 혼합 accuracy risk 측정:

```bash
scripts/run_fixture_suite.sh fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --compute-type float16 --require none
scripts/analyze_code_switch_suite.py output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
```

현재 기준 결과:

- exact 0/5.
- normalized 0/5.
- Latin token preservation 14/28, 50%.
- output: `output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json`.

Wrapper smoke test:

```bash
scripts/stt_codex.py --stt-model tiny --stt-device cpu --stt-compute-type int8 --cmd python3 -- -q
```

이 smoke test는 wrapper 실행, child PTY, trigger 처리, STT 호출, empty transcript skip, 임시 audio 삭제를 확인한다. 실제 발화 품질은 확인하지 않는다.

## Current Limits

- 실제 마이크 입력 품질이 낮으면 STT 결과가 크게 나빠진다. 장비 교체 후 `--save-run`으로 audio와 transcript를 같이 확인한다.
- 기본 `Ctrl+T` tap trigger는 child PTY로 전달되지 않고 parent wrapper가 소비한다. tmux나 terminal 설정에 따라 control sequence가 예상과 다를 수 있다.
- `--inject-key t`는 smoke test에 유용하지만 일반 typing과 충돌하므로 기본값으로 쓰지 않는다.
- legacy hold mode의 기본 release gap `0.35s`는 stop 판정을 빠르게 한다. hold/repeat UX가 필요하고 더 긴 대기가 필요하면 `--trigger-mode hold --release-gap 0.75`처럼 직접 지정한다.
- 한영 혼합 문장에서 `session`, `bug`, 파일명, option name 같은 Latin token이 한글 외래어 표기로 바뀔 수 있다.
- wrapper 기본 흐름은 token recovery, personal vocabulary, workspace metadata 기반 복원을 수행하지 않는다.
- STT 실행 중에는 wrapper event loop가 잠시 block될 수 있다.
- Buffer handoff는 기본 daemon request path다. file handoff가 필요하면 `--audio-handoff file`, `--save-run`, `--keep-audio` 중 하나를 명시한다.
- `--save-run`은 실제 발화 audio와 transcript를 파일로 남긴다. 외부 공유 전 `output/` 확인이 필요하다.

## E2E Test Gate

E2E는 사용자가 실제 장비로 발화한 뒤 확인한다.

통과 기준:

- `scripts/stt_codex.py`가 Codex CLI를 child PTY로 실행한다.
- 사용자가 `Ctrl+T`로 녹음을 시작하면 `recording 중` 상태가 표시되고, 다시 `Ctrl+T`를 누르면 recording stop이 표시된다.
- STT raw transcript가 Codex CLI 입력창에 삽입된다.
- Enter는 자동 전송되지 않는다.
- 사용자가 삽입된 문장을 수정하거나 그대로 Enter로 전송할 수 있다.
- 기본 실행에서는 audio와 transcript가 영구 저장되지 않는다.
- `--save-run`을 켠 경우에만 `output/runs/`에 run artifact가 남는다.

## Local Baseline Snapshot

2026-06-19 local baseline snapshot:

- OS: Ubuntu Linux, x86_64.
- CPU: AMD Ryzen 5 5600H, 6 cores / 12 threads.
- RAM: 13GiB.
- GPU: NVIDIA GeForce RTX 3050 Mobile, 4GiB VRAM, CUDA 12.2 driver available.
- 내장 GPU: AMD Radeon Vega Mobile.
- Audio capture: ALSA `arecord` 사용 가능, `HD-Audio Generic ALC257 Analog` capture device 확인.
- Clipboard: `xclip` 사용 가능.
- 미설치: `pactl`, `wl-copy`, `sox`.
- Python: 3.12.3.
- 로컬 STT 런타임: `.venv`에 `faster-whisper==1.2.1` 설치 확인.
- 로컬 STT 모델: `Systran/faster-whisper-tiny` 다운로드 확인.
- 정확도 기준 모델: `large-v3` CUDA `float16` 실행 확인. CUDA 실행에는 `requirements-cuda.txt` 설치 필요.
- 한영 혼합 기준: HiKE code-switching suite에서 Latin-script token 보존율 50% 확인. 일반 문장의 외래어 표기 전환은 자연스러울 수 있으나, 파일명/옵션명/코드 식별자 문맥의 복원은 wrapper 기본 흐름의 소유 책임이 아니다.

## Current Capability Surface

- Microphone recording: `scripts/record.sh`, `scripts/record_clipboard.sh`, `scripts/push_to_talk.py`, `scripts/stt_codex.py`.
- Local STT conversion: `scripts/transcribe.sh`, `scripts/transcribe.py`, `scripts/transcribe_worker.sh`, `scripts/transcribe_worker.py`.
- Fixture regression: `scripts/run_fixture_suite.sh`, `scripts/run_fixture_suite.py`, `scripts/compare_transcript.py`, `scripts/analyze_code_switch_suite.py`.
- Clipboard helper flow: `scripts/copy_text.sh`, `scripts/stt_clipboard.sh`, `scripts/record_clipboard.sh`.
- Manual token recovery script: `scripts/recover_tokens.py`.
- Codex child PTY wrapper: `scripts/stt_codex.py`.
- Optional run artifact save: `scripts/stt_codex.py --save-run`.

## Input Modes

- Raw mode: repo context 없이 STT 결과를 그대로 Codex CLI 입력창에 삽입한다. wrapper 기본 mode다.
- Manual recovery mode: `scripts/recover_tokens.py`가 수동 memory JSON으로 transcript token을 복원한다.
- Clipboard mode: `scripts/stt_clipboard.sh`와 `scripts/record_clipboard.sh`가 변환 결과를 clipboard에 복사한다.
- Wrapper STT mode: `scripts/stt_codex.py`가 `Ctrl+T` 녹음, STT 변환, child PTY 삽입을 처리한다.

## Current Behavior Contract

- Linux 데스크탑에서 wrapper를 실행한다.
- wrapper 안에서 Codex CLI가 child PTY로 실행된다.
- 사용자가 `Ctrl+T`를 한 번 눌러 녹음을 시작하고 다시 눌러 종료하면 로컬 STT가 transcript를 만든다.
- 변환 결과가 Codex CLI 입력창에 삽입된다.
- 사용자가 삽입된 텍스트를 확인하고 직접 전송한다.
- 정답 transcript가 있는 fixture WAV로 STT 변환 회귀 확인이 가능하다.
- 한국어와 한영 혼합 명령의 실험 결과는 `experiments/`에 기록한다.
- 자동 전송 없이 사용자의 확인 단계를 유지한다.
- 녹음본과 transcript는 기본적으로 영구 저장하지 않는다.
- 명시적 저장 옵션을 켰을 때만 run artifact를 남긴다.
- raw 입력 mode와 manual token recovery script는 서로 분리되어 있다.
- 기본 STT backend는 daemon이다. 같은 load-time config의 여러 wrapper가 하나의 loaded model을 공유한다. wrapper-local worker가 필요하면 `scripts/stt_codex.py --stt-backend worker`를 명시하고, 이전 subprocess path가 필요하면 `scripts/stt_codex.py --stt-backend subprocess`를 명시한다.
- STT launcher는 현재 worktree `.venv`가 없으면 main/primary worktree `.venv`를 자동 fallback으로 사용한다.

## Repository Shape

- `scripts/`: Codex PTY wrapper, 녹음, STT, fixture 검증, clipboard helper 스크립트.
- `stt_core/`: 실행환경과 무관한 순수 판단과 data contract.
- `stt_runtime/`: OS, subprocess, PTY, terminal, filesystem side-effect adapter.
- `stt_features/`: 사용자-facing STT 입력 보조 flow 조립.
- `memory/`: 수동 token recovery memory 예시와 계약.
- `experiments/`: 모델, 녹음 방식, 단축키 UX 실험 기록.
- `output/`: 명시적으로 저장한 로컬 실행 결과물. 기본적으로 Git 추적 제외.
- `.codex/skills/task-system/`: task 운영 계약 reference.
- `.codex/skills/task-commit/`: 한국어 topic commit helper.

## Current Non-Scope

- Codex CLI 수정.
- STT 결과 자동 전송.
- token recovery 기본 적용.
- workspace metadata 기반 자동 복원.
