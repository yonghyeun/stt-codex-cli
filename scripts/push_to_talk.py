#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import selectors
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRIGGER_KEYCODE = 28
DEFAULT_MODIFIER_KEYCODES = (64, 108, 204)
DEFAULT_MAX_DURATION = 60.0
DEFAULT_MIN_DURATION = 0.15


@dataclass(frozen=True)
class KeyEvent:
    kind: str
    detail: int


class XInputEventParser:
    def __init__(self) -> None:
        self.pending_kind: str | None = None

    def feed(self, line: str) -> KeyEvent | None:
        if "(RawKeyPress)" in line:
            self.pending_kind = "press"
            return None
        if "(RawKeyRelease)" in line:
            self.pending_kind = "release"
            return None

        stripped = line.strip()
        if self.pending_kind and stripped.startswith("detail:"):
            _, _, raw_detail = stripped.partition(":")
            self.pending_kind, kind = None, self.pending_kind
            return KeyEvent(kind=kind, detail=int(raw_detail.strip()))
        return None


class Recorder:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.process: subprocess.Popen[bytes] | None = None
        self.output_file: Path | None = None
        self.started_at: float | None = None

    def start(self) -> Path:
        if self.process is not None:
            raise RuntimeError("recording is already running")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = self.output_dir / f"recording-{timestamp}.wav"

        device = os.environ.get("STT_RECORD_DEVICE", "default")
        rate = os.environ.get("STT_RECORD_RATE", "16000")
        channels = os.environ.get("STT_RECORD_CHANNELS", "1")
        sample_format = os.environ.get("STT_RECORD_FORMAT", "S16_LE")

        command = [
            "arecord",
            "-D",
            device,
            "-f",
            sample_format,
            "-r",
            rate,
            "-c",
            channels,
            str(output_file),
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        self.output_file = output_file
        self.started_at = time.monotonic()
        return output_file

    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        return time.monotonic() - self.started_at

    def stop(self) -> Path:
        if self.process is None or self.output_file is None:
            raise RuntimeError("recording is not running")

        process = self.process
        output_file = self.output_file
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

        self.process = None
        self.output_file = None
        self.started_at = None
        return output_file

    def terminate(self) -> None:
        if self.process is None:
            return
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        self.process = None
        self.output_file = None
        self.started_at = None


def parse_keycodes(value: str) -> tuple[int, ...]:
    keycodes: list[int] = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        try:
            keycode = int(part)
        except ValueError as error:
            raise argparse.ArgumentTypeError(f"invalid keycode: {part}") from error
        if keycode <= 0:
            raise argparse.ArgumentTypeError(f"keycode must be positive: {keycode}")
        keycodes.append(keycode)
    if not keycodes:
        raise argparse.ArgumentTypeError("at least one keycode is required")
    return tuple(keycodes)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push-to-talk STT input helper using xinput key press/release events."
    )
    parser.add_argument(
        "--keycode",
        type=positive_int,
        default=DEFAULT_TRIGGER_KEYCODE,
        help=f"Trigger keycode to hold. Default: {DEFAULT_TRIGGER_KEYCODE} (t)",
    )
    parser.add_argument(
        "--modifier-keycodes",
        type=parse_keycodes,
        default=DEFAULT_MODIFIER_KEYCODES,
        help="Comma-separated modifier keycodes for --require-modifier. Default: 64,108,204 (Alt keys)",
    )
    modifier_group = parser.add_mutually_exclusive_group()
    parser.set_defaults(no_modifier=True)
    modifier_group.add_argument(
        "--no-modifier",
        dest="no_modifier",
        action="store_true",
        help="Trigger on keycode alone without requiring a modifier. Default.",
    )
    modifier_group.add_argument(
        "--require-modifier",
        dest="no_modifier",
        action="store_false",
        help="Require one of --modifier-keycodes with the trigger key.",
    )
    parser.add_argument(
        "--listen-timeout",
        type=positive_float,
        help="Seconds to wait for the hotkey before failing.",
    )
    parser.add_argument(
        "--max-duration",
        type=positive_float,
        default=DEFAULT_MAX_DURATION,
        help=f"Maximum recording duration. Default: {DEFAULT_MAX_DURATION:g}s",
    )
    parser.add_argument(
        "--min-duration",
        type=positive_float,
        default=DEFAULT_MIN_DURATION,
        help=f"Minimum accepted recording duration. Default: {DEFAULT_MIN_DURATION:g}s",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("STT_OUTPUT_DIR", "output/recordings"),
        help="Recording output directory. Default: output/recordings",
    )
    parser.add_argument(
        "--record-only",
        action="store_true",
        help="Record with push-to-talk and print the WAV path, then stop.",
    )
    parser.add_argument("--no-recovery", action="store_true", help="Skip token recovery.")
    parser.add_argument("--memory", help="Token recovery memory JSON.")
    parser.add_argument(
        "--min-confidence",
        default=os.environ.get("STT_TOKEN_MIN_CONFIDENCE", "0.8"),
        help="Minimum token recovery confidence. Default: 0.8",
    )
    parser.add_argument(
        "--clipboard-backend",
        default=os.environ.get("STT_CLIPBOARD_BACKEND", "auto"),
        help="Clipboard backend: auto, xclip, or wl-copy.",
    )
    parser.add_argument(
        "--no-copy-verify",
        action="store_true",
        help="Skip clipboard readback verification.",
    )
    parser.add_argument("--output-transcript", help="Write raw STT transcript to PATH.")
    parser.add_argument("--output-recovered", help="Write final recovered text to PATH.")
    parser.add_argument(
        "transcribe_args",
        nargs=argparse.REMAINDER,
        help="Arguments after -- are passed to scripts/transcribe.sh.",
    )
    args = parser.parse_args()
    if args.transcribe_args and args.transcribe_args[0] == "--":
        args.transcribe_args = args.transcribe_args[1:]
    return args


def modifier_active(pressed: set[int], modifier_keycodes: tuple[int, ...], no_modifier: bool) -> bool:
    return no_modifier or bool(pressed.intersection(modifier_keycodes))


def should_start_recording(args: argparse.Namespace, pressed: set[int]) -> bool:
    return args.keycode in pressed and modifier_active(
        pressed,
        args.modifier_keycodes,
        args.no_modifier,
    )


def should_stop_recording(args: argparse.Namespace, pressed: set[int]) -> bool:
    if args.keycode not in pressed:
        return True
    return not modifier_active(pressed, args.modifier_keycodes, args.no_modifier)


def start_xinput() -> subprocess.Popen[str]:
    try:
        return subprocess.Popen(
            ["xinput", "test-xi2", "--root"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as error:
        raise RuntimeError("xinput is required but was not found") from error


def record_once(args: argparse.Namespace) -> Path:
    xinput = start_xinput()
    if xinput.stdout is None:
        raise RuntimeError("failed to open xinput output")

    selector = selectors.DefaultSelector()
    selector.register(xinput.stdout, selectors.EVENT_READ)
    parser = XInputEventParser()
    recorder = Recorder(REPO_ROOT / args.output_dir)
    pressed: set[int] = set()
    listen_started_at = time.monotonic()
    recording = False
    recording_file: Path | None = None

    if args.no_modifier:
        print(f"waiting: hotkey=keycode {args.keycode}", file=sys.stderr)
    else:
        print(
            "waiting: hotkey="
            f"modifier+keycode {args.keycode} "
            f"modifier_keycodes={','.join(str(code) for code in args.modifier_keycodes)}",
            file=sys.stderr,
        )

    try:
        while True:
            if args.listen_timeout and not recording:
                if time.monotonic() - listen_started_at > args.listen_timeout:
                    raise RuntimeError("timed out waiting for push-to-talk hotkey")

            if recording and recorder.elapsed() >= args.max_duration:
                print(
                    f"max duration reached: {args.max_duration:g}s",
                    file=sys.stderr,
                )
                recording_file = recorder.stop()
                break

            events = selector.select(timeout=0.1)
            if not events:
                continue

            for key, _ in events:
                line = key.fileobj.readline()
                if not line:
                    raise RuntimeError("xinput stopped unexpectedly")
                event = parser.feed(line)
                if event is None:
                    continue

                if event.kind == "press":
                    pressed.add(event.detail)
                    if not recording and should_start_recording(args, pressed):
                        recording_file = recorder.start()
                        recording = True
                        print(f"recording started: {recording_file}", file=sys.stderr)

                if event.kind == "release":
                    pressed.discard(event.detail)
                    if recording and should_stop_recording(args, pressed):
                        elapsed = recorder.elapsed()
                        recording_file = recorder.stop()
                        print(
                            f"recording stopped: elapsed={elapsed:.2f}s file={recording_file}",
                            file=sys.stderr,
                        )
                        if elapsed < args.min_duration:
                            raise RuntimeError(
                                f"recording too short: {elapsed:.2f}s < {args.min_duration:g}s"
                            )
                        return recording_file
    finally:
        recorder.terminate()
        xinput.terminate()
        try:
            xinput.wait(timeout=2)
        except subprocess.TimeoutExpired:
            xinput.kill()
            xinput.wait(timeout=2)

    if recording_file is None:
        raise RuntimeError("recording did not complete")
    if recorder.elapsed() and recorder.elapsed() < args.min_duration:
        raise RuntimeError("recording too short")
    return recording_file


def run_stt_clipboard(args: argparse.Namespace, recording_file: Path) -> int:
    command = [str(REPO_ROOT / "scripts/stt_clipboard.sh")]
    if args.no_recovery:
        command.append("--no-recovery")
    if args.memory:
        command.extend(["--memory", args.memory])
    command.extend(["--min-confidence", str(args.min_confidence)])
    command.extend(["--clipboard-backend", args.clipboard_backend])
    if args.no_copy_verify:
        command.append("--no-copy-verify")
    if args.output_transcript:
        command.extend(["--output-transcript", args.output_transcript])
    if args.output_recovered:
        command.extend(["--output-recovered", args.output_recovered])
    command.append(str(recording_file))
    command.extend(args.transcribe_args)
    return subprocess.call(command)


def main() -> int:
    args = parse_args()
    try:
        recording_file = record_once(args)
        if args.record_only:
            print(recording_file)
            return 0
        return run_stt_clipboard(args, recording_file)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
