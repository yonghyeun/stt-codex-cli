#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import ctranslate2
from faster_whisper import WhisperModel


DEFAULT_MODEL = "large-v3"
DEFAULT_LANGUAGE = "ko"


def env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a local audio file with faster-whisper."
    )
    parser.add_argument("audio_file", help="Path to a WAV or other ffmpeg-readable file.")
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
        "--model-dir",
        default=os.environ.get("STT_MODEL_DIR"),
        help="Optional model download/cache directory.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write transcript text.",
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


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"


def resolve_compute_type(device: str, compute_type: str) -> str:
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "float32"


def language_arg(language: str) -> str | None:
    return None if language == "auto" else language


def main() -> int:
    args = parse_args()
    audio_file = Path(args.audio_file)
    if not audio_file.exists():
        print(f"audio file not found: {audio_file}", file=sys.stderr)
        return 2

    device = resolve_device(args.device)
    compute_type = resolve_compute_type(device, args.compute_type)
    started_at = time.monotonic()

    print(
        "loading model: "
        f"model={args.model} device={device} compute_type={compute_type}",
        file=sys.stderr,
    )

    model = WhisperModel(
        args.model,
        device=device,
        compute_type=compute_type,
        download_root=args.model_dir,
    )

    segments, info = model.transcribe(
        str(audio_file),
        language=language_arg(args.language),
        beam_size=args.beam_size,
        vad_filter=args.vad_filter,
        condition_on_previous_text=False,
    )

    parts: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            parts.append(text)

    transcript = " ".join(parts).strip()
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(transcript + "\n", encoding="utf-8")

    elapsed = time.monotonic() - started_at
    print(transcript)
    print(
        "transcribed: "
        f"language={info.language} probability={info.language_probability:.3f} "
        f"duration={info.duration:.2f}s elapsed={elapsed:.2f}s",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
