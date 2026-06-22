from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence

from stt_runtime.transcription import (
    SubprocessTranscriptionClient,
    TranscriptionConfig,
    TranscriptionRequest,
    transcribe_audio,
)


class RecordingRunner:
    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: str = "hello transcript\n",
        stderr: str = "loading model\n\ntranscribed ok\n",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[tuple[Sequence[str], dict[str, Any]]] = []

    def __call__(
        self,
        command: Sequence[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(
            list(command),
            self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
        )


class SubprocessTranscriptionClientTest(unittest.TestCase):
    def test_transcribe_runs_transcribe_script_with_positive_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audio_file = repo_root / "audio.wav"
            runner = RecordingRunner()
            statuses: list[str] = []
            client = SubprocessTranscriptionClient(
                repo_root=repo_root,
                config=TranscriptionConfig(
                    model="large-v3",
                    language="ko",
                    device="cuda",
                    compute_type="float16",
                    beam_size=7,
                    initial_prompt="prompt text",
                    vad_filter=True,
                ),
                status=statuses.append,
                runner=runner,
            )

            result = client.transcribe(TranscriptionRequest(audio_file=audio_file))

            command, kwargs = runner.calls[0]
            self.assertEqual(
                list(command),
                [
                    str(repo_root / "scripts/transcribe.sh"),
                    str(audio_file),
                    "--model",
                    "large-v3",
                    "--language",
                    "ko",
                    "--device",
                    "cuda",
                    "--compute-type",
                    "float16",
                    "--beam-size",
                    "7",
                    "--initial-prompt",
                    "prompt text",
                ],
            )
            self.assertEqual(kwargs["cwd"], repo_root)
            self.assertTrue(kwargs["text"])
            self.assertTrue(kwargs["capture_output"])
            self.assertFalse(kwargs["check"])
            self.assertEqual(result.transcript, "hello transcript")
            self.assertEqual(result.stderr_lines, ("loading model", "transcribed ok"))
            self.assertEqual(
                statuses,
                ["transcribing...", "stt: loading model", "stt: transcribed ok"],
            )

    def test_transcribe_disables_vad_when_config_requests_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            runner = RecordingRunner()
            client = SubprocessTranscriptionClient(
                repo_root=repo_root,
                config=TranscriptionConfig(
                    model="tiny",
                    language="ko",
                    device="cpu",
                    compute_type="int8",
                    beam_size=1,
                    initial_prompt=None,
                    vad_filter=False,
                ),
                status=lambda message: None,
                runner=runner,
            )

            client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))

            command, _ = runner.calls[0]
            self.assertIn("--no-vad-filter", command)
            self.assertNotIn("--initial-prompt", command)

    def test_transcribe_raises_on_subprocess_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = RecordingRunner(returncode=42, stderr="boom\n")
            client = SubprocessTranscriptionClient(
                repo_root=Path(temp_dir),
                config=TranscriptionConfig(
                    model="tiny",
                    language="ko",
                    device="cpu",
                    compute_type="int8",
                    beam_size=1,
                    initial_prompt=None,
                    vad_filter=True,
                ),
                status=lambda message: None,
                runner=runner,
            )

            with self.assertRaisesRegex(RuntimeError, "exit code 42"):
                client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))

    def test_legacy_transcribe_audio_returns_string(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            runner = RecordingRunner(stdout=" legacy transcript \n")

            transcript = transcribe_audio(
                repo_root=repo_root,
                audio_file=Path("audio.wav"),
                stt_model="tiny",
                stt_language="ko",
                stt_device="cpu",
                stt_compute_type="int8",
                stt_beam_size=1,
                stt_initial_prompt=None,
                stt_no_vad_filter=True,
                status=lambda message: None,
                runner=runner,
            )

            command, _ = runner.calls[0]
            self.assertEqual(transcript, "legacy transcript")
            self.assertIn("--no-vad-filter", command)


if __name__ == "__main__":
    unittest.main()
