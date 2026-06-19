#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import fcntl
import os
import pty
import selectors
import signal
import sys
import termios
import tty
from pathlib import Path


DEFAULT_CMD = "codex"
PARENT_PREFIX = "[stt-parent]"
READ_SIZE = 4096


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Codex CLI inside a child PTY for future STT input injection."
    )
    parser.add_argument(
        "--cmd",
        default=os.environ.get("STT_CODEX_CMD", DEFAULT_CMD),
        help=f"Command to run inside the child PTY. Default: {DEFAULT_CMD}",
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="Working directory for the child command. Default: current directory.",
    )
    parser.add_argument(
        "--quiet-parent",
        action="store_true",
        help="Hide parent wrapper status lines.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color in parent wrapper status lines.",
    )
    parser.add_argument(
        "--codex-alt-screen",
        action="store_true",
        help="Do not add --no-alt-screen when running Codex.",
    )
    parser.add_argument(
        "cmd_args",
        nargs=argparse.REMAINDER,
        help="Arguments after -- are passed to the child command.",
    )
    args = parser.parse_args()
    if args.cmd_args and args.cmd_args[0] == "--":
        args.cmd_args = args.cmd_args[1:]
    if not args.cmd:
        parser.error("--cmd must not be empty")
    return args


def is_codex_command(command: str) -> bool:
    return Path(command).name == "codex"


def should_add_codex_no_alt_screen(args: argparse.Namespace) -> bool:
    return (
        is_codex_command(args.cmd)
        and not args.codex_alt_screen
        and "--no-alt-screen" not in args.cmd_args
    )


def child_argv(args: argparse.Namespace) -> list[str]:
    cmd_args = list(args.cmd_args)
    if should_add_codex_no_alt_screen(args):
        cmd_args.insert(0, "--no-alt-screen")
    return [args.cmd, *cmd_args]


def format_command(argv: list[str]) -> str:
    return " ".join(argv)


def parent_status(args: argparse.Namespace, message: str) -> None:
    if args.quiet_parent:
        return
    prefix = PARENT_PREFIX
    if sys.stderr.isatty() and not args.no_color:
        prefix = f"\033[36m{PARENT_PREFIX}\033[0m"
    print(f"{prefix} {message}", file=sys.stderr, flush=True)


def parent_banner(args: argparse.Namespace, argv: list[str], cwd: str | None) -> None:
    if args.quiet_parent:
        return
    display_cwd = cwd if cwd is not None else os.getcwd()
    parent_status(args, f"starting child: {format_command(argv)}")
    parent_status(args, f"cwd: {display_cwd}")
    parent_status(args, "child output follows")
    if sys.stderr.isatty() and not args.no_color:
        print("\033[36m" + ("-" * 48) + "\033[0m", file=sys.stderr, flush=True)
    else:
        print("-" * 48, file=sys.stderr, flush=True)


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


def passthrough(pid: int, child_fd: int) -> int:
    selector = selectors.DefaultSelector()
    selector.register(child_fd, selectors.EVENT_READ, "child")
    stdin_open = True
    try:
        selector.register(sys.stdin.fileno(), selectors.EVENT_READ, "stdin")
    except OSError:
        stdin_open = False
    exit_code: int | None = None

    def handle_sigwinch(signum: int, frame: object) -> None:
        copy_window_size(child_fd)

    previous_sigwinch = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, handle_sigwinch)
    copy_window_size(child_fd)

    try:
        while True:
            if exit_code is None:
                child_exit = reap_child(pid)
                if child_exit is not None:
                    exit_code = child_exit

            if exit_code is not None and not selector.get_map():
                return exit_code

            events = selector.select(timeout=0.1)
            if not events:
                if exit_code is not None:
                    return exit_code
                continue

            for key, _ in events:
                source = key.data
                if source == "child":
                    try:
                        data = os.read(child_fd, READ_SIZE)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        selector.unregister(child_fd)
                        os.close(child_fd)
                        if exit_code is None:
                            exit_code = reap_child(pid)
                        if exit_code is None:
                            _, status = os.waitpid(pid, 0)
                            exit_code = decode_wait_status(status)
                        continue
                    if not data:
                        selector.unregister(child_fd)
                        os.close(child_fd)
                        continue
                    os.write(sys.stdout.fileno(), data)

                if source == "stdin" and stdin_open:
                    data = os.read(sys.stdin.fileno(), READ_SIZE)
                    if not data:
                        selector.unregister(sys.stdin.fileno())
                        stdin_open = False
                        continue
                    os.write(child_fd, data)
    finally:
        signal.signal(signal.SIGWINCH, previous_sigwinch)
        selector.close()


def main() -> int:
    args = parse_args()
    try:
        cwd = validate_cwd(args.cwd)
        argv = child_argv(args)
        parent_banner(args, argv, cwd)
        pid, child_fd = spawn_child(argv, cwd)
        parent_status(args, f"child pid: {pid}")
        with TerminalMode():
            exit_code = passthrough(pid, child_fd)
        parent_status(args, f"child exited: {exit_code}")
        return exit_code
    except KeyboardInterrupt:
        return 130
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
