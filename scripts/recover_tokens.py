#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY = "memory/manual-aliases.json"
FALLBACK_MEMORY = "memory/manual-aliases.example.json"
DEFAULT_MIN_CONFIDENCE = 0.8
VALID_SCOPES = {"global", "workspace", "personal"}


@dataclass(frozen=True)
class MemoryEntry:
    spoken: str
    target: str
    scope: str
    confidence: float
    source: str


@dataclass(frozen=True)
class AppliedReplacement:
    spoken: str
    target: str
    scope: str
    confidence: float
    source: str
    count: int


def repo_relative_path(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO_ROOT / value


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def default_memory_path() -> Path:
    env_path = os.environ.get("STT_TOKEN_MEMORY")
    if env_path:
        return repo_relative_path(env_path)

    memory_path = repo_relative_path(DEFAULT_MEMORY)
    if memory_path.exists():
        return memory_path
    return repo_relative_path(FALLBACK_MEMORY)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recover Codex/workspace tokens from a transcript using manual memory."
    )
    parser.add_argument(
        "text",
        nargs="*",
        help="Transcript text. If omitted, stdin is used.",
    )
    parser.add_argument(
        "--memory",
        default=None,
        help=(
            f"Manual token memory JSON. Default: {DEFAULT_MEMORY}, "
            f"fallback: {FALLBACK_MEMORY}, env: STT_TOKEN_MEMORY"
        ),
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help=f"Minimum entry confidence to apply. Default: {DEFAULT_MIN_CONFIDENCE}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print recovery result as JSON.",
    )
    parser.add_argument(
        "--fixture",
        help="Run recovery fixture JSON instead of recovering one transcript.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    if not path.exists():
        raise ValueError(f"file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error


def require_non_empty_string(value: Any, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"memory entry {index} field '{field}' must be a non-empty string")
    return value.strip()


def require_confidence(value: Any, index: int) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"memory entry {index} field 'confidence' must be a number")
    confidence = float(value)
    if not 0 <= confidence <= 1:
        raise ValueError(f"memory entry {index} field 'confidence' must be between 0 and 1")
    return confidence


def parse_memory_entry(raw_entry: Any, index: int) -> MemoryEntry:
    if not isinstance(raw_entry, dict):
        raise ValueError(f"memory entry {index} must be an object")

    spoken = require_non_empty_string(raw_entry.get("spoken"), "spoken", index)
    target = require_non_empty_string(raw_entry.get("target"), "target", index)
    scope = require_non_empty_string(raw_entry.get("scope", "workspace"), "scope", index)
    if scope not in VALID_SCOPES:
        raise ValueError(
            f"memory entry {index} field 'scope' must be one of {sorted(VALID_SCOPES)}"
        )
    confidence = require_confidence(raw_entry.get("confidence", 1.0), index)
    source = require_non_empty_string(raw_entry.get("source", "manual"), "source", index)
    return MemoryEntry(
        spoken=spoken,
        target=target,
        scope=scope,
        confidence=confidence,
        source=source,
    )


def load_memory(path: Path) -> list[MemoryEntry]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("memory file must contain a JSON object")
    if payload.get("version") != 1:
        raise ValueError("memory file field 'version' must be 1")
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("memory file field 'entries' must be a list")

    entries = [
        parse_memory_entry(raw_entry, index)
        for index, raw_entry in enumerate(raw_entries)
    ]
    return sorted(entries, key=lambda entry: len(entry.spoken), reverse=True)


def spoken_pattern(spoken: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in spoken.split()]
    return re.compile(r"\s*".join(parts))


def recover_text(
    text: str,
    entries: list[MemoryEntry],
    min_confidence: float,
) -> tuple[str, list[AppliedReplacement]]:
    if not 0 <= min_confidence <= 1:
        raise ValueError("--min-confidence must be between 0 and 1")

    recovered = text
    applied: list[AppliedReplacement] = []
    for entry in entries:
        if entry.confidence < min_confidence:
            continue
        pattern = spoken_pattern(entry.spoken)
        recovered, count = pattern.subn(entry.target, recovered)
        if count:
            applied.append(
                AppliedReplacement(
                    spoken=entry.spoken,
                    target=entry.target,
                    scope=entry.scope,
                    confidence=entry.confidence,
                    source=entry.source,
                    count=count,
                )
            )
    return recovered, applied


def replacement_to_dict(replacement: AppliedReplacement) -> dict[str, Any]:
    return {
        "spoken": replacement.spoken,
        "target": replacement.target,
        "scope": replacement.scope,
        "confidence": replacement.confidence,
        "source": replacement.source,
        "count": replacement.count,
    }


def result_payload(
    original: str,
    recovered: str,
    applied: list[AppliedReplacement],
    memory_path: Path,
) -> dict[str, Any]:
    return {
        "original": original,
        "recovered": recovered,
        "changed": original != recovered,
        "memory": display_path(memory_path),
        "applied": [replacement_to_dict(replacement) for replacement in applied],
    }


def input_text(args: argparse.Namespace) -> str:
    if args.text:
        return " ".join(args.text).strip()
    if sys.stdin.isatty():
        raise ValueError("text is required when stdin is empty")
    return sys.stdin.read().strip()


def resolve_memory_path(args: argparse.Namespace, fixture_payload: dict[str, Any] | None = None) -> Path:
    if args.memory:
        return repo_relative_path(args.memory)
    if fixture_payload and fixture_payload.get("memory"):
        return repo_relative_path(str(fixture_payload["memory"]))
    return default_memory_path()


def run_fixture(args: argparse.Namespace) -> int:
    fixture_path = repo_relative_path(args.fixture)
    fixture_payload = load_json(fixture_path)
    if not isinstance(fixture_payload, dict):
        raise ValueError("fixture file must contain a JSON object")
    raw_cases = fixture_payload.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("fixture file field 'cases' must be a list")

    memory_path = resolve_memory_path(args, fixture_payload)
    entries = load_memory(memory_path)
    failures = []
    results = []
    for index, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, dict):
            raise ValueError(f"fixture case {index} must be an object")
        case_input = require_non_empty_string(raw_case.get("input"), "input", index)
        expected = require_non_empty_string(raw_case.get("expected"), "expected", index)
        recovered, applied = recover_text(case_input, entries, args.min_confidence)
        passed = recovered == expected
        result = {
            "label": raw_case.get("label", f"case-{index}"),
            "input": case_input,
            "expected": expected,
            "actual": recovered,
            "passed": passed,
            "applied": [replacement_to_dict(replacement) for replacement in applied],
        }
        results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"{status} {result['label']}: {case_input} -> {recovered}")
        if not passed:
            failures.append(result)

    summary = {
        "fixture": display_path(fixture_path),
        "memory": display_path(memory_path),
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "results": results,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"summary: passed={summary['passed']}/{summary['total']} "
            f"memory={summary['memory']}"
        )
    return 1 if failures else 0


def main() -> int:
    args = parse_args()
    try:
        if args.fixture:
            return run_fixture(args)

        memory_path = resolve_memory_path(args)
        entries = load_memory(memory_path)
        original = input_text(args)
        recovered, applied = recover_text(original, entries, args.min_confidence)
        payload = result_payload(original, recovered, applied, memory_path)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(recovered)
        return 0
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
