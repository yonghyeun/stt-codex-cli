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
        description="Fetch KSS Dataset rows as local speech fixtures."
    )
    parser.add_argument(
        "--row-idx",
        type=int,
        default=0,
        help="Dataset row index to fetch. Default: 0. Ignored when --manifest is used.",
    )
    parser.add_argument(
        "--manifest",
        help="Fixture suite manifest JSON. Fetches every fixture row into fixtures/generated/<manifest id>/.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Fixture output directory. Default: fixtures/generated/kss-row-<idx> or fixtures/generated/<manifest id>",
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


def fetch_fixture(row_idx: int, output_dir: Path, expected_text: str | None = None) -> dict:
    if row_idx < 0:
        print("--row-idx must be >= 0", file=sys.stderr)
        raise SystemExit(2)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_url = rows_api_url(row_idx)
    payload = fetch_json(api_url)
    rows = payload.get("rows") or []
    if len(rows) != 1:
        raise RuntimeError(f"expected one row, got {len(rows)}")

    row_payload = rows[0]
    row = row_payload["row"]
    wav_path = output_dir / "audio.wav"
    expected_path = output_dir / "expected.txt"
    metadata_path = output_dir / "metadata.local.json"

    download(audio_url(row), wav_path)
    source_expected = row["expanded_script"].strip()
    if expected_text is not None and expected_text.strip() != source_expected:
        raise RuntimeError(
            f"manifest expected text does not match row {row_idx}: {expected_text!r} != {source_expected!r}"
        )
    expected_text = source_expected
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

    return {
        "audio_file": str(wav_path),
        "expected_file": str(expected_path),
        "metadata_file": str(metadata_path),
        "expected": expected_text,
    }


def main() -> int:
    args = parse_args()
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        root = Path(args.output_dir or f"fixtures/generated/{manifest['id']}")
        for fixture in manifest["fixtures"]:
            row_idx = int(fixture["row_idx"])
            output_dir = root / f"kss-row-{row_idx:05d}"
            result = fetch_fixture(row_idx, output_dir, fixture.get("expected"))
            print(
                f"row_idx={row_idx} audio_file={result['audio_file']} expected={result['expected']}"
            )
        return 0

    result = fetch_fixture(
        args.row_idx,
        Path(args.output_dir or f"fixtures/generated/kss-row-{args.row_idx:05d}"),
    )
    print(f"audio_file={result['audio_file']}")
    print(f"expected_file={result['expected_file']}")
    print(f"metadata_file={result['metadata_file']}")
    print(f"expected={result['expected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
