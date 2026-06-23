#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import measure_stt_latency_baseline as latency


DEFAULT_PRIOR_CASE_SCORES = {
    "cmd-0002": 1.0000,
    "cmd-0018": 0.3147,
    "cmd-0021": 0.3435,
    "cmd-0024": 0.9111,
}
DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS = 5.956
DEFAULT_SAMPLE_IDS = latency.DEFAULT_SAMPLE_IDS


@dataclass(frozen=True)
class TradeoffCombo:
    combo_id: str
    beam_size: int
    vad_filter: bool


COMBOS = (
    TradeoffCombo("beam5-vad-on", 5, True),
    TradeoffCombo("beam1-vad-on", 1, True),
    TradeoffCombo("beam5-vad-off", 5, False),
    TradeoffCombo("beam1-vad-off", 1, False),
)
DEFAULT_COMBO_ID = "beam5-vad-on"


def round_elapsed(value: float) -> float:
    return round(value, 6)


def combo_by_id(combo_id: str) -> TradeoffCombo:
    for combo in COMBOS:
        if combo.combo_id == combo_id:
            return combo
    raise latency.ContractError(f"unknown combo: {combo_id}")


def combo_config(args: argparse.Namespace, combo: TradeoffCombo) -> latency.LatencyConfig:
    return latency.LatencyConfig(
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        beam_size=combo.beam_size,
        initial_prompt=args.initial_prompt,
        vad_filter=combo.vad_filter,
    )


def combo_run_id(prefix: str, combo: TradeoffCombo) -> str:
    return f"{prefix}-{combo.combo_id}"


def case_floor_decision(case: dict[str, Any]) -> str:
    sample_id = str(case.get("sample_id"))
    raw_text = case.get("text_comparison", {}).get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        return "fail_empty_transcript"

    case_score = case.get("quality", {}).get("case_score")
    if not isinstance(case_score, int | float):
        return "fail_missing_score"

    prior_score = DEFAULT_PRIOR_CASE_SCORES.get(sample_id)
    if sample_id == "cmd-0002" and case_score < 1.0:
        return "fail_cmd_0002_regression"
    if prior_score is not None and case_score < prior_score:
        return "fail_quality_regression"
    return "pass"


def combo_floor_decision(cases: Sequence[dict[str, Any]]) -> str:
    decisions = [case_floor_decision(case) for case in cases]
    if all(decision == "pass" for decision in decisions):
        return "pass"
    return "fail"


def summarize_combo(result: dict[str, Any], default_average: float | None) -> dict[str, Any]:
    latency_average = result["latency_summary"]["averages"].get(
        "subprocess_elapsed_seconds"
    )
    decode_average = result["latency_summary"]["averages"].get("decode_elapsed_seconds")
    floor_decision = combo_floor_decision(result["cases"])
    latency_delta = None
    if isinstance(latency_average, int | float) and isinstance(default_average, int | float):
        latency_delta = round_elapsed(float(latency_average) - float(default_average))
    prior_29_delta = None
    if isinstance(latency_average, int | float):
        prior_29_delta = round_elapsed(
            float(latency_average) - DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS
        )

    if result["run_id"].endswith(DEFAULT_COMBO_ID):
        speed_profile_decision = "default_only"
    elif floor_decision != "pass":
        speed_profile_decision = "excluded_accuracy_floor"
    elif latency_delta is not None and latency_delta >= 0:
        speed_profile_decision = "excluded_no_latency_gain"
    else:
        speed_profile_decision = "fixed-smoke-only-candidate"

    return {
        "combo_id": result["combo"]["combo_id"],
        "beam_size": result["combo"]["beam_size"],
        "vad_filter": result["combo"]["vad_filter"],
        "average_latency_seconds": latency_average,
        "average_decode_seconds": decode_average,
        "latency_delta_vs_default_seconds": latency_delta,
        "latency_delta_vs_prior_29_seconds": prior_29_delta,
        "average_case_score": result["quality_summary"].get("average_case_score"),
        "average_normalized_char_error_rate": result["quality_summary"].get(
            "average_normalized_char_error_rate"
        ),
        "average_text_similarity": result["quality_summary"].get(
            "average_text_similarity"
        ),
        "average_critical_token_f1": result["quality_summary"].get(
            "average_critical_token_f1"
        ),
        "floor_decision": floor_decision,
        "speed_profile_decision": speed_profile_decision,
    }


def attach_combo(result: dict[str, Any], combo: TradeoffCombo) -> dict[str, Any]:
    result["combo"] = {
        "combo_id": combo.combo_id,
        "beam_size": combo.beam_size,
        "vad_filter": combo.vad_filter,
    }
    for case in result["cases"]:
        prior_score = DEFAULT_PRIOR_CASE_SCORES.get(str(case["sample_id"]))
        case["prior_29"] = {
            "case_score": prior_score,
            "floor_decision": case_floor_decision(case),
        }
    return result


def run_combo(
    *,
    args: argparse.Namespace,
    combo: TradeoffCombo,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    sample_ids: Sequence[str],
) -> dict[str, Any]:
    result = latency.run_latency_baseline(
        suite_path=suite_path,
        input_root=input_root,
        run_root=run_root,
        run_id=combo_run_id(args.run_id_prefix, combo),
        sample_ids=sample_ids,
        config=combo_config(args, combo),
        baseline_result=Path(args.baseline_result),
        transcribe_command=Path(args.transcribe_command),
        force=args.force,
    )
    return attach_combo(result, combo)


def build_tradeoff_result(
    *,
    args: argparse.Namespace,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    sample_ids: Sequence[str],
    combo_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    default_average = combo_results[DEFAULT_COMBO_ID]["latency_summary"]["averages"].get(
        "subprocess_elapsed_seconds"
    )
    summaries = {
        combo_id: summarize_combo(result, default_average)
        for combo_id, result in combo_results.items()
    }
    return {
        "schema_version": 1,
        "issue": "#35",
        "suite_path": suite_path.as_posix(),
        "input_root": input_root.as_posix(),
        "run_root": run_root.as_posix(),
        "run_id_prefix": args.run_id_prefix,
        "sample_ids": list(sample_ids),
        "coverage": "fixed-smoke-only",
        "prior_29": {
            "subprocess_average_seconds": DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS,
            "case_scores": DEFAULT_PRIOR_CASE_SCORES,
        },
        "summaries": summaries,
        "results": combo_results,
    }


def format_seconds(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.3f}"
    return "not measured"


def format_score(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.4f}"
    return "not measured"


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Beam/VAD Latency Tradeoff",
        "",
        "## Scope",
        "",
        "- Issue: `#35` under umbrella `#28`.",
        "- Coverage: fixed smoke set only.",
        "- Matrix: `beam_size=5/1` x `vad_filter=on/off`.",
        f"- Fixed smoke input set: `{', '.join(result['sample_ids'])}`.",
        "- Non-scope: prompt tuning, token recovery, worker/buffer handoff, release gap.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "STT_PYTHON_BIN=/path/to/.venv/bin/python \\",
        "STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \\",
        "scripts/evaluate_beam_vad_tradeoff.py \\",
        f"  --run-id-prefix {result['run_id_prefix']} \\",
        f"  --input-root {result['input_root']} \\",
        "  --model large-v3 \\",
        "  --device cuda \\",
        "  --compute-type float16 \\",
        "  --language ko \\",
        "  --report-output evals/stt_accuracy/reports/2026-06-23-beam-vad-tradeoff.md \\",
        "  --force",
        "```",
        "",
        "## Summary",
        "",
        "- `#29` current-input fixed-smoke subprocess average: "
        f"`{format_seconds(result['prior_29']['subprocess_average_seconds'])}` seconds.",
        "",
        "| combo | beam | VAD | avg latency s | avg decode s | delta vs default s | delta vs #29 avg s | avg case score | avg normalized CER | floor | decision |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for combo in COMBOS:
        summary = result["summaries"][combo.combo_id]
        lines.append(
            "| "
            f"`{combo.combo_id}` | "
            f"{summary['beam_size']} | "
            f"{'on' if summary['vad_filter'] else 'off'} | "
            f"{format_seconds(summary['average_latency_seconds'])} | "
            f"{format_seconds(summary['average_decode_seconds'])} | "
            f"{format_seconds(summary['latency_delta_vs_default_seconds'])} | "
            f"{format_seconds(summary['latency_delta_vs_prior_29_seconds'])} | "
            f"{format_score(summary['average_case_score'])} | "
            f"{format_score(summary['average_normalized_char_error_rate'])} | "
            f"{summary['floor_decision']} | "
            f"{summary['speed_profile_decision']} |"
        )

    lines.extend(
        [
            "",
            "## Case Floor",
            "",
            "| combo | sample | case score | #29 case score | normalized CER | failures | decision |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for combo in COMBOS:
        for case in result["results"][combo.combo_id]["cases"]:
            failures = ", ".join(case.get("failure_types", [])) or "none"
            lines.append(
                "| "
                f"`{combo.combo_id}` | "
                f"`{case['sample_id']}` | "
                f"{format_score(case['quality'].get('case_score'))} | "
                f"{format_score(case['prior_29'].get('case_score'))} | "
                f"{format_score(case['quality'].get('normalized_char_error_rate'))} | "
                f"{failures} | "
                f"{case['prior_29']['floor_decision']} |"
            )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- Default accuracy-first profile remains `beam_size=5`, VAD on.",
            "- Full suite was not run in this leaf; all candidate decisions are fixed-smoke-only.",
            "- A combo marked `fixed-smoke-only-candidate` may inform speed profile docs, but must not be promoted as suite-backed.",
            "",
            "## Measurement Boundary",
            "",
            "- Measured: fixed smoke subprocess latency and accuracy for each beam/VAD combo.",
            "- Not measured: full suite, live PTT latency, child PTY injection latency, terminal render latency.",
            "- Raw transcript artifacts remain local-only under `evals/stt_accuracy/runs/`.",
            "",
        ]
    )
    return "\n".join(lines)


def render_dry_run(
    *,
    args: argparse.Namespace,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    sample_ids: Sequence[str],
) -> dict[str, Any]:
    cases = latency.load_latency_cases(
        suite_path=suite_path,
        input_root=input_root,
        run_dir=run_root / args.run_id_prefix,
        sample_ids=sample_ids,
    )
    return {
        "schema_version": 1,
        "mode": "dry-run",
        "run_id_prefix": args.run_id_prefix,
        "suite_path": suite_path.as_posix(),
        "input_root": input_root.as_posix(),
        "run_root": run_root.as_posix(),
        "sample_ids": list(sample_ids),
        "combos": [combo.__dict__ for combo in COMBOS],
        "coverage": "fixed-smoke-only",
        "config": {
            "model": args.model,
            "device": args.device,
            "compute_type": args.compute_type,
            "language": args.language,
            "initial_prompt": args.initial_prompt,
        },
        "cases": [
            {
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "category": case.category,
                "audio_file": case.audio_file.as_posix(),
            }
            for case in cases
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate fixed-smoke beam/VAD latency and quality tradeoffs."
    )
    parser.add_argument("--suite", default=str(latency.DEFAULT_SUITE))
    parser.add_argument("--input-root", default=str(latency.DEFAULT_INPUT_ROOT))
    parser.add_argument("--run-root", default=str(latency.DEFAULT_RUN_ROOT))
    parser.add_argument("--run-id-prefix", default="20260623-beam-vad-fixed-smoke")
    parser.add_argument("--sample-id", action="append", dest="sample_ids")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--language", default="ko")
    parser.add_argument("--initial-prompt", default="")
    parser.add_argument("--baseline-result", default=str(latency.DEFAULT_BASELINE_RESULT))
    parser.add_argument("--transcribe-command", default=str(latency.DEFAULT_TRANSCRIBE_COMMAND))
    parser.add_argument("--report-output")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    suite_path = latency.resolve_suite(args.suite)
    input_root = Path(args.input_root)
    run_root = Path(args.run_root)
    sample_ids = args.sample_ids or list(DEFAULT_SAMPLE_IDS)

    if args.dry_run:
        print(
            json.dumps(
                render_dry_run(
                    args=args,
                    suite_path=suite_path,
                    input_root=input_root,
                    run_root=run_root,
                    sample_ids=sample_ids,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    combo_results = {
        combo.combo_id: run_combo(
            args=args,
            combo=combo,
            suite_path=suite_path,
            input_root=input_root,
            run_root=run_root,
            sample_ids=sample_ids,
        )
        for combo in COMBOS
    }
    result = build_tradeoff_result(
        args=args,
        suite_path=suite_path,
        input_root=input_root,
        run_root=run_root,
        sample_ids=sample_ids,
        combo_results=combo_results,
    )
    if args.report_output:
        report_output = Path(args.report_output)
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(render_report(result), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
