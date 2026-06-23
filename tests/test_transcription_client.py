from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import Any, Sequence

from scripts import transcribe_worker
from stt_features import codex_input
from stt_runtime.transcription import (
    PersistentWorkerTranscriptionClient,
    SubprocessTranscriptionClient,
    TranscriptionConfig,
    TranscriptionRequest,
    TranscriptionResult,
    daemon_config_id,
    daemon_socket_path,
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


class FakeWorkerStdin:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.closed = False
        self.flush_count = 0

    def write(self, value: str) -> int:
        self.lines.append(value)
        return len(value)

    def flush(self) -> None:
        self.flush_count += 1

    def close(self) -> None:
        self.closed = True


class FakeWorkerStdout:
    def __init__(self, lines: Sequence[str]) -> None:
        self._lines = list(lines)

    def __iter__(self) -> FakeWorkerStdout:
        return self

    def __next__(self) -> str:
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def readline(self) -> str:
        if not self._lines:
            return ""
        return self._lines.pop(0)


class FakeWorkerProcess:
    def __init__(
        self,
        stdout_lines: Sequence[str],
        stderr_lines: Sequence[str] | None = None,
    ) -> None:
        self.stdin = FakeWorkerStdin()
        self.stdout = FakeWorkerStdout(stdout_lines)
        self.stderr = FakeWorkerStdout(stderr_lines or [])
        self.terminated = False
        self.killed = False
        self.wait_calls: list[float | None] = []
        self._returncode: int | None = None

    def poll(self) -> int | None:
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True
        self._returncode = 0

    def kill(self) -> None:
        self.killed = True
        self._returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if self._returncode is None:
            self._returncode = 0
        return self._returncode


class FakeWorkerFactory:
    def __init__(
        self,
        stdout_lines: Sequence[str],
        stderr_lines: Sequence[str] | None = None,
    ) -> None:
        self.stdout_lines = stdout_lines
        self.stderr_lines = stderr_lines or []
        self.calls: list[tuple[Sequence[str], dict[str, Any]]] = []
        self.processes: list[FakeWorkerProcess] = []

    def __call__(self, command: Sequence[str], **kwargs: Any) -> FakeWorkerProcess:
        self.calls.append((list(command), kwargs))
        process = FakeWorkerProcess(self.stdout_lines, self.stderr_lines)
        self.processes.append(process)
        return process


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeInfo:
    duration = 1.25
    language = "ko"
    language_probability = 0.99


class FakeWorkerModel:
    def __init__(self, transcripts: Sequence[str]) -> None:
        self._transcripts = list(transcripts)
        self.calls: list[tuple[object, dict[str, Any]]] = []

    def transcribe(
        self,
        audio_file: object,
        **kwargs: Any,
    ) -> tuple[list[FakeSegment], FakeInfo]:
        captured_audio = audio_file
        if hasattr(audio_file, "read"):
            captured_audio = audio_file.read()
        self.calls.append((captured_audio, kwargs))
        transcript = self._transcripts.pop(0)
        return [FakeSegment(transcript)], FakeInfo()


class FakeWorkerModelFactory:
    def __init__(self, transcripts: Sequence[str]) -> None:
        self.model = FakeWorkerModel(transcripts)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> FakeWorkerModel:
        self.calls.append(kwargs)
        return self.model


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

    def test_transcribe_can_pass_empty_initial_prompt_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = RecordingRunner()
            client = SubprocessTranscriptionClient(
                repo_root=Path(temp_dir),
                config=TranscriptionConfig(
                    model="tiny",
                    language="ko",
                    device="cpu",
                    compute_type="int8",
                    beam_size=1,
                    initial_prompt="",
                    vad_filter=True,
                ),
                status=lambda message: None,
                runner=runner,
            )

            client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))

            command, _ = runner.calls[0]
            self.assertIn("--initial-prompt", command)
            self.assertEqual(command[command.index("--initial-prompt") + 1], "")

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


class DaemonConfigTest(unittest.TestCase):
    def test_daemon_config_id_uses_only_load_time_config(self) -> None:
        config = TranscriptionConfig(
            model="large-v3",
            language="ko",
            device="cuda",
            compute_type="int8_float16",
            beam_size=5,
            initial_prompt="prompt",
            vad_filter=True,
        )

        self.assertEqual(
            daemon_config_id(config),
            daemon_config_id(
                replace(
                    config,
                    language="en",
                    beam_size=1,
                    initial_prompt="different",
                    vad_filter=False,
                )
            ),
        )
        self.assertNotEqual(
            daemon_config_id(config),
            daemon_config_id(replace(config, model="medium")),
        )
        self.assertNotEqual(
            daemon_config_id(config),
            daemon_config_id(replace(config, device="cpu")),
        )
        self.assertNotEqual(
            daemon_config_id(config),
            daemon_config_id(replace(config, compute_type="float16")),
        )

    def test_daemon_socket_path_is_config_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TranscriptionConfig(
                model="Systran/faster-whisper-large-v3",
                language="ko",
                device="cuda",
                compute_type="int8_float16",
                beam_size=5,
                initial_prompt=None,
                vad_filter=True,
            )

            socket_path = daemon_socket_path(config, socket_dir=Path(temp_dir))

            self.assertEqual(socket_path.parent, Path(temp_dir))
            self.assertEqual(socket_path.suffix, ".sock")
            self.assertIn("systran-faster-whisper-large-v3", socket_path.name)
            self.assertIn("cuda", socket_path.name)
            self.assertIn("int8_float16", socket_path.name)


class PersistentWorkerTranscriptionClientTest(unittest.TestCase):
    def test_second_request_reuses_single_worker_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            factory = FakeWorkerFactory(
                [
                    '{"ok": true, "transcript": "first"}\n',
                    '{"ok": true, "transcript": "second"}\n',
                ]
            )
            statuses: list[str] = []
            client = PersistentWorkerTranscriptionClient(
                repo_root=repo_root,
                config=TranscriptionConfig(
                    model="large-v3",
                    language="ko",
                    device="cuda",
                    compute_type="float16",
                    beam_size=5,
                    initial_prompt="prompt text",
                    vad_filter=True,
                ),
                status=statuses.append,
                process_factory=factory,
            )

            first = client.transcribe(TranscriptionRequest(audio_file=Path("a.wav")))
            second = client.transcribe(TranscriptionRequest(audio_file=Path("b.wav")))

            self.assertEqual(first, TranscriptionResult("first", ()))
            self.assertEqual(second, TranscriptionResult("second", ()))
            self.assertEqual(len(factory.calls), 1)
            command, kwargs = factory.calls[0]
            self.assertEqual(command[0], str(repo_root / "scripts/transcribe_worker.sh"))
            self.assertIn("--model", command)
            self.assertIn("large-v3", command)
            self.assertEqual(kwargs["cwd"], repo_root)
            self.assertTrue(kwargs["text"])
            self.assertEqual(factory.processes[0].stdin.lines, [
                '{"audio_file": "a.wav"}\n',
                '{"audio_file": "b.wav"}\n',
            ])
            self.assertEqual(
                statuses,
                ["starting stt worker...", "transcribing...", "transcribing..."],
            )

    def test_buffer_request_sends_base64_audio_to_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = FakeWorkerFactory(['{"ok": true, "transcript": "buffered"}\n'])
            client = PersistentWorkerTranscriptionClient(
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
                process_factory=factory,
            )

            result = client.transcribe(
                TranscriptionRequest(audio_bytes=b"RIFF fake wav", audio_format="wav")
            )

            self.assertEqual(result.transcript, "buffered")
            payload = json.loads(factory.processes[0].stdin.lines[0])
            self.assertNotIn("audio_file", payload)
            self.assertEqual(payload["audio_format"], "wav")
            self.assertEqual(
                payload["audio_bytes_b64"],
                base64.b64encode(b"RIFF fake wav").decode("ascii"),
            )

    def test_worker_command_can_pass_empty_initial_prompt_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = FakeWorkerFactory(['{"ok": true, "transcript": "done"}\n'])
            client = PersistentWorkerTranscriptionClient(
                repo_root=Path(temp_dir),
                config=TranscriptionConfig(
                    model="tiny",
                    language="ko",
                    device="cpu",
                    compute_type="int8",
                    beam_size=1,
                    initial_prompt="",
                    vad_filter=True,
                ),
                status=lambda message: None,
                process_factory=factory,
            )

            client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))

            command, _ = factory.calls[0]
            self.assertIn("--initial-prompt", command)
            self.assertEqual(command[command.index("--initial-prompt") + 1], "")

    def test_close_terminates_worker_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            factory = FakeWorkerFactory(['{"ok": true, "transcript": "done"}\n'])
            client = PersistentWorkerTranscriptionClient(
                repo_root=Path(temp_dir),
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
                process_factory=factory,
            )
            client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))

            client.close()

            process = factory.processes[0]
            self.assertTrue(process.stdin.closed)
            self.assertFalse(process.terminated)
            self.assertFalse(process.killed)
            self.assertEqual(process.wait_calls, [0.5])

    def test_worker_error_response_raises_runtime_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = PersistentWorkerTranscriptionClient(
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
                process_factory=FakeWorkerFactory(
                    ['{"ok": false, "error": "audio file not found"}\n']
                ),
            )

            with self.assertRaisesRegex(RuntimeError, "audio file not found"):
                client.transcribe(TranscriptionRequest(audio_file=Path("missing.wav")))

    def test_worker_response_metadata_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            client = PersistentWorkerTranscriptionClient(
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
                process_factory=FakeWorkerFactory(
                    [
                        json.dumps(
                            {
                                "ok": True,
                                "transcript": "done",
                                "config_id": "large-v3-cuda-int8_float16",
                                "model_load_count": 1,
                                "queue_wait_seconds": 0.125,
                            }
                        )
                        + "\n"
                    ]
                ),
            )

            result = client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))

            self.assertEqual(result.transcript, "done")
            self.assertEqual(result.metadata["config_id"], "large-v3-cuda-int8_float16")
            self.assertEqual(result.metadata["model_load_count"], 1)
            self.assertEqual(result.metadata["queue_wait_seconds"], 0.125)

    def test_worker_stderr_is_relayed_through_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statuses: list[str] = []
            client = PersistentWorkerTranscriptionClient(
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
                status=statuses.append,
                process_factory=FakeWorkerFactory(
                    ['{"ok": true, "transcript": "done"}\n'],
                    stderr_lines=["loading model\n", "worker ready\n"],
                ),
            )

            client.transcribe(TranscriptionRequest(audio_file=Path("audio.wav")))
            client.close()

            self.assertIn("stt: loading model", statuses)
            self.assertIn("stt: worker ready", statuses)


class TranscriptionClientFactoryTest(unittest.TestCase):
    def test_default_backend_falls_back_to_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TranscriptionConfig(
                model="tiny",
                language="ko",
                device="cpu",
                compute_type="int8",
                beam_size=1,
                initial_prompt=None,
                vad_filter=True,
            )

            client = codex_input.create_transcription_client(
                args=object(),
                repo_root=Path(temp_dir),
                config=config,
                status=lambda message: None,
            )

            self.assertIsInstance(client, SubprocessTranscriptionClient)

    def test_worker_backend_selects_persistent_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TranscriptionConfig(
                model="tiny",
                language="ko",
                device="cpu",
                compute_type="int8",
                beam_size=1,
                initial_prompt=None,
                vad_filter=True,
            )

            client = codex_input.create_transcription_client(
                args=type("Args", (), {"stt_backend": "worker"})(),
                repo_root=Path(temp_dir),
                config=config,
                status=lambda message: None,
            )

            self.assertIsInstance(client, PersistentWorkerTranscriptionClient)


class TranscribeWorkerScriptTest(unittest.TestCase):
    def test_worker_loads_model_once_for_multiple_wav_path_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_audio = root / "first.wav"
            second_audio = root / "second.wav"
            first_audio.write_bytes(b"fake wav")
            second_audio.write_bytes(b"fake wav")
            model_factory = FakeWorkerModelFactory([" first transcript ", "second"])
            args = transcribe_worker.WorkerConfig(
                model="large-v3",
                language="ko",
                device="cpu",
                compute_type="int8",
                beam_size=3,
                initial_prompt="prompt",
                model_dir=None,
                vad_filter=True,
            )
            stdin = StringIO(
                f'{{"audio_file": "{first_audio}"}}\n'
                f'{{"audio_file": "{second_audio}"}}\n'
            )
            stdout = StringIO()
            stderr = StringIO()

            exit_code = transcribe_worker.run_worker(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                model_factory=model_factory,
            )

            responses = [line for line in stdout.getvalue().splitlines() if line]
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(model_factory.calls), 1)
            self.assertEqual(len(model_factory.model.calls), 2)
            self.assertIn('"transcript": "first transcript"', responses[0])
            self.assertIn('"transcript": "second"', responses[1])
            self.assertIn("worker ready", stderr.getvalue())

    def test_worker_accepts_wav_buffer_request(self) -> None:
        audio_bytes = b"RIFF fake wav"
        model_factory = FakeWorkerModelFactory(["buffer transcript"])
        args = transcribe_worker.WorkerConfig(
            model="tiny",
            language="ko",
            device="cpu",
            compute_type="int8",
            beam_size=1,
            initial_prompt=None,
            model_dir=None,
            vad_filter=True,
        )
        stdin = StringIO(
            json.dumps(
                {
                    "audio_bytes_b64": base64.b64encode(audio_bytes).decode("ascii"),
                    "audio_format": "wav",
                }
            )
            + "\n"
        )
        stdout = StringIO()
        stderr = StringIO()

        exit_code = transcribe_worker.run_worker(
            args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            model_factory=model_factory,
        )

        response = json.loads(stdout.getvalue().strip())
        self.assertEqual(exit_code, 0)
        self.assertTrue(response["ok"])
        self.assertEqual(response["handoff"], "buffer")
        self.assertEqual(model_factory.model.calls[0][0], audio_bytes)


if __name__ == "__main__":
    unittest.main()
