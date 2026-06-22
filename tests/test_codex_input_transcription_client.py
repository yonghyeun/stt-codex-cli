from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from stt_features import codex_input
from stt_runtime.recording import RecordingState
from stt_runtime.transcription import (
    TranscriptionRequest,
    TranscriptionResult,
)


class FinishedProcess:
    def poll(self) -> int:
        return 0


class FakeTranscriptionClient:
    def __init__(self, transcript: str = "fake transcript") -> None:
        self.transcript = transcript
        self.requests: list[TranscriptionRequest] = []
        self.closed = False

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        self.requests.append(request)
        return TranscriptionResult(
            transcript=self.transcript,
            stderr_lines=("fake stderr",),
        )

    def close(self) -> None:
        self.closed = True


def make_args(**overrides: object) -> SimpleNamespace:
    values = {
        "min_duration": 0.15,
        "save_run": False,
        "keep_audio": False,
        "run_output_dir": "output/runs",
        "cwd": None,
        "stt_model": "large-v3",
        "stt_language": "ko",
        "stt_device": "auto",
        "stt_compute_type": "auto",
        "stt_beam_size": 5,
        "stt_initial_prompt": "prompt",
        "stt_no_vad_filter": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class CodexInputTranscriptionClientTest(unittest.TestCase):
    def test_transcription_config_from_args_converts_negative_vad_boundary(self) -> None:
        config = codex_input.transcription_config_from_args(
            make_args(stt_no_vad_filter=True)
        )

        self.assertEqual(config.model, "large-v3")
        self.assertFalse(config.vad_filter)

    def test_finish_recording_uses_supplied_client(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audio_file = root / "audio.wav"
            audio_file.write_bytes(b"fake wav")
            state = RecordingState(
                process=FinishedProcess(),  # type: ignore[arg-type]
                audio_file=audio_file,
                started_at=time.monotonic() - 1.0,
                started_wall_at=datetime(2026, 6, 23, tzinfo=timezone.utc),
                last_trigger_at=time.monotonic() - 1.0,
            )
            client = FakeTranscriptionClient()
            config = codex_input.transcription_config_from_args(make_args())
            statuses: list[str] = []
            read_fd, write_fd = os.pipe()

            try:
                codex_input.finish_recording_and_inject(
                    args=make_args(),
                    repo_root=root,
                    child_fd=write_fd,
                    child_command=["codex"],
                    state=state,
                    status=statuses.append,
                    transcription_client=client,
                    transcription_config=config,
                )
                os.close(write_fd)
                write_fd = -1
                injected = os.read(read_fd, 4096).decode()
            finally:
                if write_fd >= 0:
                    os.close(write_fd)
                os.close(read_fd)

            self.assertEqual(
                client.requests,
                [TranscriptionRequest(audio_file=audio_file)],
            )
            self.assertEqual(injected, "fake transcript")
            self.assertFalse(audio_file.exists())
            self.assertIn(
                "injected transcript 15 chars; review text, then press Enter to send",
                statuses,
            )


if __name__ == "__main__":
    unittest.main()
