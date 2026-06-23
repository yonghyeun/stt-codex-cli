#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import transcribe_worker


DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE_TYPE = "auto"
DEFAULT_IDLE_TIMEOUT_SECONDS = 300.0


class DaemonModel(transcribe_worker.WorkerModel, Protocol):
    pass


class ModelFactory(Protocol):
    def __call__(
        self,
        *,
        model: str,
        device: str,
        compute_type: str,
        download_root: str | None,
    ) -> DaemonModel:
        ...


@dataclass(frozen=True)
class DaemonConfig:
    model: str
    device: str
    compute_type: str
    model_dir: str | None
    config_id: str


class TranscriptionDaemon:
    def __init__(
        self,
        *,
        config: DaemonConfig,
        model: DaemonModel,
    ) -> None:
        self._config = config
        self._model = model
        self._lock = threading.Lock()
        self._model_load_count = 1

    @property
    def config_id(self) -> str:
        return self._config.config_id

    def handle_request(self, request: dict[str, object]) -> dict[str, object]:
        received_at = time.monotonic()
        try:
            requested_config_id = request.get("config_id")
            if requested_config_id != self._config.config_id:
                raise ValueError(
                    f"config mismatch: requested {requested_config_id!r}, "
                    f"daemon {self._config.config_id!r}"
                )

            audio_input = transcribe_worker.audio_input_from_request(request)
            worker_config = request_worker_config(request, self._config)

            with self._lock:
                queue_wait_seconds = time.monotonic() - received_at
                transcript, info, segment_count, elapsed = transcribe_worker.transcribe_audio(
                    model=self._model,
                    audio_source=audio_input.source,
                    config=worker_config,
                )

            return {
                "ok": True,
                "transcript": transcript,
                "segment_count": segment_count,
                "audio_duration_seconds": round(info.duration, 6),
                "handoff": audio_input.handoff,
                "config_id": self._config.config_id,
                "model": self._config.model,
                "device": self._config.device,
                "compute_type": self._config.compute_type,
                "model_load_count": self._model_load_count,
                "queue_wait_seconds": round(queue_wait_seconds, 6),
                "elapsed_seconds": round(elapsed, 6),
            }
        except Exception as error:
            return {"ok": False, "error": str(error), "config_id": self._config.config_id}


def request_worker_config(
    request: dict[str, object],
    daemon_config: DaemonConfig,
) -> transcribe_worker.WorkerConfig:
    return transcribe_worker.WorkerConfig(
        model=daemon_config.model,
        language=string_request_value(request, "language", transcribe_worker.DEFAULT_LANGUAGE),
        device=daemon_config.device,
        compute_type=daemon_config.compute_type,
        beam_size=int_request_value(request, "beam_size", 5),
        initial_prompt=optional_string_request_value(request, "initial_prompt"),
        model_dir=daemon_config.model_dir,
        vad_filter=bool_request_value(request, "vad_filter", True),
    )


def string_request_value(
    request: dict[str, object],
    key: str,
    default: str,
) -> str:
    value = request.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"request.{key} must be a non-empty string")
    return value


def optional_string_request_value(
    request: dict[str, object],
    key: str,
) -> str | None:
    value = request.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"request.{key} must be a string or null")
    return value


def int_request_value(
    request: dict[str, object],
    key: str,
    default: int,
) -> int:
    value = request.get(key, default)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"request.{key} must be a positive integer")
    return value


def bool_request_value(
    request: dict[str, object],
    key: str,
    default: bool,
) -> bool:
    value = request.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"request.{key} must be a boolean")
    return value


def load_daemon(
    config: DaemonConfig,
    *,
    model_factory: ModelFactory = transcribe_worker.default_model_factory,
) -> TranscriptionDaemon:
    device = transcribe_worker.resolve_device(config.device)
    compute_type = transcribe_worker.resolve_compute_type(device, config.compute_type)
    resolved_config = DaemonConfig(
        model=config.model,
        device=device,
        compute_type=compute_type,
        model_dir=config.model_dir,
        config_id=config.config_id,
    )
    model = model_factory(
        model=resolved_config.model,
        device=resolved_config.device,
        compute_type=resolved_config.compute_type,
        download_root=resolved_config.model_dir,
    )
    return TranscriptionDaemon(config=resolved_config, model=model)


def request_daemon(
    socket_path: Path,
    request: dict[str, object],
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout_seconds)
        client.connect(str(socket_path))
        payload = json.dumps(request, ensure_ascii=False).encode() + b"\n"
        client.sendall(payload)
        line = _readline(client)
    response = json.loads(line)
    if not isinstance(response, dict):
        raise RuntimeError("daemon returned invalid response")
    return response


def serve_daemon(
    *,
    config: DaemonConfig,
    socket_path: Path,
    idle_timeout_seconds: float | None,
    model_factory: ModelFactory = transcribe_worker.default_model_factory,
    stop_event: threading.Event | None = None,
) -> int:
    stop_event = stop_event or threading.Event()
    daemon = load_daemon(config, model_factory=model_factory)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    _prepare_socket_path(socket_path)

    threads: list[threading.Thread] = []
    activity_lock = threading.Lock()
    last_activity = time.monotonic()
    active_connections = 0

    def mark_connection_started() -> None:
        nonlocal active_connections, last_activity
        with activity_lock:
            active_connections += 1
            last_activity = time.monotonic()

    def mark_connection_done() -> None:
        nonlocal active_connections, last_activity
        with activity_lock:
            active_connections -= 1
            last_activity = time.monotonic()

    def idle_timeout_reached() -> bool:
        with activity_lock:
            if active_connections > 0:
                return False
            return time.monotonic() - last_activity >= idle_timeout_seconds

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(socket_path))
        server.listen()
        server.settimeout(0.05)
        try:
            while not stop_event.is_set():
                if (
                    idle_timeout_seconds is not None
                    and idle_timeout_reached()
                ):
                    break
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                mark_connection_started()
                thread = threading.Thread(
                    target=_handle_connection,
                    args=(connection, daemon, mark_connection_done),
                )
                thread.start()
                threads.append(thread)
        finally:
            for thread in threads:
                thread.join(timeout=2.0)
            socket_path.unlink(missing_ok=True)
    return 0


def _prepare_socket_path(socket_path: Path) -> None:
    if not socket_path.exists():
        return
    try:
        request_daemon(socket_path, {"probe": True}, timeout_seconds=0.1)
    except OSError:
        socket_path.unlink(missing_ok=True)
        return
    raise RuntimeError(f"daemon socket is already active: {socket_path}")


def _handle_connection(
    connection: socket.socket,
    daemon: TranscriptionDaemon,
    on_done: Callable[[], None] | None = None,
) -> None:
    try:
        with connection:
            try:
                line = _readline(connection)
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("request must be a JSON object")
                response = daemon.handle_request(request)
            except Exception as error:
                response = {"ok": False, "error": str(error), "config_id": daemon.config_id}
            connection.sendall(json.dumps(response, ensure_ascii=False).encode() + b"\n")
    finally:
        if on_done is not None:
            on_done()


def _readline(connection: socket.socket) -> str:
    chunks: list[bytes] = []
    while True:
        chunk = connection.recv(1)
        if not chunk:
            break
        if chunk == b"\n":
            break
        chunks.append(chunk)
    if not chunks:
        raise RuntimeError("daemon closed without response")
    return b"".join(chunks).decode()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a shared STT daemon.")
    parser.add_argument("--socket", required=True, help="Unix domain socket path.")
    parser.add_argument("--config-id", required=True, help="Load-time config id.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default=DEFAULT_DEVICE)
    parser.add_argument("--compute-type", default=DEFAULT_COMPUTE_TYPE)
    parser.add_argument("--model-dir", default=None)
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=DEFAULT_IDLE_TIMEOUT_SECONDS,
        help=f"Seconds before idle daemon exits. Default: {DEFAULT_IDLE_TIMEOUT_SECONDS:g}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return serve_daemon(
        config=DaemonConfig(
            model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            model_dir=args.model_dir,
            config_id=args.config_id,
        ),
        socket_path=Path(args.socket),
        idle_timeout_seconds=args.idle_timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
