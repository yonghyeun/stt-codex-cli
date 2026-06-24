# Repository Agent Routing

이 repo는 Codex CLI용 로컬 STT 입력 보조 도구 실험 workspace다.

기준 경로는 repo root `.`이다.
문서, 명령, 스크립트 예시는 parent directory 이름에 의존하지 않는다.

## 읽기 순서

1. 이 `AGENTS.md`를 읽는다.
2. 변경 파일이 속한 영역의 README 또는 인접 문서를 읽는다.
3. `.codex/**` 변경이면 `.codex/AGENTS.md`를 읽는다.

## Routing

| 변경 경로 | 반드시 읽을 문서 | 목적 |
| --- | --- | --- |
| `.codex/**` | `.codex/AGENTS.md` | repo-local skill과 task 계약 규칙 |
| `.github/**` | `.github/README.md` | issue/PR template 규칙 |
| `stt_core/**` | `stt_core/README.md` | 순수 판단과 data contract 소유권 |
| `stt_runtime/**` | `stt_runtime/README.md` | OS, subprocess, PTY, file write adapter 경계 |
| `stt_features/**` | `stt_features/README.md` | 사용자 use-case flow 조립 경계 |
| `scripts/**` | `README.md` | STT 실행 스크립트 경계 |
| `evals/**` | `evals/README.md` | 평가 트랙, suite, report 계약 |
| `fixtures/**` | `fixtures/README.md` | legacy fixture와 reference suite 경계 |
| `experiments/**` | `README.md` | 실험 기록 경계 |
| `output/**` | `README.md` | wrapper 로컬 산출물 경계 |

## 작업 경계

- 실험은 작은 commit 단위로 나눈다.
- 기본값에서는 STT 결과를 Codex CLI에 자동 전송하지 않는다.
- 자동 전송은 명시 opt-in 실험 기능으로만 다룬다.
- 현재 1차 UX는 Codex CLI child PTY 입력창에 STT raw transcript를 삽입하는 흐름이다.
- 오인식 가능성이 있는 문장은 사용자가 확인 후 전송한다.
- GitHub 원격 계약은 `origin`과 repo-local task lifecycle skill로 관리한다.
- issue/PR 생성, closeout, merge 자동화는 `.codex/skills/task-*`와
  `.codex/skills/risk-*`를 통해서만 수행한다.
- GitHub mutation skill은 항상 dry-run을 먼저 실행하고, 실제 mutation에는
  `--yes` 같은 명시 확인 인자를 사용한다.
