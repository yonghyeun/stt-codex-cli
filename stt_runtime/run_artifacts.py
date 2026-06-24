from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from stt_core.run_metadata import build_run_metadata, run_id_from_timestamp
from stt_runtime.recording import StatusFn, recording_config


def resolve_run_output_dir(repo_root: Path, run_output_dir: str) -> Path:
    output_dir = Path(run_output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    return output_dir


def create_run_dir(repo_root: Path, run_output_dir: str, timestamp: datetime) -> Path:
    output_dir = resolve_run_output_dir(repo_root, run_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = run_id_from_timestamp(timestamp)
    for suffix in [None, *range(1, 1000)]:
        run_name = base_name if suffix is None else f"{base_name}-{suffix:03d}"
        run_dir = output_dir / run_name
        try:
            run_dir.mkdir()
            return run_dir
        except FileExistsError:
            continue
    raise RuntimeError(f"could not create unique run directory under {output_dir}")


def save_run_artifacts(
    *,
    repo_root: Path,
    save_run: bool,
    keep_audio: bool,
    run_output_dir: str,
    audio_file: Path,
    transcript: str,
    started_at: datetime,
    elapsed: float,
    injected: bool,
    submitted: bool,
    submit_mode: str,
    outcome: str,
    error: str | None,
    stt: dict[str, Any],
    child_command: list[str],
    child_cwd: str | None,
    status: StatusFn,
) -> Path | None:
    if not save_run:
        return None

    run_dir = create_run_dir(repo_root, run_output_dir, started_at)
    audio_output = run_dir / "audio.wav"
    transcript_output = run_dir / "transcript.txt"
    metadata_output = run_dir / "metadata.json"

    if keep_audio:
        shutil.copy2(audio_file, audio_output)
    else:
        shutil.move(str(audio_file), audio_output)
    transcript_output.write_text(transcript + "\n", encoding="utf-8")

    metadata = build_run_metadata(
        run_id=run_dir.name,
        created_at=datetime.now().astimezone(),
        recording_started_at=started_at,
        elapsed=elapsed,
        outcome=outcome,
        injected=injected,
        submitted=submitted,
        submit_mode=submit_mode,
        transcript=transcript,
        audio_file="audio.wav",
        transcript_file="transcript.txt",
        error=error,
        recording=recording_config(),
        stt=stt,
        child={
            "command": child_command,
            "cwd": child_cwd or os.getcwd(),
        },
    )
    metadata_output.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    status(f"saved run artifacts: {run_dir}")
    return run_dir
