#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

from compare_transcript import normalize
from faster_whisper import WhisperModel
from transcribe import DEFAULT_LANGUAGE, DEFAULT_MODEL, language_arg, resolve_compute_type, resolve_device


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run STT over a generated fixture suite and compare transcripts."
    )
    parser.add_argument("manifest", help="Fixture suite manifest JSON.")
    parser.add_argument(
        "--fixture-root",
        help="Generated fixture root. Default: fixtures/generated/<manifest id>",
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
        "--model-dir",
        default=os.environ.get("STT_MODEL_DIR"),
        help="Optional model download/cache directory.",
    )
    parser.add_argument(
        "--output",
        help="Output JSON path. Default: output/suite/<manifest id>-<model>-<device>-<compute>.json",
    )
    parser.add_argument(
        "--require",
        choices=("exact", "normalized", "none"),
        default="normalized",
        help="Failure threshold. Default: normalized",
    )
    return parser.parse_args()


def load_manifest(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fixture_dir(fixture_root: Path, row_idx: int) -> Path:
    return fixture_root / f"kss-row-{row_idx:05d}"


def transcribe_audio(model: WhisperModel, audio_file: Path, args: argparse.Namespace) -> tuple[str, float]:
    started_at = time.monotonic()
    segments, _ = model.transcribe(
        str(audio_file),
        language=language_arg(args.language),
        beam_size=args.beam_size,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    parts = [segment.text.strip() for segment in segments if segment.text.strip()]
    return " ".join(parts).strip(), time.monotonic() - started_at


def result_ok(result: dict, required: str) -> bool:
    if required == "none":
        return True
    return bool(result[f"{required}_match"])


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    suite_id = manifest["id"]
    fixture_root = Path(args.fixture_root or f"fixtures/generated/{suite_id}")

    device = resolve_device(args.device)
    compute_type = resolve_compute_type(device, args.compute_type)
    output_path = Path(
        args.output
        or f"output/suite/{suite_id}-{slug(args.model)}-{device}-{compute_type}.json"
    )

    print(
        "loading model: "
        f"model={args.model} device={device} compute_type={compute_type}",
        flush=True,
    )
    model = WhisperModel(
        args.model,
        device=device,
        compute_type=compute_type,
        download_root=args.model_dir,
    )

    suite_started_at = time.monotonic()
    results = []
    for fixture in manifest["fixtures"]:
        row_idx = int(fixture["row_idx"])
        directory = fixture_dir(fixture_root, row_idx)
        audio_file = directory / "audio.wav"
        expected_file = directory / "expected.txt"
        if not audio_file.exists() or not expected_file.exists():
            raise FileNotFoundError(
                f"missing generated fixture for row {row_idx}: run scripts/fetch_kss_fixture.py --manifest {args.manifest}"
            )

        expected = expected_file.read_text(encoding="utf-8").strip()
        actual, elapsed = transcribe_audio(model, audio_file, args)
        exact_match = expected == actual
        normalized_match = normalize(expected) == normalize(actual)
        result = {
            "row_idx": row_idx,
            "label": fixture["label"],
            "expected": expected,
            "actual": actual,
            "exact_match": exact_match,
            "normalized_match": normalized_match,
            "elapsed": round(elapsed, 3),
        }
        results.append(result)
        status = "PASS" if result_ok(result, args.require) else "FAIL"
        print(
            f"{status} row={row_idx:05d} exact={exact_match} normalized={normalized_match} elapsed={elapsed:.2f}s"
        )

    summary = {
        "suite_id": suite_id,
        "manifest": args.manifest,
        "model": args.model,
        "device": device,
        "compute_type": compute_type,
        "required_match": args.require,
        "elapsed": round(time.monotonic() - suite_started_at, 3),
        "total": len(results),
        "exact_pass": sum(1 for result in results if result["exact_match"]),
        "normalized_pass": sum(1 for result in results if result["normalized_match"]),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"output={output_path}")

    failures = [result for result in results if not result_ok(result, args.require)]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
