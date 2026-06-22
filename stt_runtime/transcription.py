from __future__ import annotations

import base64
import json
import subprocess
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

from stt_runtime.recording import StatusFn


@dataclass(frozen=True)
class TranscriptionConfig:
    model: str
    language: str
    device: str
    compute_type: str
    beam_size: int
    initial_prompt: str | None
    vad_filter: bool


@dataclass(frozen=True)
class TranscriptionRequest:
    audio_file: Path | None = None
    audio_bytes: bytes | None = None
    audio_format: str = "wav"

    def __post_init__(self) -> None:
        has_file = self.audio_file is not None
        has_buffer = self.audio_bytes is not None
        if has_file == has_buffer:
            raise ValueError("exactly one of audio_file or audio_bytes is required")
        if self.audio_bytes is not None and not self.audio_bytes:
            raise ValueError("audio_bytes must not be empty")
        if not self.audio_format:
            raise ValueError("audio_format must not be empty")


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str
    stderr_lines: tuple[str, ...]


class TranscriptionClient(Protocol):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        ...

    def close(self) -> None:
        ...


class SubprocessRunner(Protocol):
    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        ...


class WorkerProcess(Protocol):
    stdin: TextIO | None
    stdout: TextIO | None
    stderr: TextIO | None

    def poll(self) -> int | None:
        ...

    def terminate(self) -> None:
        ...

    def kill(self) -> None:
        ...

    def wait(self, timeout: float | None = None) -> int:
        ...


class WorkerProcessFactory(Protocol):
    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        text: bool,
        stdin: int,
        stdout: int,
        stderr: int,
        bufsize: int,
    ) -> WorkerProcess:
        ...


class SubprocessTranscriptionClient:
    def __init__(
        self,
        *,
        repo_root: Path,
        config: TranscriptionConfig,
        status: StatusFn,
        runner: SubprocessRunner = subprocess.run,
    ) -> None:
        self._repo_root = repo_root
        self._config = config
        self._status = status
        self._runner = runner

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        command = self._build_command(request)

        self._status("transcribing...")
        result = self._runner(
            command,
            cwd=self._repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        stderr_lines = tuple(
            line.strip() for line in result.stderr.splitlines() if line.strip()
        )
        for line in stderr_lines:
            self._status(f"stt: {line}")
        if result.returncode != 0:
            raise RuntimeError(f"STT failed with exit code {result.returncode}")
        return TranscriptionResult(
            transcript=result.stdout.strip(),
            stderr_lines=stderr_lines,
        )

    def close(self) -> None:
        return None

    def _build_command(self, request: TranscriptionRequest) -> list[str]:
        if request.audio_file is None:
            raise RuntimeError("subprocess transcription requires an audio file")
        command = [
            str(self._repo_root / "scripts/transcribe.sh"),
            str(request.audio_file),
            "--model",
            self._config.model,
            "--language",
            self._config.language,
            "--device",
            self._config.device,
            "--compute-type",
            self._config.compute_type,
            "--beam-size",
            str(self._config.beam_size),
        ]
        if self._config.initial_prompt is not None:
            command.extend(["--initial-prompt", self._config.initial_prompt])
        if not self._config.vad_filter:
            command.append("--no-vad-filter")
        return command


class PersistentWorkerTranscriptionClient:
    def __init__(
        self,
        *,
        repo_root: Path,
        config: TranscriptionConfig,
        status: StatusFn,
        process_factory: WorkerProcessFactory = subprocess.Popen,
    ) -> None:
        self._repo_root = repo_root
        self._config = config
        self._status = status
        self._process_factory = process_factory
        self._process: WorkerProcess | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        process = self._ensure_worker()
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("STT worker pipes are not available")

        self._status("transcribing...")
        stderr_start = len(self._stderr_lines)
        payload = json.dumps(self._request_payload(request), ensure_ascii=False)
        try:
            process.stdin.write(payload + "\n")
            process.stdin.flush()
        except BrokenPipeError as error:
            raise RuntimeError("STT worker closed before accepting request") from error

        line = process.stdout.readline()
        if not line:
            raise RuntimeError("STT worker stopped without response")

        try:
            response = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError("STT worker returned invalid JSON") from error

        if not isinstance(response, dict):
            raise RuntimeError("STT worker returned invalid response")
        if response.get("ok") is not True:
            error = response.get("error")
            if not isinstance(error, str) or not error:
                error = "unknown worker error"
            raise RuntimeError(f"STT worker failed: {error}")

        transcript = response.get("transcript")
        if not isinstance(transcript, str):
            raise RuntimeError("STT worker response did not include transcript")
        return TranscriptionResult(
            transcript=transcript.strip(),
            stderr_lines=tuple(self._stderr_lines[stderr_start:]),
        )

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return

        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass

        if process.poll() is not None:
            self._join_stderr_thread()
            return

        try:
            process.wait(timeout=0.5)
            self._join_stderr_thread()
            return
        except subprocess.TimeoutExpired:
            pass

        if process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)
        self._join_stderr_thread()

    def _ensure_worker(self) -> WorkerProcess:
        if self._process is not None:
            if self._process.poll() is not None:
                raise RuntimeError("STT worker exited before request")
            return self._process

        command = self._build_command()
        self._status("starting stt worker...")
        process = self._process_factory(
            command,
            cwd=self._repo_root,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("STT worker pipes are not available")
        self._process = process
        self._start_stderr_thread(process)
        return process

    def _start_stderr_thread(self, process: WorkerProcess) -> None:
        if process.stderr is None:
            return
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(process.stderr,),
            daemon=True,
        )
        self._stderr_thread.start()

    def _drain_stderr(self, stderr: TextIO) -> None:
        for raw_line in stderr:
            line = raw_line.strip()
            if not line:
                continue
            self._stderr_lines.append(line)
            self._status(f"stt: {line}")

    def _join_stderr_thread(self) -> None:
        if self._stderr_thread is None:
            return
        self._stderr_thread.join(timeout=1.0)
        self._stderr_thread = None

    def _build_command(self) -> list[str]:
        command = [
            str(self._repo_root / "scripts/transcribe_worker.sh"),
            "--model",
            self._config.model,
            "--language",
            self._config.language,
            "--device",
            self._config.device,
            "--compute-type",
            self._config.compute_type,
            "--beam-size",
            str(self._config.beam_size),
        ]
        if self._config.initial_prompt is not None:
            command.extend(["--initial-prompt", self._config.initial_prompt])
        if not self._config.vad_filter:
            command.append("--no-vad-filter")
        return command

    def _request_payload(self, request: TranscriptionRequest) -> dict[str, str]:
        if request.audio_bytes is not None:
            return {
                "audio_bytes_b64": base64.b64encode(request.audio_bytes).decode("ascii"),
                "audio_format": request.audio_format,
            }
        if request.audio_file is None:
            raise RuntimeError("worker transcription requires audio input")
        return {"audio_file": str(request.audio_file)}


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
    runner: SubprocessRunner = subprocess.run,
) -> str:
    client = SubprocessTranscriptionClient(
        repo_root=repo_root,
        config=TranscriptionConfig(
            model=stt_model,
            language=stt_language,
            device=stt_device,
            compute_type=stt_compute_type,
            beam_size=stt_beam_size,
            initial_prompt=stt_initial_prompt,
            vad_filter=not stt_no_vad_filter,
        ),
        status=status,
        runner=runner,
    )
    try:
        return client.transcribe(TranscriptionRequest(audio_file=audio_file)).transcript
    finally:
        client.close()
