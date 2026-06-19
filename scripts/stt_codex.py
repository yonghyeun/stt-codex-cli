#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import fcntl
import os
import pty
import selectors
import signal
import subprocess
import sys
import tempfile
import termios
import time
import tty
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CMD = "codex"
DEFAULT_INJECT_MODE = "stt"
DEFAULT_FIXED_INJECT_KEY = "ctrl+t"
DEFAULT_STT_INJECT_KEY = "t"
DEFAULT_INJECT_TEXT = "hello from stt wrapper"
DEFAULT_RELEASE_GAP = 0.75
DEFAULT_MAX_DURATION = 60.0
DEFAULT_MIN_DURATION = 0.15
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


@dataclass
class RecordingState:
    process: subprocess.Popen[bytes] | None = None
    audio_file: Path | None = None
    started_at: float | None = None
    last_trigger_at: float | None = None

    def active(self) -> bool:
        return self.process is not None

    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        return time.monotonic() - self.started_at


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
        "--inject-mode",
        choices=("stt", "fixed-text"),
        default=os.environ.get("STT_INJECT_MODE", DEFAULT_INJECT_MODE),
        help=f"Injection mode. Default: {DEFAULT_INJECT_MODE}",
    )
    parser.add_argument(
        "--inject-key",
        default=os.environ.get("STT_INJECT_KEY"),
        help="Key sequence that triggers injection. Default: t for stt, ctrl+t for fixed-text.",
    )
    parser.add_argument(
        "--inject-text",
        default=os.environ.get("STT_INJECT_TEXT", DEFAULT_INJECT_TEXT),
        help=f"Text to inject into the child PTY. Default: {DEFAULT_INJECT_TEXT!r}",
    )
    parser.add_argument(
        "--disable-inject-key",
        action="store_true",
        help="Pass all stdin through without reserving an injection key.",
    )
    parser.add_argument(
        "--release-gap",
        type=positive_float,
        default=float(os.environ.get("STT_PTT_RELEASE_GAP", str(DEFAULT_RELEASE_GAP))),
        help=f"Seconds without repeated trigger input before STT recording stops. Default: {DEFAULT_RELEASE_GAP:g}s",
    )
    parser.add_argument(
        "--max-duration",
        type=positive_float,
        default=float(os.environ.get("STT_PTT_MAX_DURATION", str(DEFAULT_MAX_DURATION))),
        help=f"Maximum STT recording duration. Default: {DEFAULT_MAX_DURATION:g}s",
    )
    parser.add_argument(
        "--min-duration",
        type=positive_float,
        default=float(os.environ.get("STT_PTT_MIN_DURATION", str(DEFAULT_MIN_DURATION))),
        help=f"Minimum accepted STT recording duration. Default: {DEFAULT_MIN_DURATION:g}s",
    )
    parser.add_argument(
        "--temp-dir",
        default=os.environ.get("STT_TEMP_DIR"),
        help="Directory for temporary audio files. Default: system temp directory.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep temporary audio files after transcription.",
    )
    parser.add_argument(
        "--stt-model",
        default=os.environ.get("STT_MODEL", "large-v3"),
        help="Whisper model for STT mode. Default: large-v3",
    )
    parser.add_argument(
        "--stt-language",
        default=os.environ.get("STT_LANGUAGE", "ko"),
        help="STT language code. Default: ko",
    )
    parser.add_argument(
        "--stt-device",
        choices=("auto", "cpu", "cuda"),
        default=os.environ.get("STT_DEVICE", "auto"),
        help="STT inference device. Default: auto",
    )
    parser.add_argument(
        "--stt-compute-type",
        default=os.environ.get("STT_COMPUTE_TYPE", "auto"),
        help="STT compute type. Default: auto",
    )
    parser.add_argument(
        "--stt-beam-size",
        type=positive_int,
        default=int(os.environ.get("STT_BEAM_SIZE", "5")),
        help="STT beam size. Default: 5",
    )
    parser.add_argument(
        "--stt-initial-prompt",
        default=os.environ.get("STT_INITIAL_PROMPT"),
        help="Optional STT initial prompt.",
    )
    parser.add_argument(
        "--stt-no-vad-filter",
        action="store_true",
        help="Disable faster-whisper VAD filter in STT mode.",
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
    if args.inject_key is None:
        args.inject_key = (
            DEFAULT_STT_INJECT_KEY
            if args.inject_mode == "stt"
            else DEFAULT_FIXED_INJECT_KEY
        )
    if not args.inject_text:
        parser.error("--inject-text must not be empty")
    try:
        args.inject_key_bytes = parse_key_sequence(args.inject_key)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))
    return args


def positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid number: {value}") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"value must be positive: {value}")
    return parsed


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"value must be positive: {value}")
    return parsed


def parse_key_sequence(value: str) -> bytes:
    normalized = value.strip().lower()
    if not normalized:
        raise argparse.ArgumentTypeError("--inject-key must not be empty")

    named_keys = {
        "tab": b"\t",
        "esc": b"\x1b",
        "escape": b"\x1b",
        "space": b" ",
        "enter": b"\r",
    }
    if normalized in named_keys:
        return named_keys[normalized]

    if normalized.startswith("ctrl+"):
        key = normalized.removeprefix("ctrl+")
        if len(key) != 1 or not ("a" <= key <= "z"):
            raise argparse.ArgumentTypeError(
                "ctrl key syntax must be ctrl+<a-z>, for example ctrl+t"
            )
        return bytes([ord(key) - ord("a") + 1])

    if len(value) == 1:
        return value.encode()

    raise argparse.ArgumentTypeError(
        "inject key must be a single character, named key, or ctrl+<a-z>"
    )


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
    if not args.disable_inject_key:
        if args.inject_mode == "fixed-text":
            parent_status(
                args,
                f"inject key: {args.inject_key} -> {len(args.inject_text)} chars; Enter still manual",
            )
        else:
            parent_status(
                args,
                f"ptt key: {args.inject_key}; release gap {args.release_gap:g}s; Enter still manual",
            )
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


def create_temp_audio(args: argparse.Namespace) -> Path:
    temp_dir = args.temp_dir
    if temp_dir is not None:
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="stt-codex-",
        suffix=".wav",
        dir=temp_dir,
        delete=False,
    ) as temp_file:
        return Path(temp_file.name)


def start_recording(args: argparse.Namespace, state: RecordingState) -> None:
    if state.active():
        return

    audio_file = create_temp_audio(args)
    command = [
        "arecord",
        "-D",
        os.environ.get("STT_RECORD_DEVICE", "default"),
        "-f",
        os.environ.get("STT_RECORD_FORMAT", "S16_LE"),
        "-r",
        os.environ.get("STT_RECORD_RATE", "16000"),
        "-c",
        os.environ.get("STT_RECORD_CHANNELS", "1"),
        str(audio_file),
    ]
    state.process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    state.audio_file = audio_file
    state.started_at = time.monotonic()
    state.last_trigger_at = state.started_at
    parent_status(args, f"recording started: {audio_file}")


def stop_recording(args: argparse.Namespace, state: RecordingState) -> tuple[Path, float]:
    if state.process is None or state.audio_file is None:
        raise RuntimeError("recording is not running")

    process = state.process
    audio_file = state.audio_file
    elapsed = state.elapsed()
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    state.process = None
    state.audio_file = None
    state.started_at = None
    state.last_trigger_at = None
    parent_status(args, f"recording stopped: elapsed={elapsed:.2f}s")
    return audio_file, elapsed


def cleanup_audio(args: argparse.Namespace, audio_file: Path) -> None:
    if args.keep_audio:
        parent_status(args, f"kept audio: {audio_file}")
        return
    try:
        audio_file.unlink()
        parent_status(args, "deleted temporary audio")
    except FileNotFoundError:
        return


def transcript_has_text(transcript: str) -> bool:
    return any(character.isalnum() for character in transcript)


def transcribe_audio(args: argparse.Namespace, audio_file: Path) -> str:
    command = [
        str(REPO_ROOT / "scripts/transcribe.sh"),
        str(audio_file),
        "--model",
        args.stt_model,
        "--language",
        args.stt_language,
        "--device",
        args.stt_device,
        "--compute-type",
        args.stt_compute_type,
        "--beam-size",
        str(args.stt_beam_size),
    ]
    if args.stt_initial_prompt:
        command.extend(["--initial-prompt", args.stt_initial_prompt])
    if args.stt_no_vad_filter:
        command.append("--no-vad-filter")

    parent_status(args, "transcribing...")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    for line in result.stderr.splitlines():
        if line.strip():
            parent_status(args, f"stt: {line.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"STT failed with exit code {result.returncode}")
    return result.stdout.strip()


def inject_transcript(args: argparse.Namespace, child_fd: int, transcript: str) -> None:
    if not transcript_has_text(transcript):
        parent_status(args, "empty transcript; nothing injected")
        return
    os.write(child_fd, transcript.encode())
    parent_status(
        args,
        f"injected transcript {len(transcript)} chars; review text, then press Enter to send",
    )


def finish_recording_and_inject(
    args: argparse.Namespace,
    child_fd: int,
    state: RecordingState,
) -> None:
    audio_file, elapsed = stop_recording(args, state)
    try:
        if elapsed < args.min_duration:
            parent_status(
                args,
                f"recording too short: {elapsed:.2f}s < {args.min_duration:g}s; skipped STT",
            )
            return
        transcript = transcribe_audio(args, audio_file)
        inject_transcript(args, child_fd, transcript)
    finally:
        cleanup_audio(args, audio_file)


def handle_fixed_text_injection(args: argparse.Namespace, child_fd: int, data: bytes) -> None:
    if args.disable_inject_key:
        os.write(child_fd, data)
        return

    trigger = args.inject_key_bytes
    start = 0
    while True:
        index = data.find(trigger, start)
        if index < 0:
            if start < len(data):
                os.write(child_fd, data[start:])
            return

        if index > start:
            os.write(child_fd, data[start:index])

        os.write(child_fd, args.inject_text.encode())
        parent_status(
            args,
            f"injected {len(args.inject_text)} chars; review text, then press Enter to send",
        )
        start = index + len(trigger)


def handle_stt_ptt_input(
    args: argparse.Namespace,
    child_fd: int,
    data: bytes,
    state: RecordingState,
) -> None:
    if args.disable_inject_key:
        os.write(child_fd, data)
        return

    trigger = args.inject_key_bytes
    start = 0
    while True:
        index = data.find(trigger, start)
        if index < 0:
            if start < len(data):
                os.write(child_fd, data[start:])
            return

        if index > start:
            os.write(child_fd, data[start:index])

        if not state.active():
            start_recording(args, state)
        state.last_trigger_at = time.monotonic()
        start = index + len(trigger)


def handle_stdin_data(
    args: argparse.Namespace,
    child_fd: int,
    data: bytes,
    state: RecordingState,
) -> None:
    if args.inject_mode == "fixed-text":
        handle_fixed_text_injection(args, child_fd, data)
        return
    handle_stt_ptt_input(args, child_fd, data, state)


def maybe_finish_stt_recording(
    args: argparse.Namespace,
    child_fd: int,
    state: RecordingState,
) -> None:
    if not state.active() or state.last_trigger_at is None:
        return

    elapsed_since_trigger = time.monotonic() - state.last_trigger_at
    if state.elapsed() >= args.max_duration:
        parent_status(args, f"max duration reached: {args.max_duration:g}s")
        try:
            finish_recording_and_inject(args, child_fd, state)
        except RuntimeError as error:
            parent_status(args, f"stt error: {error}")
        return
    if elapsed_since_trigger >= args.release_gap:
        try:
            finish_recording_and_inject(args, child_fd, state)
        except RuntimeError as error:
            parent_status(args, f"stt error: {error}")


def passthrough(args: argparse.Namespace, pid: int, child_fd: int) -> int:
    selector = selectors.DefaultSelector()
    selector.register(child_fd, selectors.EVENT_READ, "child")
    stdin_open = True
    try:
        selector.register(sys.stdin.fileno(), selectors.EVENT_READ, "stdin")
    except OSError:
        stdin_open = False
    exit_code: int | None = None
    recording_state = RecordingState()

    def handle_sigwinch(signum: int, frame: object) -> None:
        copy_window_size(child_fd)

    previous_sigwinch = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, handle_sigwinch)
    copy_window_size(child_fd)

    try:
        while True:
            if args.inject_mode == "stt":
                maybe_finish_stt_recording(args, child_fd, recording_state)

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
                    handle_stdin_data(args, child_fd, data, recording_state)
    finally:
        if recording_state.active():
            audio_file, _ = stop_recording(args, recording_state)
            cleanup_audio(args, audio_file)
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
            exit_code = passthrough(args, pid, child_fd)
        parent_status(args, f"child exited: {exit_code}")
        return exit_code
    except KeyboardInterrupt:
        return 130
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
