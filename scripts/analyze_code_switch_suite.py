#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def ascii_tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Latin-script token preservation in a code-switching suite result."
    )
    parser.add_argument("suite_result", help="JSON result from scripts/run_fixture_suite.sh.")
    parser.add_argument(
        "--output",
        help="Optional JSON output path for the analysis.",
    )
    return parser.parse_args()


def analyze_row(row: dict) -> dict:
    expected_tokens = ascii_tokens(row["expected"])
    actual_tokens = ascii_tokens(row["actual"])
    actual_token_set = set(actual_tokens)
    preserved = [token for token in expected_tokens if token in actual_token_set]
    missing = [token for token in expected_tokens if token not in actual_token_set]
    total = len(expected_tokens)
    preserved_count = len(preserved)
    preservation_rate = preserved_count / total if total else 1.0
    return {
        "row_idx": row["row_idx"],
        "label": row["label"],
        "category": row.get("category"),
        "cs_level": row.get("cs_level"),
        "expected_tokens": expected_tokens,
        "actual_tokens": actual_tokens,
        "preserved_tokens": preserved,
        "missing_tokens": missing,
        "preserved_count": preserved_count,
        "expected_count": total,
        "preservation_rate": round(preservation_rate, 4),
    }


def main() -> int:
    args = parse_args()
    suite = json.loads(Path(args.suite_result).read_text(encoding="utf-8"))
    rows = [analyze_row(row) for row in suite["results"]]
    expected_total = sum(row["expected_count"] for row in rows)
    preserved_total = sum(row["preserved_count"] for row in rows)
    summary = {
        "suite_id": suite["suite_id"],
        "model": suite["model"],
        "language": suite.get("language"),
        "device": suite["device"],
        "compute_type": suite["compute_type"],
        "initial_prompt": suite.get("initial_prompt"),
        "rows": len(rows),
        "expected_latin_tokens": expected_total,
        "preserved_latin_tokens": preserved_total,
        "preservation_rate": round(
            preserved_total / expected_total if expected_total else 1.0,
            4,
        ),
        "row_results": rows,
    }

    for row in rows:
        print(
            "row={row_idx:05d} preserved={preserved_count}/{expected_count} "
            "missing={missing_tokens}".format(**row)
        )
    print(
        "latin_token_preservation="
        f"{summary['preserved_latin_tokens']}/{summary['expected_latin_tokens']} "
        f"({summary['preservation_rate']:.2%})"
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"output={output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
