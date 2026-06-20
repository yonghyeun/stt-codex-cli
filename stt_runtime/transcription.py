from __future__ import annotations

import subprocess
from pathlib import Path

from stt_runtime.recording import StatusFn


def transcribe_audio(
    *,
    repo_root: Path,
    audio_file: Path,
    stt_model: str,
    stt_language: str,
    stt_device: str,
    stt_compute_type: str,
    stt_beam_size: int,
    stt_initial_prompt: str | None,
    stt_no_vad_filter: bool,
    status: StatusFn,
) -> str:
    command = [
        str(repo_root / "scripts/transcribe.sh"),
        str(audio_file),
        "--model",
        stt_model,
        "--language",
        stt_language,
        "--device",
        stt_device,
        "--compute-type",
        stt_compute_type,
        "--beam-size",
        str(stt_beam_size),
    ]
    if stt_initial_prompt:
        command.extend(["--initial-prompt", stt_initial_prompt])
    if stt_no_vad_filter:
        command.append("--no-vad-filter")

    status("transcribing...")
    result = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    for line in result.stderr.splitlines():
        if line.strip():
            status(f"stt: {line.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"STT failed with exit code {result.returncode}")
    return result.stdout.strip()
