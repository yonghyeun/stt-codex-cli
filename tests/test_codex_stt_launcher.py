from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "scripts/install_codex_stt_command.sh"


class CodexSttLauncherTest(unittest.TestCase):
    def test_launcher_preserves_invocation_cwd_for_child_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "bin/codex-stt"
            invocation_dir = root / "caller"
            invocation_dir.mkdir()

            subprocess.run(
                [
                    str(INSTALLER),
                    "--target",
                    str(target),
                    "--root",
                    str(REPO_ROOT),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            result = subprocess.run(
                [
                    str(target),
                    "--quiet-parent",
                    "--parent-panel",
                    "none",
                    "--cmd",
                    "pwd",
                ],
                cwd=invocation_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(result.stdout.strip(), str(invocation_dir))


if __name__ == "__main__":
    unittest.main()
