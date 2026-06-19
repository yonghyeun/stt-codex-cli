# STT Codex CLI

Linux에서 Codex CLI 입력을 보조하기 위한 로컬 STT 실험 workspace.

## Root

- 이 repo의 기준 경로는 `.`이다.
- 모든 명령과 문서 경로는 repo root `.` 기준으로 작성한다.
- 특정 parent directory 이름에 의존하지 않는다.

## Goal

- 마이크 입력을 텍스트로 변환한다.
- 변환 결과를 클립보드에 복사한다.
- Codex CLI에는 사용자가 직접 붙여넣고 확인 후 전송한다.

## Product Contract

최종 산출물은 Linux 데스크탑에서 사용자가 키를 누르고 말하면 로컬 STT 모델이 음성을 텍스트로 변환하고, 변환 결과를 클립보드에 복사하는 Codex CLI 입력 보조 도구다.

사용자는 복사된 텍스트를 Codex CLI에 직접 붙여넣고, 오인식 여부를 확인한 뒤 전송한다.

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
- 결과 전달은 클립보드 복사까지로 제한한다.
- Codex CLI 자동 전송은 하지 않는다.

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
- Python: 3.12.3.
- 로컬 STT 런타임: `.venv`에 `faster-whisper==1.2.1` 설치 확인.
- 로컬 STT 모델: 초기 조사 시 Whisper/Hugging Face/faster-whisper/whisperx 캐시 또는 설치본 없음. Prototype 2 smoke test로 `Systran/faster-whisper-tiny` 다운로드 확인.

첫 프로토타입은 녹음 파일 생성까지만 다룬다. 누르고 말하기 UX는 녹음 안정성 확인 후 별도 프로토타입에서 다룬다.

## Prototype Roadmap

1. 마이크 입력을 녹음 파일로 저장한다.
2. 로컬 STT 모델 후보를 하나 붙여 텍스트 변환을 확인한다.
3. 정답 transcript가 있는 fixture WAV로 재현 가능한 변환 실험을 만든다.
4. 한국어와 한영 혼합 문장의 정확도 실험을 기록한다.
5. 변환 결과를 클립보드에 복사한다.
6. 누르고 말하기 방식의 입력 UX를 만든다.
7. 녹음, STT, 클립보드 복사를 하나의 명령으로 묶는다.
8. 실제 Codex CLI 입력 흐름에서 반복 사용성을 검증한다.
9. 정확도, 오인식 사례, 처리 시간을 기준으로 모델과 UX를 조정한다.

## Closeout Criteria

- Linux 데스크탑에서 한 명령 또는 한 단축키 흐름으로 실행 가능하다.
- 사용자가 누르고 말한 문장이 로컬 STT로 텍스트화된다.
- 변환 결과가 클립보드에 복사된다.
- 사용자가 Codex CLI에 직접 붙여넣고 확인 후 전송할 수 있다.
- 정답 transcript가 있는 fixture WAV로 STT 변환 회귀 확인이 가능하다.
- 한국어와 한영 혼합 명령의 실험 결과가 `experiments/`에 기록되어 있다.
- 알려진 오인식 사례와 회피 방법이 문서화되어 있다.
- 자동 전송 없이 사용자의 확인 단계를 유지한다.

## Initial Shape

- `scripts/`: 녹음, STT, 클립보드 복사 스크립트.
- `experiments/`: 모델, 녹음 방식, 단축키 UX 실험 기록.
- `output/`: 로컬 실행 결과물. 기본적으로 Git 추적 제외.
- `.github/ISSUE_TEMPLATE/`: repo task issue template.
- `.codex/skills/task-system/`: task 운영 계약 reference.
- `.codex/skills/task-commit/`: 한국어 topic commit helper.

## Current Non-Scope

- Codex CLI 수정.
- STT 결과 자동 전송.
- GitHub issue/PR 생성/merge 자동화.
- 원격 repo label/issue 계약 확정.
