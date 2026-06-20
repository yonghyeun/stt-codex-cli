from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


StatusFn = Callable[[str], None]


@dataclass
class RecordingState:
    process: subprocess.Popen[bytes] | None = None
    audio_file: Path | None = None
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


def start_recording(
    *,
    temp_dir: str | None,
    state: RecordingState,
    status: StatusFn,
) -> None:
    if state.active():
        return

    audio_file = create_temp_audio(temp_dir)
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
    state.started_wall_at = datetime.now().astimezone()
    state.last_trigger_at = state.started_at
    status(f"recording started: {audio_file}")


def stop_recording(
    *,
    state: RecordingState,
    status: StatusFn,
) -> tuple[Path, float, datetime]:
    if state.process is None or state.audio_file is None:
        raise RuntimeError("recording is not running")

    process = state.process
    audio_file = state.audio_file
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

    state.process = None
    state.audio_file = None
    state.started_at = None
    state.started_wall_at = None
    state.last_trigger_at = None
    status(f"recording stopped: elapsed={elapsed:.2f}s")
    return audio_file, elapsed, started_wall_at


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
