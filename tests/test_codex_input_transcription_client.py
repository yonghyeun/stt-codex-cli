from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
        "stt_backend": "daemon",
        "audio_handoff": "auto",
        "inject_mode": "stt",
        "disable_inject_key": False,
        "inject_key_bytes": b"\x14",
        "temp_dir": None,
        "trigger_mode": "tap",
        "max_duration": 60.0,
        "release_gap": 0.35,
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

    def test_auto_audio_handoff_uses_buffer_for_worker_speed_path(self) -> None:
        args = make_args(stt_backend="worker", save_run=False, keep_audio=False)

        self.assertEqual(codex_input.resolve_audio_handoff(args), "buffer")

    def test_auto_audio_handoff_uses_buffer_for_default_daemon_speed_path(self) -> None:
        args = make_args(save_run=False, keep_audio=False)

        self.assertEqual(args.stt_backend, "daemon")

        self.assertEqual(codex_input.resolve_audio_handoff(args), "buffer")

    def test_auto_audio_handoff_uses_file_when_artifacts_are_requested(self) -> None:
        self.assertEqual(codex_input.resolve_audio_handoff(make_args(save_run=True)), "file")
        self.assertEqual(codex_input.resolve_audio_handoff(make_args(keep_audio=True)), "file")

    def test_auto_audio_handoff_uses_file_for_subprocess_backend(self) -> None:
        args = make_args(stt_backend="subprocess")

        self.assertEqual(codex_input.resolve_audio_handoff(args), "file")

    def test_finish_recording_sends_buffer_request_without_temp_file(self) -> None:
        state = RecordingState(
            process=FinishedProcess(),  # type: ignore[arg-type]
            audio_file=None,
            audio_chunks=[b"RIFF ", b"fake wav"],
            started_at=time.monotonic() - 1.0,
            started_wall_at=datetime(2026, 6, 23, tzinfo=timezone.utc),
            last_trigger_at=time.monotonic() - 1.0,
            handoff="buffer",
        )
        client = FakeTranscriptionClient()
        config = codex_input.transcription_config_from_args(make_args())
        statuses: list[str] = []
        read_fd, write_fd = os.pipe()

        try:
            codex_input.finish_recording_and_inject(
                args=make_args(audio_handoff="buffer"),
                repo_root=Path.cwd(),
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

        self.assertEqual(injected, "fake transcript")
        self.assertEqual(len(client.requests), 1)
        self.assertIsNone(client.requests[0].audio_file)
        self.assertEqual(client.requests[0].audio_bytes, b"RIFF fake wav")
        self.assertIn("released in-memory audio buffer", statuses)

    def test_buffer_recording_without_audio_bytes_raises_runtime_error(self) -> None:
        state = RecordingState(
            process=FinishedProcess(),  # type: ignore[arg-type]
            audio_file=None,
            audio_chunks=[],
            started_at=time.monotonic() - 1.0,
            started_wall_at=datetime(2026, 6, 23, tzinfo=timezone.utc),
            last_trigger_at=time.monotonic() - 1.0,
            handoff="buffer",
        )
        client = FakeTranscriptionClient()
        config = codex_input.transcription_config_from_args(make_args())
        read_fd, write_fd = os.pipe()

        try:
            with self.assertRaisesRegex(RuntimeError, "audio bytes"):
                codex_input.finish_recording_and_inject(
                    args=make_args(audio_handoff="buffer"),
                    repo_root=Path.cwd(),
                    child_fd=write_fd,
                    child_command=["codex"],
                    state=state,
                    status=lambda message: None,
                    transcription_client=client,
                    transcription_config=config,
                )
        finally:
            os.close(write_fd)
            os.close(read_fd)

    def test_tap_trigger_starts_recording_and_consumes_key(self) -> None:
        state = RecordingState()
        statuses: list[str] = []
        read_fd, write_fd = os.pipe()

        def fake_start_recording(**kwargs: object) -> None:
            state.process = FinishedProcess()  # type: ignore[assignment]
            state.started_at = time.monotonic()
            state.last_trigger_at = state.started_at
            kwargs["status"]("recording started: in-memory audio buffer")  # type: ignore[index,operator]

        try:
            with patch.object(codex_input, "start_recording", fake_start_recording):
                codex_input.handle_stdin_data(
                    args=make_args(),
                    child_fd=write_fd,
                    data=b"before\x14after",
                    state=state,
                    status=statuses.append,
                )
            os.close(write_fd)
            write_fd = -1
            forwarded = os.read(read_fd, 4096)
        finally:
            if write_fd >= 0:
                os.close(write_fd)
            os.close(read_fd)

        self.assertTrue(state.active())
        self.assertFalse(state.stop_requested)
        self.assertEqual(forwarded, b"beforeafter")
        self.assertIn("recording started: in-memory audio buffer", statuses)

    def test_second_tap_requests_stop_without_forwarding_key(self) -> None:
        state = RecordingState(
            process=FinishedProcess(),  # type: ignore[arg-type]
            started_at=time.monotonic() - 1.0,
            last_trigger_at=time.monotonic() - 1.0,
        )
        read_fd, write_fd = os.pipe()

        try:
            codex_input.handle_stdin_data(
                args=make_args(),
                child_fd=write_fd,
                data=b"\x14",
                state=state,
                status=lambda message: None,
            )
            os.close(write_fd)
            write_fd = -1
            forwarded = os.read(read_fd, 4096)
        finally:
            if write_fd >= 0:
                os.close(write_fd)
            os.close(read_fd)

        self.assertTrue(state.stop_requested)
        self.assertEqual(forwarded, b"")

    def test_tap_mode_ignores_release_gap_until_stop_is_requested(self) -> None:
        state = RecordingState(
            process=FinishedProcess(),  # type: ignore[arg-type]
            started_at=time.monotonic() - 2.0,
            last_trigger_at=time.monotonic() - 2.0,
        )
        called = False

        def fake_finish_recording_and_inject(**kwargs: object) -> None:
            nonlocal called
            called = True

        with patch.object(
            codex_input,
            "finish_recording_and_inject",
            fake_finish_recording_and_inject,
        ):
            codex_input.maybe_finish_stt_recording(
                args=make_args(release_gap=0.01),
                repo_root=Path.cwd(),
                child_fd=-1,
                child_command=["codex"],
                state=state,
                status=lambda message: None,
                transcription_client=FakeTranscriptionClient(),
                transcription_config=codex_input.transcription_config_from_args(make_args()),
            )

        self.assertFalse(called)

    def test_tap_mode_finishes_when_stop_is_requested(self) -> None:
        state = RecordingState(
            process=FinishedProcess(),  # type: ignore[arg-type]
            started_at=time.monotonic() - 1.0,
            last_trigger_at=time.monotonic() - 1.0,
            stop_requested=True,
        )
        called = False

        def fake_finish_recording_and_inject(**kwargs: object) -> None:
            nonlocal called
            called = True

        with patch.object(
            codex_input,
            "finish_recording_and_inject",
            fake_finish_recording_and_inject,
        ):
            codex_input.maybe_finish_stt_recording(
                args=make_args(),
                repo_root=Path.cwd(),
                child_fd=-1,
                child_command=["codex"],
                state=state,
                status=lambda message: None,
                transcription_client=FakeTranscriptionClient(),
                transcription_config=codex_input.transcription_config_from_args(make_args()),
            )

        self.assertTrue(called)


if __name__ == "__main__":
    unittest.main()
