#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_result(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"result file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"invalid result json: {path}: {error}") from error


def format_number(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def format_percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "-"
    return f"{(numerator / denominator) * 100:.2f}%"


def markdown_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return text.replace("|", "\\|")


def snippet(value: Any, max_chars: int) -> str:
    text = str(value).replace("\n", " ").strip()
    if max_chars < 1 or len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def fenced_text(value: Any) -> str:
    text = str(value)
    return f"```text\n{text}\n```"


def render_key_value(items: list[tuple[str, Any]]) -> list[str]:
    return [f"- `{key}`: `{value}`" for key, value in items]


def render_quality_summary(result: dict[str, Any]) -> list[str]:
    summary = result.get("quality_summary", {})
    if not summary:
        return ["## Quality Summary", "", "- 없음"]

    rows = ["## Quality Summary", "", "| metric | value |", "| --- | ---: |"]
    for key in (
        "average_case_score",
        "average_text_similarity",
        "average_normalized_char_error_rate",
        "average_critical_token_f1",
    ):
        rows.append(f"| {key} | {format_number(summary.get(key))} |")
    return rows


def render_category_summary(result: dict[str, Any]) -> list[str]:
    summary = result.get("category_summary", {})
    rows = [
        "## Category Summary",
        "",
        "| category | total | failed | failure_rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, data in sorted(summary.items()):
        total = int(data.get("total", 0))
        failed = int(data.get("failed", 0))
        rows.append(
            f"| {category} | {total} | {failed} | {format_percent(failed, total)} |"
        )
    if not summary:
        rows.append("| - | 0 | 0 | - |")
    return rows


def render_failure_summary(result: dict[str, Any]) -> list[str]:
    summary = result.get("failure_summary", {})
    rows = ["## Failure Summary", "", "| failure_type | count |", "| --- | ---: |"]
    for failure_type, count in sorted(summary.items(), key=lambda item: (-item[1], item[0])):
        rows.append(f"| {failure_type} | {count} |")
    if not summary:
        rows.append("| - | 0 |")
    return rows


def render_case_table(result: dict[str, Any], max_text_chars: int) -> list[str]:
    rows = [
        "## Cases",
        "",
        "| case | sample | category | score | similarity | nCER | token_f1 | failures | expected | raw |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for case in result.get("cases", []):
        comparison = case.get("text_comparison", {})
        quality = case.get("quality", {})
        failures = ", ".join(case.get("failure_types", [])) or "-"
        rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(case.get("case_id", "")),
                    markdown_cell(case.get("sample_id", "")),
                    markdown_cell(case.get("category", "")),
                    format_number(quality.get("case_score")),
                    format_number(quality.get("text_similarity")),
                    format_number(quality.get("normalized_char_error_rate")),
                    format_number(quality.get("critical_token_f1")),
                    markdown_cell(failures),
                    markdown_cell(snippet(comparison.get("expected_text", ""), max_text_chars)),
                    markdown_cell(snippet(comparison.get("raw_text", ""), max_text_chars)),
                ]
            )
            + " |"
        )
    return rows


def render_text_blocks(result: dict[str, Any]) -> list[str]:
    rows = ["## Text Comparison", ""]
    for case in result.get("cases", []):
        comparison = case.get("text_comparison", {})
        failures = ", ".join(case.get("failure_types", [])) or "-"
        rows.extend(
            [
                f"### {case.get('case_id', '')} / {case.get('sample_id', '')}",
                "",
                f"- category: `{case.get('category', '')}`",
                f"- failures: `{failures}`",
                "",
                "Expected:",
                "",
                fenced_text(comparison.get("expected_text", "")),
                "",
                "Raw:",
                "",
                fenced_text(comparison.get("raw_text", "")),
                "",
                "Recovered:",
                "",
                fenced_text(comparison.get("recovered_text", "")),
                "",
            ]
        )
    return rows


def render_markdown(
    result: dict[str, Any],
    *,
    show_text: bool = False,
    max_text_chars: int = 80,
) -> str:
    config = result.get("config", {})
    rows: list[str] = [
        "# STT Accuracy Result",
        "",
        *render_key_value(
            [
                ("run_id", result.get("run_id", "")),
                ("suite_id", result.get("suite_id", "")),
                ("input_set", result.get("input_set", "")),
                ("model", config.get("model", "")),
                ("device", config.get("device", "")),
                ("compute_type", config.get("compute_type", "")),
                ("language", config.get("language", "")),
                ("elapsed_seconds", format_number(result.get("elapsed_seconds"))),
                ("total", result.get("total", 0)),
                ("failed", result.get("failed", 0)),
                (
                    "failure_rate",
                    format_percent(int(result.get("failed", 0)), int(result.get("total", 0))),
                ),
            ]
        ),
        "",
        *render_quality_summary(result),
        "",
        *render_category_summary(result),
        "",
        *render_failure_summary(result),
        "",
        *render_case_table(result, max_text_chars),
    ]
    if show_text:
        rows.extend(["", *render_text_blocks(result)])
    return "\n".join(rows).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an STT accuracy result.json as human-readable Markdown."
    )
    parser.add_argument("result_json", help="Path to evals/stt_accuracy/runs/<run_id>/result.json.")
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Include full expected/raw/recovered text blocks for local inspection.",
    )
    parser.add_argument(
        "--max-text-chars",
        type=int,
        default=80,
        help="Maximum expected/raw snippet length in the case table. Default: 80.",
    )
    return parser.parse_args(argv)


def main_to_text(argv: list[str] | None = None) -> str:
    args = parse_args(argv)
    result = load_result(Path(args.result_json))
    return render_markdown(
        result,
        show_text=args.show_text,
        max_text_chars=args.max_text_chars,
    )


def main(argv: list[str] | None = None) -> int:
    sys.stdout.write(main_to_text(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
