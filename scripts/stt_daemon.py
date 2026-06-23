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
DEFAULT_IDLE_TIMEOUT_SECONDS = 600.0


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


@dataclass
class RequestRecord:
    sequence: int
    request_id: str
    state: str
    queued_at: float
    queued_monotonic: float
    queue_rank_at_enqueue: int
    started_at: float | None = None
    started_monotonic: float | None = None
    finished_at: float | None = None
    finished_monotonic: float | None = None
    client_pid: int | str = "unknown"
    client_uid: int | str = "unknown"
    client_gid: int | str = "unknown"


class TranscriptionDaemon:
    def __init__(
        self,
        *,
        config: DaemonConfig,
        model: DaemonModel,
    ) -> None:
        self._config = config
        self._model = model
        self._condition = threading.Condition()
        self._queued_requests: list[RequestRecord] = []
        self._running_request: RequestRecord | None = None
        self._next_sequence = 0
        self._started_monotonic = time.monotonic()
        self._last_request_finished_monotonic: float | None = None
        self._model_load_count = 1

    @property
    def config_id(self) -> str:
        return self._config.config_id

    def handle_request(self, request: dict[str, object]) -> dict[str, object]:
        record = self._enqueue_request(request)
        try:
            requested_config_id = request.get("config_id")
            if requested_config_id != self._config.config_id:
                raise ValueError(
                    f"config mismatch: requested {requested_config_id!r}, "
                    f"daemon {self._config.config_id!r}"
                )

            audio_input = transcribe_worker.audio_input_from_request(request)
            worker_config = request_worker_config(request, self._config)

            self._start_request(record)
            queue_wait_seconds = self._queue_wait_seconds(record)
            transcript, info, segment_count, elapsed = transcribe_worker.transcribe_audio(
                model=self._model,
                audio_source=audio_input.source,
                config=worker_config,
            )
            self._finish_request(record, "done")

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
                **request_record_metadata(record),
            }
        except Exception as error:
            self._finish_request(record, "error")
            return {
                "ok": False,
                "error": str(error),
                "config_id": self._config.config_id,
                **request_record_metadata(record),
            }

    def handle_stats_request(
        self,
        request: dict[str, object],
        *,
        idle_timeout_seconds: float | None,
    ) -> dict[str, object]:
        requested_config_id = request.get("config_id")
        if requested_config_id is not None and requested_config_id != self._config.config_id:
            return {
                "ok": False,
                "type": "stats",
                "error": (
                    f"config mismatch: requested {requested_config_id!r}, "
                    f"daemon {self._config.config_id!r}"
                ),
                "config_id": self._config.config_id,
            }

        own_request_id = optional_stats_request_id(request)
        with self._condition:
            running = self._running_request
            queued = list(self._queued_requests)
            requests: list[dict[str, object]] = []
            if running is not None:
                requests.append(request_summary(running, queue_rank=1))
            start_rank = 2 if running is not None else 1
            requests.extend(
                request_summary(record, queue_rank=rank)
                for rank, record in enumerate(queued, start=start_rank)
            )
            own_request = next(
                (
                    summary
                    for summary in requests
                    if summary["request_id"] == own_request_id
                ),
                None,
            )
            idle_timeout_remaining = self._idle_timeout_remaining_seconds(
                idle_timeout_seconds
            )
            daemon_state = "busy" if running is not None else "queued" if queued else "idle"

        return {
            "ok": True,
            "type": "stats",
            "config_id": self._config.config_id,
            "daemon_state": daemon_state,
            "running_request": request_summary(running, queue_rank=1)
            if running is not None
            else None,
            "queued_request_count": len(queued),
            "active_request_count": len(requests),
            "requests": requests,
            "own_request": own_request,
            "own_queue_rank": own_request["queue_rank"] if own_request is not None else None,
            "own_request_state": own_request["request_state"]
            if own_request is not None
            else "unknown",
            "idle_timeout_remaining_seconds": idle_timeout_remaining,
        }

    def idle_timeout_reached(self, idle_timeout_seconds: float | None) -> bool:
        if idle_timeout_seconds is None:
            return False
        if self._last_request_finished_monotonic is None:
            return False
        remaining = self._idle_timeout_remaining_seconds(idle_timeout_seconds)
        return remaining is not None and remaining <= 0

    def _idle_timeout_remaining_seconds(
        self,
        idle_timeout_seconds: float | None,
    ) -> float | None:
        if idle_timeout_seconds is None:
            return None
        if self._running_request is not None or self._queued_requests:
            return None
        baseline = self._last_request_finished_monotonic or self._started_monotonic
        elapsed = time.monotonic() - baseline
        return round(max(0.0, idle_timeout_seconds - elapsed), 6)

    def _enqueue_request(self, request: dict[str, object]) -> RequestRecord:
        with self._condition:
            self._next_sequence += 1
            sequence = self._next_sequence
            record = RequestRecord(
                sequence=sequence,
                request_id=request_id_from_request(request, sequence),
                state="queued",
                queued_at=time.time(),
                queued_monotonic=time.monotonic(),
                queue_rank_at_enqueue=len(self._queued_requests)
                + (1 if self._running_request is not None else 0)
                + 1,
            )
            self._queued_requests.append(record)
            self._condition.notify_all()
            return record

    def _start_request(self, record: RequestRecord) -> None:
        with self._condition:
            while (
                self._running_request is not None
                or not self._queued_requests
                or self._queued_requests[0] is not record
            ):
                self._condition.wait()
            self._queued_requests.pop(0)
            self._running_request = record
            record.state = "running"
            record.started_at = time.time()
            record.started_monotonic = time.monotonic()

    def _finish_request(self, record: RequestRecord, state: str) -> None:
        with self._condition:
            if record in self._queued_requests:
                self._queued_requests.remove(record)
            if self._running_request is record:
                self._running_request = None
            if record.finished_at is None:
                record.finished_at = time.time()
                record.finished_monotonic = time.monotonic()
                self._last_request_finished_monotonic = record.finished_monotonic
            record.state = state
            self._condition.notify_all()

    @staticmethod
    def _queue_wait_seconds(record: RequestRecord) -> float:
        if record.started_monotonic is None:
            return 0.0
        return record.started_monotonic - record.queued_monotonic


def request_id_from_request(request: dict[str, object], sequence: int) -> str:
    request_id = request.get("request_id")
    if request_id is None:
        return f"req-{sequence:06d}"
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request.request_id must be a non-empty string")
    return request_id


def optional_stats_request_id(request: dict[str, object]) -> str | None:
    request_id = request.get("request_id")
    if request_id is None:
        return None
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request.request_id must be a non-empty string")
    return request_id


def request_record_metadata(record: RequestRecord) -> dict[str, object]:
    metadata: dict[str, object] = {
        "request_id": record.request_id,
        "request_state": record.state,
        "queue_rank_at_enqueue": record.queue_rank_at_enqueue,
        "queued_at": round(record.queued_at, 6),
        "client_pid": record.client_pid,
        "client_uid": record.client_uid,
        "client_gid": record.client_gid,
    }
    if record.started_at is not None:
        metadata["started_at"] = round(record.started_at, 6)
    if record.finished_at is not None:
        metadata["finished_at"] = round(record.finished_at, 6)
    return metadata


def request_summary(record: RequestRecord, *, queue_rank: int) -> dict[str, object]:
    summary = request_record_metadata(record)
    summary["state"] = record.state
    summary["queue_rank"] = queue_rank
    return summary


def is_stats_request(request: dict[str, object]) -> bool:
    return request.get("type") == "stats"


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
    active_connections = 0

    def mark_connection_started() -> None:
        nonlocal active_connections
        with activity_lock:
            active_connections += 1

    def mark_connection_done() -> None:
        nonlocal active_connections
        with activity_lock:
            active_connections -= 1

    def idle_timeout_reached() -> bool:
        with activity_lock:
            if active_connections > 0:
                return False
        return daemon.idle_timeout_reached(idle_timeout_seconds)

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
                    args=(
                        connection,
                        daemon,
                        mark_connection_done,
                        idle_timeout_seconds,
                    ),
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
    idle_timeout_seconds: float | None = None,
) -> None:
    try:
        with connection:
            try:
                line = _readline(connection)
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("request must be a JSON object")
                if is_stats_request(request):
                    response = daemon.handle_stats_request(
                        request,
                        idle_timeout_seconds=idle_timeout_seconds,
                    )
                else:
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
