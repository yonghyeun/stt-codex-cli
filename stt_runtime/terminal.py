from __future__ import annotations

import fcntl
import sys
import termios
import tty
from pathlib import Path


class TerminalMode:
    def __init__(self) -> None:
        self.fd = sys.stdin.fileno()
        self.original_attrs: list[object] | None = None

    def __enter__(self) -> None:
        if sys.stdin.isatty():
            self.original_attrs = termios.tcgetattr(self.fd)
            tty.setraw(self.fd)

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if self.original_attrs is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.original_attrs)


def validate_cwd(raw_cwd: str | None) -> str | None:
    if raw_cwd is None:
        return None
    cwd = Path(raw_cwd).expanduser()
    if not cwd.exists():
        raise RuntimeError(f"cwd does not exist: {cwd}")
    if not cwd.is_dir():
        raise RuntimeError(f"cwd is not a directory: {cwd}")
    return str(cwd)


def copy_window_size(child_fd: int) -> None:
    if not sys.stdin.isatty():
        return
    try:
        size = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
        fcntl.ioctl(child_fd, termios.TIOCSWINSZ, size)
    except OSError:
        return
