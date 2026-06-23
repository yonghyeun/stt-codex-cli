#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt_core.command import (
    child_argv as build_child_argv,
    format_command,
    is_codex_command,
    should_add_codex_no_alt_screen as command_should_add_codex_no_alt_screen,
)
from stt_core.keyboard import KeySequenceError, parse_key_sequence as parse_core_key_sequence
from stt_core.run_metadata import run_id_from_timestamp
from stt_core.transcript import transcript_has_text
from stt_core.transcription_prompt import DEFAULT_KOREAN_PHONETIC_INITIAL_PROMPT
from stt_features.codex_input import (
    inject_transcript as inject_feature_transcript,
    passthrough,
    resolve_audio_handoff,
)
from stt_runtime.child_process import spawn_child
from stt_runtime.recording import recording_config
from stt_runtime.run_artifacts import (
    create_run_dir as create_runtime_run_dir,
    resolve_run_output_dir as resolve_runtime_run_output_dir,
    save_run_artifacts as save_runtime_run_artifacts,
)
from stt_runtime.terminal import TerminalMode, validate_cwd
from stt_runtime.terminal import TerminalStatusRenderer

DEFAULT_CMD = "codex"
DEFAULT_INJECT_MODE = "stt"
DEFAULT_FIXED_INJECT_KEY = "ctrl+t"
DEFAULT_STT_INJECT_KEY = "ctrl+t"
DEFAULT_INJECT_TEXT = "hello from stt wrapper"
DEFAULT_TRIGGER_MODE = "tap"
DEFAULT_RELEASE_GAP = 0.35
DEFAULT_MAX_DURATION = 60.0
DEFAULT_MIN_DURATION = 0.15
DEFAULT_RUN_OUTPUT_DIR = "output/runs"
DEFAULT_STT_BACKEND = "worker"
DEFAULT_AUDIO_HANDOFF = "auto"
DEFAULT_STT_INITIAL_PROMPT = DEFAULT_KOREAN_PHONETIC_INITIAL_PROMPT
DEFAULT_STT_DAEMON_IDLE_TIMEOUT = 600.0
DEFAULT_STT_DAEMON_START_TIMEOUT = 30.0
DEFAULT_PARENT_PANEL = "ascii"
PARENT_PANEL_CHOICES = ("ascii", "none")
PARENT_PREFIX = "[stt-parent]"
PARENT_ASCII_PANEL = tuple(
    r"""
                 ;i.
                  M$L                    .;i.
                  M$Y;                .;iii;;.
                 ;$YY$i._           .iiii;;;;;
                .iiiYYYYYYiiiii;;;;i;iii;; ;;;
              .;iYYYYYYiiiiiiYYYiiiiiii;;  ;;;
           .YYYY$$$$YYYYYYYYYYYYYYYYiii;; ;;;;
         .YYY$$$$$$YYYYYY$$$$iiiY$$$$$$$ii;;;;
        :YYYF`,  TYYYYY$$$$$YYYYYYYi$$$$$iiiii;
        Y$MM: \  :YYYY$$P"````"T$YYMMMMMMMMiiYY.
     `.;$$M$$b.,dYY$$Yi; .(     .YYMMM$$$MMMMYY
   .._$MMMMM$!YYYYYYYYYi;.`"  .;iiMMM$MMMMMMMYY
    ._$MMMP` ```""4$$$$$iiiiiiii$MMMMMMMMMMMMMY;
     MMMM$:       :$$$$$$$MMMMMMMMMMM$$MMMMMMMYYL
    :MMMM$$.    .;PPb$$$$MMMMMMMMMM$$$$MMMMMMiYYU:
     iMM$$;;: ;;;;i$$$$$$$MMMMM$$$$MMMMMMMMMMYYYYY
     `$$$$i .. ``:iiii!*"``.$$$$$$$$$MMMMMMM$YiYYY
      :Y$$iii;;;.. ` ..;;i$$$$$$$$$MMMMMM$$YYYYiYY:
       :$$$$$iiiiiii$$$$$$$$$$$MMMMMMMMMMYYYYiiYYYY.
        `$$$$$$$$$$$$$$$$$$$$MMMMMMMM$YYYYYiiiYYYYYY
         YY$$$$$$$$$$$$$$$$MMMMMMM$$YYYiiiiiiYYYYYYY
        :YYYYYY$$$$$$$$$$$$$$$$$$YYYYYYYiiiiYYYYYYi' cmang
""".strip("\n").splitlines()
)


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
        "--debug-stt",
        action="store_true",
        help="Show raw parent/STT diagnostic lines instead of the compact status bar.",
    )
    parser.add_argument(
        "--parent-panel",
        choices=PARENT_PANEL_CHOICES,
        default=os.environ.get("STT_PARENT_PANEL", DEFAULT_PARENT_PANEL),
        help=(
            "Parent terminal top panel. Use 'none' to disable it. "
            f"Default: {DEFAULT_PARENT_PANEL}. Env: STT_PARENT_PANEL"
        ),
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
        help="Key sequence that triggers injection. Default: ctrl+t.",
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
        "--trigger-mode",
        choices=("tap", "hold"),
        default=os.environ.get("STT_TRIGGER_MODE", DEFAULT_TRIGGER_MODE),
        help=(
            "STT trigger behavior. tap starts recording on first trigger and stops "
            "on the next trigger; hold preserves legacy repeated-trigger PTT. "
            f"Default: {DEFAULT_TRIGGER_MODE}. Env: STT_TRIGGER_MODE"
        ),
    )
    parser.add_argument(
        "--release-gap",
        type=positive_float,
        default=None,
        help=(
            "Legacy hold trigger mode only: seconds without repeated trigger input "
            "before STT recording stops. "
            f"Default: {DEFAULT_RELEASE_GAP:g}s. Env: STT_PTT_RELEASE_GAP"
        ),
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
        "--save-run",
        action="store_true",
        help="Save audio, transcript, and metadata under output/runs/.",
    )
    parser.add_argument(
        "--run-output-dir",
        default=os.environ.get("STT_RUN_OUTPUT_DIR", DEFAULT_RUN_OUTPUT_DIR),
        help=f"Directory for --save-run artifacts. Default: {DEFAULT_RUN_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--stt-model",
        default=os.environ.get("STT_MODEL", "large-v3"),
        help="Whisper model for STT mode. Default: large-v3",
    )
    parser.add_argument(
        "--stt-backend",
        choices=("subprocess", "worker", "daemon"),
        default=os.environ.get("STT_BACKEND", DEFAULT_STT_BACKEND),
        help=f"STT execution backend. Default: {DEFAULT_STT_BACKEND}",
    )
    parser.add_argument(
        "--stt-daemon-socket-dir",
        default=os.environ.get("STT_DAEMON_SOCKET_DIR"),
        help="Directory for shared STT daemon sockets. Default: runtime/cache directory.",
    )
    parser.add_argument(
        "--stt-daemon-idle-timeout",
        type=positive_float,
        default=float(
            os.environ.get(
                "STT_DAEMON_IDLE_TIMEOUT",
                str(DEFAULT_STT_DAEMON_IDLE_TIMEOUT),
            )
        ),
        help=(
            "Seconds before an idle shared STT daemon exits. "
            f"Default: {DEFAULT_STT_DAEMON_IDLE_TIMEOUT:g}s"
        ),
    )
    parser.add_argument(
        "--stt-daemon-start-timeout",
        type=positive_float,
        default=float(
            os.environ.get(
                "STT_DAEMON_START_TIMEOUT",
                str(DEFAULT_STT_DAEMON_START_TIMEOUT),
            )
        ),
        help=(
            "Seconds to wait for a shared STT daemon to become ready. "
            f"Default: {DEFAULT_STT_DAEMON_START_TIMEOUT:g}s"
        ),
    )
    parser.add_argument(
        "--audio-handoff",
        choices=("auto", "file", "buffer"),
        default=os.environ.get("STT_AUDIO_HANDOFF", DEFAULT_AUDIO_HANDOFF),
        help=(
            "Audio handoff path for STT mode. "
            "auto uses buffer only with worker backend and no save/debug audio options. "
            f"Default: {DEFAULT_AUDIO_HANDOFF}"
        ),
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
        default=os.environ.get("STT_INITIAL_PROMPT", DEFAULT_STT_INITIAL_PROMPT),
        help="STT initial prompt. Default: Korean phonetic prompt. Env: STT_INITIAL_PROMPT",
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
    if args.parent_panel not in PARENT_PANEL_CHOICES:
        parser.error(
            "--parent-panel must be one of: " + ", ".join(PARENT_PANEL_CHOICES)
        )
    if args.cmd_args and args.cmd_args[0] == "--":
        args.cmd_args = args.cmd_args[1:]
    if not args.cmd:
        parser.error("--cmd must not be empty")
    try:
        args.release_gap = resolve_release_gap(
            explicit_release_gap=args.release_gap,
            env=os.environ,
        )
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))
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


def resolve_release_gap(
    *,
    explicit_release_gap: float | None,
    env: Mapping[str, str],
) -> float:
    if explicit_release_gap is not None:
        return explicit_release_gap
    env_release_gap = env.get("STT_PTT_RELEASE_GAP")
    if env_release_gap is not None:
        return positive_float(env_release_gap)
    return DEFAULT_RELEASE_GAP


def parse_key_sequence(value: str) -> bytes:
    try:
        return parse_core_key_sequence(value)
    except KeySequenceError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def should_add_codex_no_alt_screen(args: argparse.Namespace) -> bool:
    return command_should_add_codex_no_alt_screen(
        args.cmd,
        list(args.cmd_args),
        codex_alt_screen=args.codex_alt_screen,
    )


def child_argv(args: argparse.Namespace) -> list[str]:
    return build_child_argv(
        args.cmd,
        list(args.cmd_args),
        codex_alt_screen=args.codex_alt_screen,
    )


def parent_status(args: argparse.Namespace, message: str) -> None:
    renderer = getattr(args, "parent_status_renderer", None)
    if renderer is not None:
        renderer(message)
        return
    if args.quiet_parent:
        return
    prefix = PARENT_PREFIX
    if sys.stderr.isatty() and not args.no_color:
        prefix = f"\033[36m{PARENT_PREFIX}\033[0m"
    print(f"{prefix} {message}", file=sys.stderr, flush=True)


def resolve_run_output_dir(args: argparse.Namespace) -> Path:
    return resolve_runtime_run_output_dir(REPO_ROOT, args.run_output_dir)


def create_run_dir(args: argparse.Namespace, timestamp: datetime) -> Path:
    return create_runtime_run_dir(REPO_ROOT, args.run_output_dir, timestamp)


def save_run_artifacts(
    args: argparse.Namespace,
    audio_file: Path,
    transcript: str,
    *,
    started_at: datetime,
    elapsed: float,
    injected: bool,
    outcome: str,
    error: str | None = None,
) -> Path | None:
    return save_runtime_run_artifacts(
        repo_root=REPO_ROOT,
        save_run=args.save_run,
        keep_audio=args.keep_audio,
        run_output_dir=args.run_output_dir,
        audio_file=audio_file,
        transcript=transcript,
        started_at=started_at,
        elapsed=elapsed,
        injected=injected,
        outcome=outcome,
        error=error,
        stt={
            "model": args.stt_model,
            "language": args.stt_language,
            "device": args.stt_device,
            "compute_type": args.stt_compute_type,
            "beam_size": args.stt_beam_size,
            "vad_filter": not args.stt_no_vad_filter,
            "initial_prompt": args.stt_initial_prompt,
        },
        child_command=child_argv(args),
        child_cwd=args.cwd,
        status=lambda message: parent_status(args, message),
    )


def inject_transcript(args: argparse.Namespace, child_fd: int, transcript: str) -> bool:
    return inject_feature_transcript(
        lambda message: parent_status(args, message),
        child_fd,
        transcript,
    )


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
            if args.trigger_mode == "hold":
                parent_status(
                    args,
                    f"trigger key: {args.inject_key} hold/repeat; release gap {args.release_gap:g}s; Enter still manual",
                )
            else:
                parent_status(
                    args,
                    f"trigger key: {args.inject_key} tap starts/stops recording; Enter still manual",
                )
            parent_status(args, f"stt backend: {args.stt_backend}")
            parent_status(
                args,
                f"audio handoff: {args.audio_handoff} -> {resolve_audio_handoff(args)}",
            )
            if args.save_run:
                parent_status(args, f"run artifacts: {resolve_run_output_dir(args)}")
    parent_status(args, "child output follows")
    if not args.debug_stt:
        return
    if sys.stderr.isatty() and not args.no_color:
        print("\033[36m" + ("-" * 48) + "\033[0m", file=sys.stderr, flush=True)
    else:
        print("-" * 48, file=sys.stderr, flush=True)


def create_parent_status_renderer(args: argparse.Namespace) -> TerminalStatusRenderer:
    return TerminalStatusRenderer(
        enabled=not args.quiet_parent,
        color=not args.no_color,
        debug=args.debug_stt,
        parent_panel=parent_panel_lines(args),
    )


def parent_panel_lines(args: argparse.Namespace) -> tuple[str, ...]:
    if getattr(args, "parent_panel", DEFAULT_PARENT_PANEL) == "none":
        return ()
    return PARENT_ASCII_PANEL


def initial_parent_status(args: argparse.Namespace) -> str:
    if args.disable_inject_key:
        return "STT passthrough | inject key disabled"
    if args.inject_mode == "fixed-text":
        return f"STT fixed-text | {args.inject_key} inserts {len(args.inject_text)} chars"
    if args.trigger_mode == "hold":
        return f"STT idle | hold {args.inject_key} to record"
    return f"STT idle | {args.inject_key} start"


def main() -> int:
    args = parse_args()
    try:
        cwd = validate_cwd(args.cwd)
        argv = child_argv(args)
        parent_status_renderer = create_parent_status_renderer(args)
        args.parent_status_renderer = parent_status_renderer
        parent_status_renderer.render_parent_panel()
        parent_banner(args, argv, cwd)
        parent_status_renderer.set_status(initial_parent_status(args))
        pid, child_fd = spawn_child(argv, cwd)
        parent_status(args, f"child pid: {pid}")
        with TerminalMode():
            exit_code = passthrough(
                args=args,
                repo_root=REPO_ROOT,
                pid=pid,
                child_fd=child_fd,
                child_command=argv,
                status=lambda message: parent_status(args, message),
                reserved_terminal_rows=parent_status_renderer.reserved_rows,
            )
        parent_status(args, f"child exited: {exit_code}")
        return exit_code
    except KeyboardInterrupt:
        return 130
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
