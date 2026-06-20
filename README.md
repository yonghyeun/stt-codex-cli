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

최종 산출물은 Linux 데스크탑에서 사용자가 wrapper를 실행하면 그 안에서 Codex CLI가 child PTY로 구동되고, 사용자가 키를 누르고 말하면 로컬 STT 모델이 음성을 텍스트로 변환해 Codex CLI 입력창에 삽입하는 입력 보조 도구다.

사용자는 삽입된 텍스트를 직접 확인하고 필요한 경우 수정한 뒤 Enter로 전송한다.

이 도구는 repo 전용 도구가 아니라 일반 terminal coding agent 입력 보조 도구로 확장 가능해야 한다. 초기 구현 대상은 Codex CLI다.

녹음본과 transcript는 기본적으로 영구 저장하지 않는다. STT 처리에는 임시 WAV 파일을 사용할 수 있지만, 처리가 끝나면 삭제한다. 사용자가 명시적으로 저장 옵션을 켠 경우에만 `output/runs/` 아래에 audio, transcript, metadata를 남긴다.

## Architecture

이 section은 현재 구조의 기준 문서다. 앞으로 아키텍처 변화나 주요 구조 업데이트가 생기면 이 section을 함께 수정한다.

현재 핵심 구조:

```text
terminal
  -> npm run stt-codex -- parent wrapper
    -> src/app/cli/stt-codex.ts
    -> child PTY: codex --no-alt-screen
    -> parent status: [stt-parent] prefix
    -> push-to-talk controller: ctrl+t
    -> temporary audio recorder: arecord
    -> local STT engine: src/features/stt-engine -> nodejs-whisper package -> whisper.cpp CLI
    -> raw transcript injector: child PTY input buffer
```

Runtime flow:

```text
사용자 실행
  -> npm run stt-codex --
  -> Codex CLI child PTY 시작
  -> 사용자가 Ctrl+T를 누르고 말함
  -> TypeScript parent wrapper가 임시 WAV 녹음
  -> Ctrl+T 반복 입력이 끊기면 녹음 종료
  -> TypeScript STT engine이 whisper.cpp로 STT 변환
  -> raw transcript를 Codex 입력창에 삽입
  -> 사용자가 확인 후 Enter
```

Boundary:

- Parent wrapper는 `[stt-parent]` prefix로 상태를 출력한다.
- Child Codex output은 변형하지 않는다.
- 기본 Codex 실행에는 `--no-alt-screen`을 붙여 parent/child 경계가 scrollback에 남게 한다.
- STT 결과는 child PTY에 텍스트로만 삽입한다.
- Enter는 자동으로 보내지 않는다.

Storage:

- 녹음은 STT 처리를 위해 임시 WAV 파일로 만든다.
- 임시 WAV는 기본 삭제한다.
- `--save-run`을 명시한 경우에만 `output/runs/YYYYMMDD-HHMMSS-mmm-stt-codex/` 아래에 audio, transcript, metadata를 보존한다.
- `--keep-audio`는 임시 WAV 자체를 남기는 debug option이다.
- `output/`은 명시 저장 결과만 담는 위치다.

Current primary TypeScript commands:

- `npm run stt-codex --`: 현재 메인 entrypoint. Codex child PTY, PTT, STT, transcript injection을 담당한다.
- `npm run transcribe --`: nodejs-whisper package의 whisper.cpp CLI를 호출하는 TypeScript STT command다.
- `npm run record --`: `arecord` 기반 WAV 녹음 command다.
- `npm run stt-clipboard --`: audio file -> STT -> token recovery -> clipboard 흐름이다.
- `npm run record-clipboard --`: microphone record -> STT clipboard 흐름이다.
- `npm run push-to-talk --`: standalone push-to-talk prototype command다.
- `npm run recover-tokens --`, `npm run compare-transcript --`, `npm run analyze-code-switch-suite --`: deterministic helper command다.
- `npm run fetch-kss-fixture --`, `npm run fetch-hike-fixture --`: fixture download command다.

Compatibility boundary:

- `scripts/*.sh`: 이전 경로 호환성을 위한 wrapper다. 내부 구현은 `npm run ...` TypeScript command로 전달한다.
- `scripts/`에는 Python product script나 Python adapter를 두지 않는다.
- STT model cache 기본 위치는 `output/models/whisper.cpp`다.

Current TypeScript surface:

- `src/README.md`: TypeScript source layout와 포팅 계약이다.
- `docs/typescript-porting.md`: TypeScript primary flow와 Node STT engine 경계를 정의한다.
- `src/features/transcript-comparison`: transcript 비교 순수 로직이다.
- `src/features/token-recovery`, `src/features/code-switch-analysis`, `src/features/audio-recording`, `src/features/clipboard`, `src/features/stt-engine`, `src/features/codex-pty`: 포팅된 기능 로직이다.
- `src/app/cli/*.ts`: 사용자-facing TypeScript command다.

Deferred architecture:

- token recovery는 기본 흐름에서 제외한다.
- workspace metadata 기반 복원은 후속 기능이다.
- clipboard 전달 흐름은 이전 prototype으로 유지하되 최종 방향은 child PTY injection이다.
- OpenCode 같은 다른 terminal coding agent 지원은 후속 일반화 대상이다.

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
- 입력 방식은 누르고 말하기 방식으로 우선 결정한다.
- 결과 전달은 child PTY에 텍스트를 삽입하는 방식으로 진행한다.
- Codex CLI 자동 전송은 하지 않는다. Enter는 사용자가 직접 입력한다.

## Current Usage

기본 실행:

```bash
npm run stt-codex --
```

정확도 기준 모델을 명시:

```bash
npm run stt-codex -- --stt-model large-v3 --stt-device cuda
```

실행 후 사용자는 `Ctrl+T`를 누르고 말한다. `Ctrl+T` 반복 입력이 끊기면 wrapper가 녹음을 종료하고 STT raw transcript를 Codex CLI 입력창에 삽입한다. Enter는 사용자가 직접 누른다.

실제 발화 audio와 transcript를 남겨 비교해야 할 때만 저장 option을 켠다.

```bash
npm run stt-codex -- --save-run --stt-model large-v3 --stt-device cuda
```

저장 결과는 `output/runs/YYYYMMDD-HHMMSS-mmm-stt-codex/` 아래에 남는다.

## TypeScript Development

설치:

```bash
npm install
```

검증:

```bash
npm test
npm run typecheck
npm run lint
npm run format:check
```

TS 주요 CLI:

```bash
npm run stt-codex -- --help
npm run transcribe -- audio.wav --model tiny --device cpu
npm run recover-tokens -- --fixture fixtures/token-recovery-v1.json
npm run compare-transcript -- expected.txt actual.txt
npm run compare-transcript -- --exact expected.txt actual.txt
npm run analyze-code-switch-suite -- output/suite/hike-code-switch-core-v1-large-v3-cuda-float16.json
```

현재 primary orchestration과 STT 실행 경계는 TypeScript다.

STT engine 기준:

- npm dependency: `nodejs-whisper`.
- 내부 실행기: `node_modules/nodejs-whisper/cpp/whisper.cpp`의 `whisper-cli`.
- model cache 기본 위치: `output/models/whisper.cpp`.
- 기본 model: `large-v3`.
- `--stt-device cuda`는 whisper.cpp를 `-DGGML_CUDA=1`로 build한다.
- `--stt-compute-type`은 기존 CLI 호환용 option이며 whisper.cpp engine에서는 직접 사용하지 않는다.
- VAD는 `--vad-model` 또는 `STT_VAD_MODEL`이 지정된 경우에만 whisper.cpp `--vad`로 전달한다.

## Pre-E2E Verification

E2E 전에 확인할 수 있는 비마이크 검증:

```bash
npm test
npm run typecheck
npm run lint
npm run format:check
npm run stt-codex -- --help
npm run stt-codex -- --inject-mode fixed-text --disable-inject-key --cmd node -- --eval 'console.log("ts-pty-smoke")'
```

한국어 fixture regression:

```bash
npm run run-fixture-suite -- fixtures/kss-ko-core-v1.json --model large-v3 --device cuda
```

현재 기준 결과:

- Node STT engine 전환 후 재측정 필요.
- 현재 worktree에는 `fixtures/generated/` audio가 없어 즉시 재실행하지 않았다.

한영 혼합 accuracy risk 측정:

```bash
npm run run-fixture-suite -- fixtures/hike-code-switch-core-v1.json --model large-v3 --device cuda --require none
npm run analyze-code-switch-suite -- output/suite/hike-code-switch-core-v1-typescript-engine.json
```

현재 기준 결과:

- Node STT engine 전환 후 재측정 필요.
- 현재 worktree에는 `fixtures/generated/` audio가 없어 즉시 재실행하지 않았다.

Wrapper smoke test:

```bash
npm run stt-codex -- --stt-model tiny --stt-device cpu --cmd node -- -i
```

이 smoke test는 wrapper 실행, child PTY, trigger 처리, STT 호출, empty transcript skip, 임시 audio 삭제를 확인한다. 실제 발화 품질은 확인하지 않는다.

## Known Issues

- 실제 마이크 입력 품질이 낮으면 STT 결과가 크게 나빠진다. 장비 교체 후 `--save-run`으로 audio와 transcript를 같이 확인한다.
- `Ctrl+T` PTT는 terminal key repeat에 의존한다. tmux나 terminal 설정에 따라 control sequence가 예상과 다를 수 있다.
- `--inject-key t`는 smoke test에 유용하지만 일반 typing과 충돌하므로 기본값으로 쓰지 않는다.
- 한영 혼합 문장에서 `session`, `bug`, 파일명, option name 같은 Latin token이 한글 외래어 표기로 바뀔 수 있다.
- token recovery, personal vocabulary, workspace metadata 기반 복원은 후속 기능이다.
- STT 실행 중에는 wrapper event loop가 잠시 block될 수 있다.
- `--save-run`은 실제 발화 audio와 transcript를 파일로 남긴다. 외부 공유 전 `output/` 확인이 필요하다.

## E2E Test Gate

E2E는 사용자가 실제 장비로 발화한 뒤 확인한다.

통과 기준:

- `npm run stt-codex --`가 Codex CLI를 child PTY로 실행한다.
- 사용자가 `Ctrl+T`를 누르고 말하면 recording start/stop이 표시된다.
- STT raw transcript가 Codex CLI 입력창에 삽입된다.
- Enter는 자동 전송되지 않는다.
- 사용자가 삽입된 문장을 수정하거나 그대로 Enter로 전송할 수 있다.
- 기본 실행에서는 audio와 transcript가 영구 저장되지 않는다.
- `--save-run`을 켠 경우에만 `output/runs/`에 run artifact가 남는다.

## Local Baseline

2026-06-19 현재 확인한 로컬 기준:

- OS: Ubuntu Linux, x86_64.
- CPU: AMD Ryzen 5 5600H, 6 cores / 12 threads.
- RAM: 13GiB.
- GPU: NVIDIA GeForce RTX 3050 Mobile, 4GiB VRAM, CUDA 12.2 driver available.
- 내장 GPU: AMD Radeon Vega Mobile.
- Audio capture: ALSA `arecord` 사용 가능, `HD-Audio Generic ALC257 Analog` capture device 확인.
- Clipboard: `xclip` 사용 가능.
- 미설치: `pactl`, `wl-copy`, `sox`.
- Node.js: v24.12.0.
- 로컬 STT runtime: npm dependency `nodejs-whisper`와 번들 `whisper.cpp` CLI.
- 로컬 STT model cache: `output/models/whisper.cpp`.
- 정확도 기준 모델: `large-v3`. CUDA 실행은 `--stt-device cuda`와 local CMake/CUDA build에 의존한다.
- 한영 혼합 기준: Node STT engine 전환 후 재측정 필요. 일반 문장의 외래어 표기 전환은 자연스러울 수 있으나, 파일명/옵션명/코드 식별자 문맥의 별도 복원은 후속 기능으로 둔다.

첫 프로토타입은 녹음 파일 생성까지만 다룬다. 누르고 말하기 UX는 녹음 안정성 확인 후 별도 프로토타입에서 다룬다.

## Prototype Roadmap

1. 마이크 입력을 녹음 파일로 저장한다.
2. 로컬 STT 모델 후보를 하나 붙여 텍스트 변환을 확인한다.
3. 정답 transcript가 있는 fixture WAV로 재현 가능한 변환 실험을 만든다.
4. 한국어와 한영 혼합 문장의 정확도 실험을 기록한다.
5. 일반 입력과 workspace 입력의 mode 계약을 분리한다.
6. 변환 결과를 클립보드에 복사한다.
7. 누르고 말하기 방식의 입력 UX를 만든다.
8. 녹음, STT, 클립보드 복사를 하나의 명령으로 묶는다.
9. 실제 Codex CLI 입력 흐름에서 반복 사용성을 검증한다.
10. 정확도, 오인식 사례, 처리 시간을 기준으로 모델과 UX를 조정한다.
11. Codex CLI를 child PTY로 실행하는 wrapper를 만든다.
12. wrapper에서 사용자 키 입력과 Codex 출력을 passthrough한다.
13. 고정 텍스트를 child PTY 입력창에 삽입해 자동 입력만 검증한다.
14. push-to-talk 녹음과 STT를 wrapper에 연결한다.
15. STT raw transcript를 Codex CLI 입력창에 삽입한다.
16. 임시 audio 기본 삭제와 선택 저장 옵션을 적용한다.

## Input Modes

- Raw mode: repo context 없이 STT 결과를 그대로 Codex CLI 입력창에 삽입한다. 기본 mode다.
- Recovery mode: 파일명, 옵션명, 코드 식별자 같은 token 복원을 수행한다. 후속 기능이다.
- Personal vocabulary mode: 사용자가 자주 쓰는 단어와 프로젝트명을 선택적으로 추가한다. 후속 기능이다.

초기 wrapper 흐름에서는 STT raw transcript만 사용한다. token recovery와 workspace metadata는 closeout 이후 후속 기능으로 둔다.

Phase 8 prototype은 자동 수집 이전 단계다. `memory/manual-aliases.example.json` 같은 수동 memory를 읽어 텍스트 transcript를 복원한다.

Phase 9 prototype은 텍스트를 clipboard에 복사한다. 현재 Linux 기준 backend는 `xclip`이며, 복사 후 clipboard 내용을 다시 읽어 검증한다.

Phase 10 prototype은 기존 audio 파일을 STT로 변환하고, token recovery를 거쳐 clipboard에 복사한다.

Phase 11 prototype은 정해진 시간 마이크를 녹음한 뒤 Phase 10 흐름으로 이어 clipboard에 복사한다. push-to-talk 입력 UX는 아직 후속 단계다.

Phase 12 prototype은 `t` 단독키 push-to-talk 입력을 추가한다. 사용자는 keycode와 modifier keycode를 바꿀 수 있다.

Phase 13 prototype은 Codex CLI를 child PTY로 실행하는 wrapper를 추가한다. 이 단계는 STT 없이 입출력 passthrough만 검증한다.

Phase 14 prototype은 wrapper에서 고정 텍스트를 Codex CLI 입력창에 삽입한다. 자동 전송은 하지 않는다.

Phase 15 prototype은 wrapper에서 push-to-talk 녹음과 STT raw transcript 삽입을 연결한다. 녹음본은 기본적으로 임시 파일로 처리하고 삭제한다.

Phase 16 prototype은 필요할 때만 audio와 transcript를 저장하는 옵션을 추가한다.

Phase 16의 저장 option은 `--save-run`이다. 저장 directory 이름은 `YYYYMMDD-HHMMSS-mmm-stt-codex` 형식이다. 같은 millisecond 충돌이 발생하면 `-001` 같은 suffix를 붙인다. 각 run directory에는 `audio.wav`, `transcript.txt`, `metadata.json`을 남긴다.

## Closeout Criteria

- Linux 데스크탑에서 한 명령 또는 한 단축키 흐름으로 실행 가능하다.
- wrapper 안에서 Codex CLI가 child PTY로 실행된다.
- 사용자가 누르고 말한 문장이 로컬 STT로 텍스트화된다.
- 변환 결과가 Codex CLI 입력창에 삽입된다.
- 사용자가 삽입된 텍스트를 확인하고 직접 전송할 수 있다.
- 정답 transcript가 있는 fixture WAV로 STT 변환 회귀 확인이 가능하다.
- 한국어와 한영 혼합 명령의 실험 결과가 `experiments/`에 기록되어 있다.
- 알려진 오인식 사례와 회피 방법이 문서화되어 있다.
- 자동 전송 없이 사용자의 확인 단계를 유지한다.
- 녹음본과 transcript는 기본적으로 영구 저장하지 않는다.
- 명시적 저장 옵션을 켰을 때만 run artifact를 남긴다.
- raw 입력 mode와 token recovery 후속 기능의 경계가 분리되어 있다.

## Initial Shape

- `scripts/`: Codex PTY wrapper, 녹음, STT, fixture 검증, 이전 clipboard prototype 스크립트.
- `memory/`: 수동 token recovery memory 예시와 계약. 후속 기능이다.
- `experiments/`: 모델, 녹음 방식, 단축키 UX 실험 기록.
- `output/`: 명시적으로 저장한 로컬 실행 결과물. 기본적으로 Git 추적 제외.
- `.github/ISSUE_TEMPLATE/`: repo task issue template.
- `.codex/skills/task-system/`: task 운영 계약 reference.
- `.codex/skills/task-commit/`: 한국어 topic commit helper.

## Current Non-Scope

- Codex CLI 수정.
- STT 결과 자동 전송.
- token recovery 기본 적용.
- workspace metadata 기반 자동 복원.
- GitHub issue/PR 생성/merge 자동화.
- 원격 repo label/issue 계약 확정.
