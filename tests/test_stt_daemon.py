from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Sequence

from scripts import stt_daemon


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeInfo:
    duration = 1.25
    language = "ko"
    language_probability = 0.99


class FakeDaemonModel:
    def __init__(self, transcripts: Sequence[str], *, delay_seconds: float = 0.0) -> None:
        self._transcripts = list(transcripts)
        self._delay_seconds = delay_seconds
        self.calls: list[tuple[object, dict[str, Any]]] = []

    def transcribe(
        self,
        audio_file: object,
        **kwargs: Any,
    ) -> tuple[list[FakeSegment], FakeInfo]:
        self.calls.append((audio_file, kwargs))
        if self._delay_seconds:
            time.sleep(self._delay_seconds)
        transcript = self._transcripts.pop(0)
        return [FakeSegment(transcript)], FakeInfo()


class FakeDaemonModelFactory:
    def __init__(self, transcripts: Sequence[str], *, delay_seconds: float = 0.0) -> None:
        self.model = FakeDaemonModel(transcripts, delay_seconds=delay_seconds)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> FakeDaemonModel:
        self.calls.append(kwargs)
        return self.model


def wait_for_socket(socket_path: Path) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if socket_path.exists():
            return
        time.sleep(0.01)
    raise AssertionError(f"socket not ready: {socket_path}")


class SttDaemonTest(unittest.TestCase):
    def test_daemon_reuses_loaded_model_for_multiple_socket_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            socket_path = root / "stt.sock"
            first_audio = root / "first.wav"
            second_audio = root / "second.wav"
            first_audio.write_bytes(b"fake wav")
            second_audio.write_bytes(b"fake wav")
            model_factory = FakeDaemonModelFactory(["first transcript", "second"])
            stop_event = threading.Event()
            server = threading.Thread(
                target=stt_daemon.serve_daemon,
                kwargs={
                    "config": stt_daemon.DaemonConfig(
                        model="large-v3",
                        device="cpu",
                        compute_type="int8",
                        model_dir=None,
                        config_id="large-v3-cpu-int8",
                    ),
                    "socket_path": socket_path,
                    "idle_timeout_seconds": None,
                    "model_factory": model_factory,
                    "stop_event": stop_event,
                },
                daemon=True,
            )
            server.start()
            wait_for_socket(socket_path)

            try:
                first = stt_daemon.request_daemon(
                    socket_path,
                    {
                        "config_id": "large-v3-cpu-int8",
                        "audio_file": str(first_audio),
                        "language": "ko",
                        "beam_size": 5,
                        "initial_prompt": "prompt",
                        "vad_filter": True,
                    },
                )
                second = stt_daemon.request_daemon(
                    socket_path,
                    {
                        "config_id": "large-v3-cpu-int8",
                        "audio_file": str(second_audio),
                        "language": "en",
                        "beam_size": 1,
                        "initial_prompt": "other",
                        "vad_filter": False,
                    },
                )
            finally:
                stop_event.set()
                server.join(timeout=2.0)

            self.assertTrue(first["ok"])
            self.assertTrue(second["ok"])
            self.assertEqual(first["transcript"], "first transcript")
            self.assertEqual(second["transcript"], "second")
            self.assertEqual(first["config_id"], "large-v3-cpu-int8")
            self.assertEqual(first["model_load_count"], 1)
            self.assertEqual(second["model_load_count"], 1)
            self.assertEqual(len(model_factory.calls), 1)
            self.assertEqual(len(model_factory.model.calls), 2)
            self.assertEqual(model_factory.model.calls[1][1]["language"], "en")
            self.assertEqual(model_factory.model.calls[1][1]["beam_size"], 1)
            self.assertFalse(model_factory.model.calls[1][1]["vad_filter"])
            self.assertEqual(first["request_id"], "req-000001")
            self.assertEqual(second["request_id"], "req-000002")
            self.assertEqual(first["request_state"], "done")
            self.assertEqual(second["request_state"], "done")
            self.assertEqual(first["queue_rank_at_enqueue"], 1)
            self.assertEqual(second["queue_rank_at_enqueue"], 1)
            self.assertIsInstance(first["queued_at"], float)
            self.assertIsInstance(first["started_at"], float)
            self.assertIsInstance(first["finished_at"], float)
            self.assertLessEqual(first["queued_at"], first["started_at"])
            self.assertLessEqual(first["started_at"], first["finished_at"])

    def test_daemon_rejects_config_mismatch(self) -> None:
        model_factory = FakeDaemonModelFactory(["unused"])
        daemon = stt_daemon.TranscriptionDaemon(
            config=stt_daemon.DaemonConfig(
                model="large-v3",
                device="cpu",
                compute_type="int8",
                model_dir=None,
                config_id="large-v3-cpu-int8",
            ),
            model=model_factory(
                model="large-v3",
                device="cpu",
                compute_type="int8",
                download_root=None,
            ),
        )

        response = daemon.handle_request(
            {
                "config_id": "medium-cpu-int8",
                "audio_file": "missing.wav",
            }
        )

        self.assertFalse(response["ok"])
        self.assertIn("config mismatch", response["error"])

    def test_concurrent_requests_are_serialized_and_report_queue_wait(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            socket_path = root / "stt.sock"
            first_audio = root / "first.wav"
            second_audio = root / "second.wav"
            first_audio.write_bytes(b"fake wav")
            second_audio.write_bytes(b"fake wav")
            model_factory = FakeDaemonModelFactory(
                ["first transcript", "second"],
                delay_seconds=0.05,
            )
            stop_event = threading.Event()
            server = threading.Thread(
                target=stt_daemon.serve_daemon,
                kwargs={
                    "config": stt_daemon.DaemonConfig(
                        model="large-v3",
                        device="cpu",
                        compute_type="int8",
                        model_dir=None,
                        config_id="large-v3-cpu-int8",
                    ),
                    "socket_path": socket_path,
                    "idle_timeout_seconds": None,
                    "model_factory": model_factory,
                    "stop_event": stop_event,
                },
                daemon=True,
            )
            server.start()
            wait_for_socket(socket_path)
            responses: list[dict[str, object]] = []

            def send(audio_file: Path) -> None:
                responses.append(
                    stt_daemon.request_daemon(
                        socket_path,
                        {
                            "config_id": "large-v3-cpu-int8",
                            "request_id": f"{audio_file.stem}-request",
                            "audio_file": str(audio_file),
                            "language": "ko",
                            "beam_size": 5,
                            "initial_prompt": None,
                            "vad_filter": True,
                        },
                    )
                )

            try:
                first_client = threading.Thread(target=send, args=(first_audio,))
                second_client = threading.Thread(target=send, args=(second_audio,))
                first_client.start()
                time.sleep(0.01)
                second_client.start()
                first_client.join(timeout=2.0)
                second_client.join(timeout=2.0)
            finally:
                stop_event.set()
                server.join(timeout=2.0)

            self.assertEqual(len(responses), 2)
            self.assertTrue(all(response["ok"] for response in responses))
            self.assertTrue(
                any(float(response["queue_wait_seconds"]) > 0 for response in responses)
            )
            by_request_id = {
                str(response["request_id"]): response for response in responses
            }
            self.assertEqual(set(by_request_id), {"first-request", "second-request"})
            self.assertEqual(
                by_request_id["first-request"]["queue_rank_at_enqueue"],
                1,
            )
            self.assertEqual(
                by_request_id["second-request"]["queue_rank_at_enqueue"],
                2,
            )
            self.assertEqual(
                [Path(call[0]).name for call in model_factory.model.calls],
                ["first.wav", "second.wav"],
            )

    def test_idle_timeout_does_not_stop_daemon_during_active_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            socket_path = root / "stt.sock"
            audio = root / "audio.wav"
            audio.write_bytes(b"fake wav")
            model_factory = FakeDaemonModelFactory(
                ["slow transcript"],
                delay_seconds=2.5,
            )
            stop_event = threading.Event()
            server = threading.Thread(
                target=stt_daemon.serve_daemon,
                kwargs={
                    "config": stt_daemon.DaemonConfig(
                        model="large-v3",
                        device="cpu",
                        compute_type="int8",
                        model_dir=None,
                        config_id="large-v3-cpu-int8",
                    ),
                    "socket_path": socket_path,
                    "idle_timeout_seconds": 0.02,
                    "model_factory": model_factory,
                    "stop_event": stop_event,
                },
                daemon=True,
            )
            server.start()
            wait_for_socket(socket_path)

            response_holder: list[dict[str, object]] = []

            def send_request() -> None:
                response_holder.append(
                    stt_daemon.request_daemon(
                        socket_path,
                        {
                            "config_id": "large-v3-cpu-int8",
                            "audio_file": str(audio),
                            "language": "ko",
                            "beam_size": 5,
                            "initial_prompt": None,
                            "vad_filter": True,
                        },
                        timeout_seconds=5.0,
                    )
                )

            client = threading.Thread(target=send_request)
            try:
                client.start()
                time.sleep(2.2)
                self.assertTrue(socket_path.exists())
                client.join(timeout=5.0)
            finally:
                stop_event.set()
                server.join(timeout=2.0)

            self.assertEqual(len(response_holder), 1)
            response = response_holder[0]
            self.assertTrue(response["ok"])
            self.assertEqual(response["transcript"], "slow transcript")


if __name__ == "__main__":
    unittest.main()
