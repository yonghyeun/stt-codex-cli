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
    RecordingState,
    cleanup_audio,
    start_recording,
    stop_recording,
)
from stt_runtime.run_artifacts import save_run_artifacts
from stt_runtime.terminal import copy_window_size
from stt_runtime.transcription import (
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
    raise RuntimeError(f"unsupported STT backend: {backend}")


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
    audio_file, elapsed, started_at = stop_recording(state=state, status=status)
    transcript = ""
    injected = False
    outcome = "unknown"
    error_message: str | None = None
    try:
        if elapsed < args.min_duration:
            status(
                f"recording too short: {elapsed:.2f}s < {args.min_duration:g}s; skipped STT"
            )
            outcome = "skipped_short_recording"
            return
        result = transcription_client.transcribe(
            TranscriptionRequest(audio_file=audio_file)
        )
        transcript = result.transcript
        injected = inject_transcript(status, child_fd, transcript)
        outcome = "injected" if injected else "empty_transcript"
    except RuntimeError as error:
        outcome = "stt_error"
        error_message = str(error)
        raise
    finally:
        save_run_artifacts(
            repo_root=repo_root,
            save_run=args.save_run,
            keep_audio=args.keep_audio,
            run_output_dir=args.run_output_dir,
            audio_file=audio_file,
            transcript=transcript,
            started_at=started_at,
            elapsed=elapsed,
            injected=injected,
            outcome=outcome,
            error=error_message,
            stt=transcription_metadata(transcription_config),
            child_command=child_command,
            child_cwd=args.cwd,
            status=status,
        )
        cleanup_audio(
            keep_audio=args.keep_audio,
            audio_file=audio_file,
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
            start_recording(temp_dir=args.temp_dir, state=state, status=status)
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
        copy_window_size(child_fd)

    previous_sigwinch = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, handle_sigwinch)
    copy_window_size(child_fd)

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
                audio_file, elapsed, started_at = stop_recording(
                    state=recording_state,
                    status=status,
                )
                save_run_artifacts(
                    repo_root=repo_root,
                    save_run=args.save_run,
                    keep_audio=args.keep_audio,
                    run_output_dir=args.run_output_dir,
                    audio_file=audio_file,
                    transcript="",
                    started_at=started_at,
                    elapsed=elapsed,
                    injected=False,
                    outcome="interrupted_recording",
                    error=None,
                    stt=transcription_metadata(transcription_config),
                    child_command=child_command,
                    child_cwd=args.cwd,
                    status=status,
                )
                cleanup_audio(
                    keep_audio=args.keep_audio,
                    audio_file=audio_file,
                    status=status,
                )
        finally:
            try:
                if active_transcription_client is not None:
                    active_transcription_client.close()
            finally:
                signal.signal(signal.SIGWINCH, previous_sigwinch)
                selector.close()
