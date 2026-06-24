from __future__ import annotations

from datetime import datetime
from typing import Any

from stt_core.transcript import transcript_has_text


def run_id_from_timestamp(timestamp: datetime) -> str:
    milliseconds = timestamp.microsecond // 1000
    return f"{timestamp:%Y%m%d-%H%M%S}-{milliseconds:03d}-stt-codex"


def build_run_metadata(
    *,
    run_id: str,
    created_at: datetime,
    recording_started_at: datetime,
    elapsed: float,
    outcome: str,
    injected: bool,
    submitted: bool,
    submit_mode: str,
    transcript: str,
    audio_file: str,
    transcript_file: str,
    error: str | None,
    recording: dict[str, str],
    stt: dict[str, Any],
    child: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": created_at.isoformat(timespec="milliseconds"),
        "recording_started_at": recording_started_at.isoformat(timespec="milliseconds"),
        "elapsed_seconds": round(elapsed, 3),
        "outcome": outcome,
        "injected": injected,
        "submitted": submitted,
        "submit_mode": submit_mode,
        "transcript_chars": len(transcript),
        "transcript_has_text": transcript_has_text(transcript),
        "audio_file": audio_file,
        "transcript_file": transcript_file,
        "error": error,
        "recording": recording,
        "stt": stt,
        "child": child,
    }
