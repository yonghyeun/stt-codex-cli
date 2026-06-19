#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DATASET = "thetaone-ai/HiKE"
CONFIG = "default"
SPLIT = "test"
SOURCE_PAGE = "https://huggingface.co/datasets/thetaone-ai/HiKE"
LICENSE = "apache-2.0"
DEFAULT_PREFIX = "hike-row"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch HiKE Korean-English code-switching rows as local speech fixtures."
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
        help="Fixture output directory. Default: fixtures/generated/hike-row-<idx> or fixtures/generated/<manifest id>",
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

    payload = fetch_json(rows_api_url(row_idx))
    rows = payload.get("rows") or []
    if len(rows) != 1:
        raise RuntimeError(f"expected one row, got {len(rows)}")

    row_payload = rows[0]
    row = row_payload["row"]
    wav_path = output_dir / "audio.wav"
    expected_path = output_dir / "expected.txt"
    display_path = output_dir / "expected.display.txt"
    metadata_path = output_dir / "metadata.local.json"

    download(audio_url(row), wav_path)
    source_expected = row["text_normalized"].strip()
    if expected_text is not None and expected_text.strip() != source_expected:
        raise RuntimeError(
            f"manifest expected text does not match row {row_idx}: {expected_text!r} != {source_expected!r}"
        )
    expected_path.write_text(source_expected + "\n", encoding="utf-8")
    display_path.write_text(row["text"].strip() + "\n", encoding="utf-8")

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
        "display_file": str(display_path),
        "text": row["text"],
        "text_normalized": row["text_normalized"],
        "text_pier_labeled": row["text_pier_labeled"],
        "cs_level": row["cs_level"],
        "cs_levels_all": row["cs_levels_all"],
        "category": row["category"],
        "loanwords": row["loanwords"],
        "sample_id": row["sample_id"],
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "audio_file": str(wav_path),
        "expected_file": str(expected_path),
        "metadata_file": str(metadata_path),
        "expected": source_expected,
    }


def main() -> int:
    args = parse_args()
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        root = Path(args.output_dir or f"fixtures/generated/{manifest['id']}")
        prefix = manifest.get("fixture_dir_prefix", DEFAULT_PREFIX)
        for fixture in manifest["fixtures"]:
            row_idx = int(fixture["row_idx"])
            output_dir = root / f"{prefix}-{row_idx:05d}"
            result = fetch_fixture(row_idx, output_dir, fixture.get("expected"))
            print(
                f"row_idx={row_idx} audio_file={result['audio_file']} expected={result['expected']}"
            )
        return 0

    result = fetch_fixture(
        args.row_idx,
        Path(args.output_dir or f"fixtures/generated/{DEFAULT_PREFIX}-{args.row_idx:05d}"),
    )
    print(f"audio_file={result['audio_file']}")
    print(f"expected_file={result['expected_file']}")
    print(f"metadata_file={result['metadata_file']}")
    print(f"expected={result['expected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
