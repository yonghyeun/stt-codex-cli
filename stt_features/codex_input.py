from __future__ import annotations

import errno
import os
import selectors
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path

from stt_core.transcript import transcript_has_text
from stt_runtime.child_process import decode_wait_status, reap_child
from stt_runtime.recording import (
    RecordedAudio,
    RecordingState,
    cleanup_recorded_audio,
    start_recording,
    stop_recording_result,
)
from stt_runtime.run_artifacts import save_run_artifacts
from stt_runtime.terminal import copy_window_size
from stt_runtime.transcription import (
    DaemonTranscriptionClient,
    PersistentWorkerTranscriptionClient,
    SubprocessTranscriptionClient,
    TranscriptionClient,
    TranscriptionConfig,
    TranscriptionRequest,
)


READ_SIZE = 4096
StatusFn = Callable[[str], None]


def transcription_config_from_args(args: object) -> TranscriptionConfig:
    return TranscriptionConfig(
        model=args.stt_model,
        language=args.stt_language,
        device=args.stt_device,
        compute_type=args.stt_compute_type,
        beam_size=args.stt_beam_size,
        initial_prompt=args.stt_initial_prompt,
        vad_filter=not args.stt_no_vad_filter,
    )


def transcription_metadata(config: TranscriptionConfig) -> dict[str, object]:
    return {
        "model": config.model,
        "language": config.language,
        "device": config.device,
        "compute_type": config.compute_type,
        "beam_size": config.beam_size,
        "vad_filter": config.vad_filter,
        "initial_prompt": config.initial_prompt,
    }


def create_transcription_client(
    *,
    args: object,
    repo_root: Path,
    config: TranscriptionConfig,
    status: StatusFn,
) -> TranscriptionClient:
    backend = getattr(args, "stt_backend", "subprocess")
    if backend == "subprocess":
        return SubprocessTranscriptionClient(
            repo_root=repo_root,
            config=config,
            status=status,
        )
    if backend == "worker":
        return PersistentWorkerTranscriptionClient(
            repo_root=repo_root,
            config=config,
            status=status,
        )
    if backend == "daemon":
        socket_dir = getattr(args, "stt_daemon_socket_dir", None)
        return DaemonTranscriptionClient(
            repo_root=repo_root,
            config=config,
            status=status,
            socket_dir=Path(socket_dir) if socket_dir else None,
            idle_timeout_seconds=float(getattr(args, "stt_daemon_idle_timeout", 300.0)),
            start_timeout_seconds=float(getattr(args, "stt_daemon_start_timeout", 30.0)),
        )
    raise RuntimeError(f"unsupported STT backend: {backend}")


def resolve_audio_handoff(args: object) -> str:
    requested = getattr(args, "audio_handoff", "auto")
    backend = getattr(args, "stt_backend", "subprocess")
    save_run = bool(getattr(args, "save_run", False))
    keep_audio = bool(getattr(args, "keep_audio", False))

    if requested == "file":
        return "file"
    if requested == "buffer":
        if backend in {"worker", "daemon"} and not save_run and not keep_audio:
            return "buffer"
        return "file"
    if requested != "auto":
        raise RuntimeError(f"unsupported audio handoff: {requested}")
    if backend in {"worker", "daemon"} and not save_run and not keep_audio:
        return "buffer"
    return "file"


def transcription_request_from_recorded_audio(
    recorded_audio: RecordedAudio,
) -> TranscriptionRequest:
    if recorded_audio.audio_bytes is not None:
        if not recorded_audio.audio_bytes:
            raise RuntimeError("recording did not produce audio bytes")
        return TranscriptionRequest(
            audio_bytes=recorded_audio.audio_bytes,
            audio_format="wav",
        )
    if recorded_audio.audio_file is None:
        raise RuntimeError("recording did not produce audio for transcription")
    return TranscriptionRequest(audio_file=recorded_audio.audio_file)


def save_and_cleanup_recorded_audio(
    *,
    args: object,
    repo_root: Path,
    child_command: list[str],
    recorded_audio: RecordedAudio,
    transcript: str,
    injected: bool,
    outcome: str,
    error_message: str | None,
    transcription_config: TranscriptionConfig,
    status: StatusFn,
) -> None:
    if recorded_audio.audio_file is not None:
        save_run_artifacts(
            repo_root=repo_root,
            save_run=args.save_run,
            keep_audio=args.keep_audio,
            run_output_dir=args.run_output_dir,
            audio_file=recorded_audio.audio_file,
            transcript=transcript,
            started_at=recorded_audio.started_at,
            elapsed=recorded_audio.elapsed,
            injected=injected,
            outcome=outcome,
            error=error_message,
            stt=transcription_metadata(transcription_config),
            child_command=child_command,
            child_cwd=args.cwd,
            status=status,
        )
    elif args.save_run or args.keep_audio:
        raise RuntimeError("save/debug audio options require file-backed audio")

    cleanup_recorded_audio(
        keep_audio=args.keep_audio,
        recorded_audio=recorded_audio,
        status=status,
    )


def inject_transcript(status: StatusFn, child_fd: int, transcript: str) -> bool:
    if not transcript_has_text(transcript):
        status("empty transcript; nothing injected")
        return False
    os.write(child_fd, transcript.encode())
    status(
        f"injected transcript {len(transcript)} chars; review text, then press Enter to send"
    )
    return True


def finish_recording_and_inject(
    *,
    args: object,
    repo_root: Path,
    child_fd: int,
    child_command: list[str],
    state: RecordingState,
    status: StatusFn,
    transcription_client: TranscriptionClient,
    transcription_config: TranscriptionConfig,
) -> None:
    recorded_audio = stop_recording_result(state=state, status=status)
    transcript = ""
    injected = False
    outcome = "unknown"
    error_message: str | None = None
    try:
        if recorded_audio.elapsed < args.min_duration:
            status(
                f"recording too short: {recorded_audio.elapsed:.2f}s < {args.min_duration:g}s; skipped STT"
            )
            outcome = "skipped_short_recording"
            return
        result = transcription_client.transcribe(
            transcription_request_from_recorded_audio(recorded_audio)
        )
        transcript = result.transcript
        injected = inject_transcript(status, child_fd, transcript)
        outcome = "injected" if injected else "empty_transcript"
    except RuntimeError as error:
        outcome = "stt_error"
        error_message = str(error)
        raise
    finally:
        save_and_cleanup_recorded_audio(
            args=args,
            repo_root=repo_root,
            child_command=child_command,
            recorded_audio=recorded_audio,
            transcript=transcript,
            injected=injected,
            outcome=outcome,
            error_message=error_message,
            transcription_config=transcription_config,
            status=status,
        )


def handle_fixed_text_injection(
    *,
    args: object,
    child_fd: int,
    data: bytes,
    status: StatusFn,
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

        os.write(child_fd, args.inject_text.encode())
        status(f"injected {len(args.inject_text)} chars; review text, then press Enter to send")
        start = index + len(trigger)


def handle_stt_ptt_input(
    *,
    args: object,
    child_fd: int,
    data: bytes,
    state: RecordingState,
    status: StatusFn,
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
            start_recording(
                temp_dir=args.temp_dir,
                state=state,
                status=status,
                handoff=resolve_audio_handoff(args),
            )
        state.last_trigger_at = time.monotonic()
        start = index + len(trigger)


def handle_stdin_data(
    *,
    args: object,
    child_fd: int,
    data: bytes,
    state: RecordingState,
    status: StatusFn,
) -> None:
    if args.inject_mode == "fixed-text":
        handle_fixed_text_injection(
            args=args,
            child_fd=child_fd,
            data=data,
            status=status,
        )
        return
    handle_stt_ptt_input(
        args=args,
        child_fd=child_fd,
        data=data,
        state=state,
        status=status,
    )


def maybe_finish_stt_recording(
    *,
    args: object,
    repo_root: Path,
    child_fd: int,
    child_command: list[str],
    state: RecordingState,
    status: StatusFn,
    transcription_client: TranscriptionClient,
    transcription_config: TranscriptionConfig,
) -> None:
    if not state.active() or state.last_trigger_at is None:
        return

    elapsed_since_trigger = time.monotonic() - state.last_trigger_at
    if state.elapsed() >= args.max_duration:
        status(f"max duration reached: {args.max_duration:g}s")
        try:
            finish_recording_and_inject(
                args=args,
                repo_root=repo_root,
                child_fd=child_fd,
                child_command=child_command,
                state=state,
                status=status,
                transcription_client=transcription_client,
                transcription_config=transcription_config,
            )
        except RuntimeError as error:
            status(f"stt error: {error}")
        return
    if elapsed_since_trigger >= args.release_gap:
        try:
            finish_recording_and_inject(
                args=args,
                repo_root=repo_root,
                child_fd=child_fd,
                child_command=child_command,
                state=state,
                status=status,
                transcription_client=transcription_client,
                transcription_config=transcription_config,
            )
        except RuntimeError as error:
            status(f"stt error: {error}")


def passthrough(
    *,
    args: object,
    repo_root: Path,
    pid: int,
    child_fd: int,
    child_command: list[str],
    status: StatusFn,
    transcription_client: TranscriptionClient | None = None,
    reserved_terminal_rows: int = 0,
) -> int:
    selector = selectors.DefaultSelector()
    selector.register(child_fd, selectors.EVENT_READ, "child")
    stdin_open = True
    try:
        selector.register(sys.stdin.fileno(), selectors.EVENT_READ, "stdin")
    except OSError:
        stdin_open = False
    exit_code: int | None = None
    recording_state = RecordingState()
    transcription_config: TranscriptionConfig | None = None
    active_transcription_client = transcription_client
    if args.inject_mode == "stt" or active_transcription_client is not None:
        transcription_config = transcription_config_from_args(args)
    if active_transcription_client is None and args.inject_mode == "stt":
        if transcription_config is None:
            raise RuntimeError("STT transcription config is not configured")
        active_transcription_client = create_transcription_client(
            args=args,
            repo_root=repo_root,
            config=transcription_config,
            status=status,
        )

    def handle_sigwinch(signum: int, frame: object) -> None:
        copy_window_size(child_fd, reserved_rows=reserved_terminal_rows)

    previous_sigwinch = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, handle_sigwinch)
    copy_window_size(child_fd, reserved_rows=reserved_terminal_rows)

    try:
        while True:
            if args.inject_mode == "stt":
                if active_transcription_client is None or transcription_config is None:
                    raise RuntimeError("STT transcription client is not configured")
                maybe_finish_stt_recording(
                    args=args,
                    repo_root=repo_root,
                    child_fd=child_fd,
                    child_command=child_command,
                    state=recording_state,
                    status=status,
                    transcription_client=active_transcription_client,
                    transcription_config=transcription_config,
                )

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
                            _, wait_status = os.waitpid(pid, 0)
                            exit_code = decode_wait_status(wait_status)
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
                    handle_stdin_data(
                        args=args,
                        child_fd=child_fd,
                        data=data,
                        state=recording_state,
                        status=status,
                    )
    finally:
        try:
            if recording_state.active():
                if transcription_config is None:
                    raise RuntimeError("STT transcription config is not configured")
                recorded_audio = stop_recording_result(
                    state=recording_state,
                    status=status,
                )
                save_and_cleanup_recorded_audio(
                    args=args,
                    repo_root=repo_root,
                    child_command=child_command,
                    recorded_audio=recorded_audio,
                    transcript="",
                    injected=False,
                    outcome="interrupted_recording",
                    error_message=None,
                    transcription_config=transcription_config,
                    status=status,
                )
        finally:
            try:
                if active_transcription_client is not None:
                    active_transcription_client.close()
            finally:
                signal.signal(signal.SIGWINCH, previous_sigwinch)
                selector.close()
