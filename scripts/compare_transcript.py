#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import string
import sys
from pathlib import Path


KOREAN_PUNCTUATION = "，。！？、…·“”‘’「」『』《》〈〉"
PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation + KOREAN_PUNCTUATION)


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = text.translate(PUNCTUATION_TABLE)
    text = re.sub(r"\s+", "", text)
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare expected and actual transcripts for fixture checks."
    )
    parser.add_argument("expected_file")
    parser.add_argument("actual_file")
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Require exact text match instead of normalized match.",
    )
    return parser.parse_args()


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def main() -> int:
    args = parse_args()
    expected = read_text(args.expected_file)
    actual = read_text(args.actual_file)

    if args.exact:
        ok = expected == actual
    else:
        ok = normalize(expected) == normalize(actual)

    if ok:
        print("transcript match")
        return 0

    print("transcript mismatch", file=sys.stderr)
    print(f"expected: {expected}", file=sys.stderr)
    print(f"actual:   {actual}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
