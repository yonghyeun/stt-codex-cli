from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "scripts/stt_python_env.sh"


class SttPythonEnvLauncherTest(unittest.TestCase):
    def test_resolves_main_worktree_venv_when_current_worktree_has_no_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            issue_worktree = root / "issue-worktree"
            main_worktree = root / "main-worktree"
            fake_bin_dir = root / "bin"
            fake_python = main_worktree / ".venv/bin/python"
            site_packages = main_worktree / ".venv/lib/python3.12/site-packages"

            issue_worktree.mkdir()
            site_packages.mkdir(parents=True)
            fake_python.parent.mkdir(parents=True, exist_ok=True)
            fake_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake_python.chmod(0o755)

            fake_git = fake_bin_dir / "git"
            fake_bin_dir.mkdir()
            fake_git.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    cat <<EOF
                    worktree ${FAKE_MAIN_WORKTREE}
                    HEAD abc
                    branch refs/heads/main

                    worktree ${FAKE_ISSUE_WORKTREE}
                    HEAD def
                    branch refs/heads/refactor/issue
                    EOF
                    """
                ),
                encoding="utf-8",
            )
            fake_git.chmod(0o755)

            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        f"source {HELPER}; "
                        'resolve_stt_python_env "$TEST_REPO_ROOT"; '
                        'printf "%s\\n%s\\n" '
                        '"$STT_RESOLVED_PYTHON_BIN" '
                        '"$STT_RESOLVED_SITE_PACKAGES"'
                    ),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    "PATH": f"{fake_bin_dir}:{os.environ['PATH']}",
                    "TEST_REPO_ROOT": str(issue_worktree),
                    "FAKE_MAIN_WORKTREE": str(main_worktree),
                    "FAKE_ISSUE_WORKTREE": str(issue_worktree),
                },
            )

            self.assertEqual(
                result.stdout.splitlines(),
                [str(fake_python), str(site_packages)],
            )

    def test_explicit_python_env_still_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = root / "repo"
            explicit_python = root / "custom-venv/bin/python"
            explicit_site_packages = root / "custom-site-packages"

            repo_root.mkdir()
            explicit_python.parent.mkdir(parents=True)
            explicit_site_packages.mkdir()
            explicit_python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            explicit_python.chmod(0o755)

            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        f"source {HELPER}; "
                        'resolve_stt_python_env "$TEST_REPO_ROOT"; '
                        'printf "%s\\n%s\\n" '
                        '"$STT_RESOLVED_PYTHON_BIN" '
                        '"$STT_RESOLVED_SITE_PACKAGES"'
                    ),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    "TEST_REPO_ROOT": str(repo_root),
                    "STT_PYTHON_BIN": str(explicit_python),
                    "STT_SITE_PACKAGES": str(explicit_site_packages),
                },
            )

            self.assertEqual(
                result.stdout.splitlines(),
                [str(explicit_python), str(explicit_site_packages)],
            )


if __name__ == "__main__":
    unittest.main()
