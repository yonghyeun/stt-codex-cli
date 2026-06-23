from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO


StatusFn = Callable[[str], None]
AudioHandoff = str


@dataclass(frozen=True)
class RecordedAudio:
    audio_file: Path | None
    audio_bytes: bytes | None
    elapsed: float
    started_at: datetime
    handoff: AudioHandoff


@dataclass
class RecordingState:
    process: subprocess.Popen[bytes] | None = None
    audio_file: Path | None = None
    audio_chunks: list[bytes] | None = None
    audio_reader: threading.Thread | None = None
    handoff: AudioHandoff = "file"
    started_at: float | None = None
    started_wall_at: datetime | None = None
    last_trigger_at: float | None = None

    def active(self) -> bool:
        return self.process is not None

    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        return time.monotonic() - self.started_at


def create_temp_audio(temp_dir: str | None) -> Path:
    if temp_dir is not None:
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="stt-codex-",
        suffix=".wav",
        dir=temp_dir,
        delete=False,
    ) as temp_file:
        return Path(temp_file.name)


def recording_config() -> dict[str, str]:
    return {
        "device": os.environ.get("STT_RECORD_DEVICE", "default"),
        "format": os.environ.get("STT_RECORD_FORMAT", "S16_LE"),
        "rate": os.environ.get("STT_RECORD_RATE", "16000"),
        "channels": os.environ.get("STT_RECORD_CHANNELS", "1"),
    }


def drain_audio_stdout(stdout: BinaryIO, audio_chunks: list[bytes]) -> None:
    while True:
        data = stdout.read(65536)
        if not data:
            return
        audio_chunks.append(data)


def start_recording(
    *,
    temp_dir: str | None,
    state: RecordingState,
    status: StatusFn,
    handoff: AudioHandoff = "file",
) -> None:
    if state.active():
        return
    if handoff not in {"file", "buffer"}:
        raise RuntimeError(f"unsupported audio handoff: {handoff}")

    config = recording_config()
    command = [
        "arecord",
        "-D",
        config["device"],
        "-f",
        config["format"],
        "-r",
        config["rate"],
        "-c",
        config["channels"],
    ]
    audio_file: Path | None = None
    audio_chunks: list[bytes] | None = None
    stdout: int | None = subprocess.DEVNULL
    if handoff == "file":
        audio_file = create_temp_audio(temp_dir)
        command.append(str(audio_file))
    else:
        command.extend(["-t", "wav"])
        audio_chunks = []
        stdout = subprocess.PIPE
    state.process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=subprocess.DEVNULL,
    )
    state.audio_file = audio_file
    state.audio_chunks = audio_chunks
    state.audio_reader = None
    state.handoff = handoff
    if handoff == "buffer":
        if state.process.stdout is None or audio_chunks is None:
            raise RuntimeError("recording stdout pipe is not available")
        state.audio_reader = threading.Thread(
            target=drain_audio_stdout,
            args=(state.process.stdout, audio_chunks),
            daemon=True,
        )
        state.audio_reader.start()
    state.started_at = time.monotonic()
    state.started_wall_at = datetime.now().astimezone()
    state.last_trigger_at = state.started_at
    if audio_file is not None:
        status(f"recording started: {audio_file}")
    else:
        status("recording started: in-memory audio buffer")


def stop_recording_result(
    *,
    state: RecordingState,
    status: StatusFn,
) -> RecordedAudio:
    if state.process is None:
        raise RuntimeError("recording is not running")

    process = state.process
    audio_file = state.audio_file
    audio_reader = state.audio_reader
    audio_chunks = state.audio_chunks
    handoff = state.handoff
    started_wall_at = state.started_wall_at or datetime.now().astimezone()
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
    if audio_reader is not None:
        audio_reader.join(timeout=2)

    audio_bytes = b"".join(audio_chunks or []) if handoff == "buffer" else None
    if handoff == "file" and audio_file is None:
        raise RuntimeError("file recording did not produce an audio file")
    if handoff == "buffer" and audio_bytes is None:
        raise RuntimeError("buffer recording did not produce audio bytes")

    state.process = None
    state.audio_file = None
    state.audio_chunks = None
    state.audio_reader = None
    state.handoff = "file"
    state.started_at = None
    state.started_wall_at = None
    state.last_trigger_at = None
    status(f"recording stopped: elapsed={elapsed:.2f}s")
    return RecordedAudio(
        audio_file=audio_file,
        audio_bytes=audio_bytes,
        elapsed=elapsed,
        started_at=started_wall_at,
        handoff=handoff,
    )


def stop_recording(
    *,
    state: RecordingState,
    status: StatusFn,
) -> tuple[Path, float, datetime]:
    recorded_audio = stop_recording_result(state=state, status=status)
    if recorded_audio.audio_file is None:
        raise RuntimeError("recording did not produce an audio file")
    return recorded_audio.audio_file, recorded_audio.elapsed, recorded_audio.started_at


def cleanup_audio(
    *,
    keep_audio: bool,
    audio_file: Path,
    status: StatusFn,
) -> None:
    if keep_audio:
        status(f"kept audio: {audio_file}")
        return
    try:
        audio_file.unlink()
        status("deleted temporary audio")
    except FileNotFoundError:
        return


def cleanup_recorded_audio(
    *,
    keep_audio: bool,
    recorded_audio: RecordedAudio,
    status: StatusFn,
) -> None:
    if recorded_audio.audio_file is not None:
        cleanup_audio(
            keep_audio=keep_audio,
            audio_file=recorded_audio.audio_file,
            status=status,
        )
        return
    status("released in-memory audio buffer")
