from __future__ import annotations

import fcntl
import struct
import sys
import termios
import tty
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from stt_core.status import compact_parent_status


PARENT_PREFIX = "[stt-parent]"
TerminalSizeFn = Callable[[], tuple[int, int]]
ParentPanel = tuple[str, ...]


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


def current_terminal_size() -> tuple[int, int]:
    size = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
    rows, columns, _, _ = struct.unpack("HHHH", size)
    return rows, columns


def adjusted_child_size(
    rows: int,
    columns: int,
    *,
    reserved_rows: int = 0,
) -> tuple[int, int]:
    return max(1, rows - max(0, reserved_rows)), columns


def packed_window_size(
    *,
    rows: int,
    columns: int,
    reserved_rows: int = 0,
) -> bytes:
    child_rows, child_columns = adjusted_child_size(
        rows,
        columns,
        reserved_rows=reserved_rows,
    )
    return struct.pack("HHHH", child_rows, child_columns, 0, 0)


class TerminalStatusRenderer:
    def __init__(
        self,
        *,
        stream: TextIO = sys.stderr,
        enabled: bool = True,
        color: bool = True,
        debug: bool = False,
        interactive: bool | None = None,
        terminal_size: TerminalSizeFn = current_terminal_size,
        prefix: str = PARENT_PREFIX,
        parent_panel: ParentPanel = (),
    ) -> None:
        self.stream = stream
        self.enabled = enabled
        self.color = color
        self.debug = debug
        self.interactive = stream.isatty() if interactive is None else interactive
        self.terminal_size = terminal_size
        self.prefix = prefix
        self.parent_panel = tuple(parent_panel)
        if self.enabled and self.interactive and not self.debug:
            self.reserved_rows = len(self.parent_panel) + 1
        else:
            self.reserved_rows = 0

    def __call__(self, message: str) -> None:
        if not self.enabled:
            return
        if self.debug:
            self._write_debug_line(message)
            return
        compact = compact_parent_status(message)
        if compact is None:
            return
        self.set_status(compact.text)

    def render_parent_panel(self) -> None:
        if (
            not self.enabled
            or self.debug
            or not self.interactive
            or not self.parent_panel
        ):
            return
        try:
            rows, columns = self.terminal_size()
        except OSError:
            return
        rows = max(1, rows)
        visible_panel_rows = min(len(self.parent_panel), max(0, rows - 2))
        if visible_panel_rows == 0:
            self.stream.write("\033[1;1H")
            self.stream.flush()
            return
        for offset, line in enumerate(self.parent_panel[:visible_panel_rows], start=1):
            display = self._truncate(line, columns)
            self.stream.write(f"\033[{offset};1H\033[2K{display}")
        self.stream.write(f"\033[{visible_panel_rows + 1};1H")
        self.stream.flush()

    def set_status(self, text: str) -> None:
        if not self.enabled:
            return
        if self.debug:
            self._write_debug_line(text)
            return
        if self.interactive:
            self._write_interactive_status(text)
            return
        self.stream.write(f"{text}\n")
        self.stream.flush()

    def _write_debug_line(self, message: str) -> None:
        prefix = self.prefix
        if self.stream.isatty() and self.color:
            prefix = f"\033[36m{self.prefix}\033[0m"
        self.stream.write(f"{prefix} {message}\n")
        self.stream.flush()

    def _write_interactive_status(self, text: str) -> None:
        try:
            rows, columns = self.terminal_size()
        except OSError:
            self.stream.write(f"{text}\n")
            self.stream.flush()
            return
        rows = max(1, rows)
        display = self._truncate(text, columns)
        self.stream.write(f"\033[s\033[{rows};1H\033[2K{display}\033[u")
        self.stream.flush()

    def _truncate(self, text: str, columns: int) -> str:
        if columns <= 0 or len(text) <= columns:
            return text
        if columns <= 3:
            return text[:columns]
        return text[: columns - 3] + "..."


def copy_window_size(child_fd: int, *, reserved_rows: int = 0) -> None:
    if not sys.stdin.isatty():
        return
    try:
        rows, columns = current_terminal_size()
        size = packed_window_size(
            rows=rows,
            columns=columns,
            reserved_rows=reserved_rows,
        )
        fcntl.ioctl(child_fd, termios.TIOCSWINSZ, size)
    except OSError:
        return
