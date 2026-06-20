from __future__ import annotations

import os
import pty
import sys


def spawn_child(argv: list[str], cwd: str | None) -> tuple[int, int]:
    pid, child_fd = pty.fork()
    if pid == 0:
        try:
            if cwd is not None:
                os.chdir(cwd)
            os.execvp(argv[0], argv)
        except OSError as error:
            print(f"failed to exec {argv[0]}: {error}", file=sys.stderr)
            os._exit(127)
    return pid, child_fd


def decode_wait_status(status: int) -> int:
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return 1


def reap_child(pid: int) -> int | None:
    waited_pid, status = os.waitpid(pid, os.WNOHANG)
    if waited_pid == 0:
        return None
    return decode_wait_status(status)
