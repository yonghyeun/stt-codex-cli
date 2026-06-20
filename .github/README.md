# GitHub Repository Automation

이 폴더는 GitHub issue template, PR template, workflow를 담당한다.

## PR Template

- PR 작성자는 root `AGENTS.md`를 먼저 확인한다.
- 변경 경로가 root `AGENTS.md`에서 라우팅하는 README/AGENTS를 추가로 확인한다.
- README 규칙이 겹치면 변경 파일에 가장 가까운 README를 우선한다.
- 문서-only 변경으로 코드 테스트를 생략하면 PR template의 verification 항목에 사유를 남긴다.

## Codex Review

- Codex code review는 GitHub/OpenAI connector 설정에 맡긴다.
- 이 repo는 GitHub Actions로 `@codex review` 댓글을 자동 생성하지 않는다.
- 필요한 경우 maintainer가 PR comment에 `@codex review`를 수동으로 남긴다.
- Codex code review repository 설정은 GitHub/OpenAI product 설정이다. 이 repo에서는 강제하지 않고 PR template에 수동 fallback만 안내한다.
