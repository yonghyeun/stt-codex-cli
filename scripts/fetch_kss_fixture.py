#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DATASET = "Bingsu/KSS_Dataset"
CONFIG = "default"
SPLIT = "train"
SOURCE_PAGE = "https://huggingface.co/datasets/Bingsu/KSS_Dataset"
LICENSE = "cc-by-nc-sa-4.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch one KSS Dataset row as a local speech fixture."
    )
    parser.add_argument(
        "--row-idx",
        type=int,
        default=0,
        help="Dataset row index to fetch. Default: 0",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Fixture output directory. Default: fixtures/generated/kss-row-<idx>",
    )
    return parser.parse_args()


def rows_api_url(row_idx: int) -> str:
    query = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": CONFIG,
            "split": SPLIT,
            "offset": row_idx,
            "length": 1,
        }
    )
    return f"https://datasets-server.huggingface.co/rows?{query}"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download(url: str, path: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        path.write_bytes(response.read())


def audio_url(row: dict) -> str:
    audio = row["audio"]
    if isinstance(audio, list) and audio:
        return audio[0]["src"]
    if isinstance(audio, dict) and "src" in audio:
        return audio["src"]
    raise ValueError("row does not contain a downloadable audio URL")


def main() -> int:
    args = parse_args()
    if args.row_idx < 0:
        print("--row-idx must be >= 0", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir or f"fixtures/generated/kss-row-{args.row_idx:05d}")
    output_dir.mkdir(parents=True, exist_ok=True)

    api_url = rows_api_url(args.row_idx)
    payload = fetch_json(api_url)
    rows = payload.get("rows") or []
    if len(rows) != 1:
        print(f"expected one row, got {len(rows)}", file=sys.stderr)
        return 1

    row_payload = rows[0]
    row = row_payload["row"]
    wav_path = output_dir / "audio.wav"
    expected_path = output_dir / "expected.txt"
    metadata_path = output_dir / "metadata.local.json"

    download(audio_url(row), wav_path)
    expected_text = row["expanded_script"].strip()
    expected_path.write_text(expected_text + "\n", encoding="utf-8")

    metadata = {
        "dataset": DATASET,
        "source_page": SOURCE_PAGE,
        "license": LICENSE,
        "config": CONFIG,
        "split": SPLIT,
        "row_idx": row_payload["row_idx"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "audio_file": str(wav_path),
        "expected_file": str(expected_path),
        "original_script": row["original_script"],
        "expanded_script": row["expanded_script"],
        "duration": row["duration"],
        "english_translation": row["english_translation"],
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"audio_file={wav_path}")
    print(f"expected_file={expected_path}")
    print(f"metadata_file={metadata_path}")
    print(f"expected={expected_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
