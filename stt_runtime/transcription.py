from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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
    audio_file: Path


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
        if self._config.initial_prompt:
            command.extend(["--initial-prompt", self._config.initial_prompt])
        if not self._config.vad_filter:
            command.append("--no-vad-filter")
        return command


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
