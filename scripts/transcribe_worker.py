#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt_core.transcription_prompt import DEFAULT_KOREAN_PHONETIC_INITIAL_PROMPT


DEFAULT_MODEL = "large-v3"
DEFAULT_LANGUAGE = "ko"
DEFAULT_INITIAL_PROMPT = DEFAULT_KOREAN_PHONETIC_INITIAL_PROMPT


class SegmentLike(Protocol):
    text: str


class TranscriptionInfoLike(Protocol):
    duration: float
    language: str
    language_probability: float


class WorkerModel(Protocol):
    def transcribe(
        self,
        audio_file: str,
        **kwargs: object,
    ) -> tuple[Iterable[SegmentLike], TranscriptionInfoLike]:
        ...


class ModelFactory(Protocol):
    def __call__(
        self,
        *,
        model: str,
        device: str,
        compute_type: str,
        download_root: str | None,
    ) -> WorkerModel:
        ...


@dataclass(frozen=True)
class WorkerConfig:
    model: str
    language: str
    device: str
    compute_type: str
    beam_size: int
    initial_prompt: str | None
    model_dir: str | None
    vad_filter: bool


def env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a persistent faster-whisper worker over stdin/stdout JSON lines."
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("STT_MODEL", DEFAULT_MODEL),
        help=f"Whisper model name or local model path. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--language",
        default=os.environ.get("STT_LANGUAGE", DEFAULT_LANGUAGE),
        help="Language code such as ko, en, or auto. Default: ko",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default=os.environ.get("STT_DEVICE", "auto"),
        help="Inference device. Default: auto",
    )
    parser.add_argument(
        "--compute-type",
        default=os.environ.get("STT_COMPUTE_TYPE", "auto"),
        help="CTranslate2 compute type. Default: auto",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=int(os.environ.get("STT_BEAM_SIZE", "5")),
        help="Beam size for decoding. Default: 5",
    )
    parser.add_argument(
        "--initial-prompt",
        default=os.environ.get("STT_INITIAL_PROMPT", DEFAULT_INITIAL_PROMPT),
        help="Prompt text to guide transcription. Default: Korean phonetic prompt. Env: STT_INITIAL_PROMPT",
    )
    parser.add_argument(
        "--model-dir",
        default=os.environ.get("STT_MODEL_DIR"),
        help="Optional model download/cache directory.",
    )
    vad_default = env_flag("STT_VAD_FILTER", True)
    vad_group = parser.add_mutually_exclusive_group()
    vad_group.add_argument(
        "--vad-filter",
        dest="vad_filter",
        action="store_true",
        default=vad_default,
        help="Enable faster-whisper VAD filtering. Default: enabled",
    )
    vad_group.add_argument(
        "--no-vad-filter",
        dest="vad_filter",
        action="store_false",
        help="Disable faster-whisper VAD filtering.",
    )
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> WorkerConfig:
    return WorkerConfig(
        model=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
        initial_prompt=args.initial_prompt,
        model_dir=args.model_dir,
        vad_filter=args.vad_filter,
    )


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    import ctranslate2

    return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"


def resolve_compute_type(device: str, compute_type: str) -> str:
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "float32"


def language_arg(language: str) -> str | None:
    return None if language == "auto" else language


def initial_prompt_arg(initial_prompt: str | None) -> str | None:
    if initial_prompt is None:
        return None
    prompt = initial_prompt.strip()
    return prompt or None


def default_model_factory(
    *,
    model: str,
    device: str,
    compute_type: str,
    download_root: str | None,
) -> WorkerModel:
    from faster_whisper import WhisperModel

    return WhisperModel(
        model,
        device=device,
        compute_type=compute_type,
        download_root=download_root,
    )


def write_response(stdout: TextIO, response: dict[str, object]) -> None:
    stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    stdout.flush()


def transcribe_audio(
    *,
    model: WorkerModel,
    audio_file: Path,
    config: WorkerConfig,
) -> tuple[str, TranscriptionInfoLike, int, float]:
    started_at = time.monotonic()
    segments, info = model.transcribe(
        str(audio_file),
        language=language_arg(config.language),
        beam_size=config.beam_size,
        initial_prompt=initial_prompt_arg(config.initial_prompt),
        vad_filter=config.vad_filter,
        condition_on_previous_text=False,
    )

    parts: list[str] = []
    segment_count = 0
    for segment in segments:
        segment_count += 1
        text = segment.text.strip()
        if text:
            parts.append(text)

    return " ".join(parts).strip(), info, segment_count, time.monotonic() - started_at


def handle_request(
    *,
    line: str,
    model: WorkerModel,
    config: WorkerConfig,
    stdout: TextIO,
    stderr: TextIO,
) -> None:
    try:
        request = json.loads(line)
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        audio_value = request.get("audio_file")
        if not isinstance(audio_value, str) or not audio_value:
            raise ValueError("request.audio_file must be a non-empty string")
        audio_file = Path(audio_value)
        if not audio_file.exists():
            raise FileNotFoundError(f"audio file not found: {audio_file}")

        transcript, info, segment_count, elapsed = transcribe_audio(
            model=model,
            audio_file=audio_file,
            config=config,
        )
        write_response(
            stdout,
            {
                "ok": True,
                "transcript": transcript,
                "segment_count": segment_count,
                "audio_duration_seconds": round(info.duration, 6),
            },
        )
        print(
            "transcribed: "
            f"audio={audio_file} language={info.language} "
            f"probability={info.language_probability:.3f} "
            f"duration={info.duration:.2f}s elapsed={elapsed:.2f}s",
            file=stderr,
            flush=True,
        )
    except Exception as error:
        write_response(stdout, {"ok": False, "error": str(error)})


def run_worker(
    config: WorkerConfig,
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    model_factory: ModelFactory = default_model_factory,
) -> int:
    device = resolve_device(config.device)
    compute_type = resolve_compute_type(device, config.compute_type)
    print(
        "loading model: "
        f"model={config.model} device={device} compute_type={compute_type}",
        file=stderr,
        flush=True,
    )
    model = model_factory(
        model=config.model,
        device=device,
        compute_type=compute_type,
        download_root=config.model_dir,
    )
    print("worker ready", file=stderr, flush=True)

    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        handle_request(
            line=line,
            model=model,
            config=config,
            stdout=stdout,
            stderr=stderr,
        )
    return 0


def main() -> int:
    return run_worker(
        config_from_args(parse_args()),
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
