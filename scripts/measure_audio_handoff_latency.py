#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import measure_stt_latency_baseline as baseline
from scripts import run_stt_accuracy_suite as accuracy
from stt_runtime.transcription import (
    PersistentWorkerTranscriptionClient,
    TranscriptionConfig,
    TranscriptionRequest,
)


DEFAULT_SUITE = baseline.DEFAULT_SUITE
DEFAULT_INPUT_ROOT = baseline.DEFAULT_INPUT_ROOT
DEFAULT_RUN_ROOT = baseline.DEFAULT_RUN_ROOT
DEFAULT_SAMPLE_IDS = baseline.DEFAULT_SAMPLE_IDS
DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS = 5.956
DEFAULT_PRIOR_CASE_SCORES = {
    "cmd-0002": 1.0000,
    "cmd-0018": 0.3147,
    "cmd-0021": 0.3435,
    "cmd-0024": 0.9111,
}


@dataclass(frozen=True)
class HandoffRun:
    transcript: str
    elapsed_seconds: float


def round_elapsed(value: float) -> float:
    return round(value, 6)


def relative_to_run_dir(path: Path, run_dir: Path) -> str:
    return path.relative_to(run_dir).as_posix()


def config_from_args(args: argparse.Namespace) -> TranscriptionConfig:
    return TranscriptionConfig(
        model=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
        initial_prompt=args.initial_prompt,
        vad_filter=not args.no_vad_filter,
    )


def request_for_mode(case: baseline.LatencyCase, mode: str) -> TranscriptionRequest:
    if mode == "file":
        return TranscriptionRequest(audio_file=case.audio_file)
    if mode == "buffer":
        return TranscriptionRequest(
            audio_bytes=case.audio_file.read_bytes(),
            audio_format="wav",
        )
    raise baseline.ContractError(f"unsupported handoff mode: {mode}")


def run_worker_case(
    *,
    client: PersistentWorkerTranscriptionClient,
    case: baseline.LatencyCase,
    mode: str,
) -> HandoffRun:
    request = request_for_mode(case, mode)
    started_at = time.monotonic()
    result = client.transcribe(request)
    elapsed = time.monotonic() - started_at
    return HandoffRun(
        transcript=result.transcript,
        elapsed_seconds=round_elapsed(elapsed),
    )


def build_case_result(
    *,
    case: baseline.LatencyCase,
    mode: str,
    run: HandoffRun,
    run_dir: Path,
) -> dict[str, Any]:
    raw_file = run_dir / mode / "raw" / f"{case.sample_id}.txt"
    recovered_file = run_dir / mode / "recovered" / f"{case.sample_id}.txt"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    recovered_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(run.transcript + "\n", encoding="utf-8")
    recovered_file.write_text(run.transcript + "\n", encoding="utf-8")

    result = accuracy.evaluate_case(
        case_id=case.case_id,
        sample_id=case.sample_id,
        category=case.category,
        metrics=case.metrics,
        expected=case.expected,
        actual=run.transcript,
        raw_file=relative_to_run_dir(raw_file, run_dir),
        recovered_file=relative_to_run_dir(recovered_file, run_dir),
    )
    result["handoff"] = mode
    result["latency"] = {
        "worker_request_elapsed_seconds": run.elapsed_seconds,
        "prior_29_subprocess_average_seconds": DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS,
        "delta_vs_prior_29_average_seconds": round_elapsed(
            run.elapsed_seconds - DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS
        ),
    }
    prior_score = DEFAULT_PRIOR_CASE_SCORES.get(case.sample_id)
    result["prior_29"] = {
        "case_score": prior_score,
        "case_score_delta": (
            None
            if prior_score is None
            else round(result["quality"]["case_score"] - prior_score, 4)
        ),
    }
    return result


def average(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round_elapsed(sum(values) / len(values))


def summarize_mode(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "average_worker_request_elapsed_seconds": average(
            [
                float(case["latency"]["worker_request_elapsed_seconds"])
                for case in case_results
            ]
        ),
        "average_case_score": accuracy.average_or_none(
            [case["quality"]["case_score"] for case in case_results]
        ),
        "average_normalized_char_error_rate": accuracy.average_or_none(
            [
                case["quality"]["normalized_char_error_rate"]
                for case in case_results
            ]
        ),
    }


def build_result_json(
    *,
    run_id: str,
    suite_path: Path,
    input_root: Path,
    run_dir: Path,
    config: TranscriptionConfig,
    sample_ids: Sequence[str],
    mode_results: dict[str, list[dict[str, Any]]],
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, Any]:
    summaries = {
        mode: summarize_mode(cases) for mode, cases in mode_results.items()
    }
    file_avg = summaries.get("file", {}).get("average_worker_request_elapsed_seconds")
    buffer_avg = summaries.get("buffer", {}).get("average_worker_request_elapsed_seconds")
    delta_buffer_vs_file = (
        None
        if not isinstance(file_avg, int | float) or not isinstance(buffer_avg, int | float)
        else round_elapsed(float(buffer_avg) - float(file_avg))
    )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "suite_path": suite_path.as_posix(),
        "input_root": input_root.as_posix(),
        "sample_ids": list(sample_ids),
        "run_dir": run_dir.as_posix(),
        "started_at_utc": started_at.isoformat(),
        "completed_at_utc": completed_at.isoformat(),
        "config": {
            "model": config.model,
            "language": config.language,
            "device": config.device,
            "compute_type": config.compute_type,
            "beam_size": config.beam_size,
            "initial_prompt": config.initial_prompt,
            "vad_filter": config.vad_filter,
            "stt_backend": "worker",
        },
        "prior_29": {
            "subprocess_average_seconds": DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS,
            "case_scores": DEFAULT_PRIOR_CASE_SCORES,
        },
        "summary": {
            "modes": summaries,
            "delta_buffer_vs_file_average_seconds": delta_buffer_vs_file,
        },
        "cases": mode_results,
        "measurement_boundary": {
            "measured": "Persistent worker request wall time per handoff mode.",
            "not_measured": [
                "live arecord stop latency",
                "child PTY injection latency",
                "terminal render latency",
            ],
        },
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
    summary = result["summary"]
    lines = [
        "# STT Buffer Handoff Report",
        "",
        "## Scope",
        "",
        "- Issue: `#32` under umbrella `#28`.",
        "- Measurement path: persistent worker file handoff vs persistent worker buffer handoff.",
        f"- Fixed smoke input set: `{', '.join(result['sample_ids'])}`.",
        "- Non-scope: release gap tuning, beam/VAD tuning, token recovery.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "STT_PYTHON_BIN=/path/to/.venv/bin/python \\",
        "STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \\",
        "scripts/measure_audio_handoff_latency.py \\",
        f"  --run-id {result['run_id']} \\",
        f"  --input-root {result['input_root']} \\",
        f"  --model {result['config']['model']} \\",
        f"  --device {result['config']['device']} \\",
        f"  --compute-type {result['config']['compute_type']} \\",
        f"  --language {result['config']['language']} \\",
        "  --report-output evals/stt_accuracy/reports/2026-06-23-buffer-handoff.md",
        "```",
        "",
        "## Prior Baseline",
        "",
        "- `#29` file-based subprocess average: "
        f"`{format_seconds(result['prior_29']['subprocess_average_seconds'])}` seconds.",
        "",
        "## Summary",
        "",
        "| path | average request seconds | average case score | average normalized CER | delta vs #29 subprocess avg |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for mode in ("file", "buffer"):
        mode_summary = summary["modes"].get(mode, {})
        average_elapsed = mode_summary.get("average_worker_request_elapsed_seconds")
        delta_vs_prior = (
            None
            if not isinstance(average_elapsed, int | float)
            else float(average_elapsed) - result["prior_29"]["subprocess_average_seconds"]
        )
        lines.append(
            "| "
            f"{mode} | "
            f"{format_seconds(average_elapsed)} | "
            f"{format_score(mode_summary.get('average_case_score'))} | "
            f"{format_score(mode_summary.get('average_normalized_char_error_rate'))} | "
            f"{format_seconds(delta_vs_prior)} |"
        )
    lines.extend(
        [
            "",
            "- buffer vs persistent-worker file average delta: "
            f"`{format_seconds(summary.get('delta_buffer_vs_file_average_seconds'))}` seconds.",
            "",
            "## Case Results",
            "",
            "| sample | path | request s | case score | #29 case score | score delta | failures |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for mode in ("file", "buffer"):
        for case in result["cases"].get(mode, []):
            failures = ", ".join(case.get("failure_types", [])) or "none"
            lines.append(
                "| "
                f"{case['sample_id']} | "
                f"{mode} | "
                f"{format_seconds(case['latency'].get('worker_request_elapsed_seconds'))} | "
                f"{format_score(case['quality'].get('case_score'))} | "
                f"{format_score(case['prior_29'].get('case_score'))} | "
                f"{format_score(case['prior_29'].get('case_score_delta'))} | "
                f"{failures} |"
            )
    lines.extend(
        [
            "",
            "## Measurement Boundary",
            "",
            "- Measured: persistent worker request wall time for file path handoff.",
            "- Measured: persistent worker request wall time for base64 WAV buffer handoff.",
            "- Measured: fixed smoke set accuracy with the existing STT accuracy evaluator.",
            "- Not measured: live `arecord` stop latency, child PTY injection latency, terminal render latency.",
            "",
        ]
    )
    return "\n".join(lines)


def run_audio_handoff_latency(
    *,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    run_id: str,
    sample_ids: Sequence[str],
    config: TranscriptionConfig,
    force: bool,
) -> dict[str, Any]:
    run_dir = run_root / run_id
    if run_dir.exists() and not force:
        raise baseline.ContractError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = baseline.load_latency_cases(
        suite_path=suite_path,
        input_root=input_root,
        run_dir=run_dir,
        sample_ids=sample_ids,
    )
    started_at = datetime.now(timezone.utc)
    mode_results: dict[str, list[dict[str, Any]]] = {}
    for mode in ("file", "buffer"):
        statuses: list[str] = []
        client = PersistentWorkerTranscriptionClient(
            repo_root=REPO_ROOT,
            config=config,
            status=statuses.append,
        )
        try:
            mode_results[mode] = [
                build_case_result(
                    case=case,
                    mode=mode,
                    run=run_worker_case(client=client, case=case, mode=mode),
                    run_dir=run_dir,
                )
                for case in cases
            ]
        finally:
            client.close()
        (run_dir / mode / "worker-status.log").write_text(
            "\n".join(statuses) + "\n",
            encoding="utf-8",
        )
    completed_at = datetime.now(timezone.utc)
    result = build_result_json(
        run_id=run_id,
        suite_path=suite_path,
        input_root=input_root,
        run_dir=run_dir,
        config=config,
        sample_ids=sample_ids,
        mode_results=mode_results,
        started_at=started_at,
        completed_at=completed_at,
    )
    (run_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def render_dry_run(
    *,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    run_id: str,
    sample_ids: Sequence[str],
    config: TranscriptionConfig,
) -> dict[str, Any]:
    run_dir = run_root / run_id
    cases = baseline.load_latency_cases(
        suite_path=suite_path,
        input_root=input_root,
        run_dir=run_dir,
        sample_ids=sample_ids,
    )
    return {
        "schema_version": 1,
        "mode": "dry-run",
        "run_id": run_id,
        "run_dir": run_dir.as_posix(),
        "sample_ids": list(sample_ids),
        "handoff_modes": ["file", "buffer"],
        "config": {
            "model": config.model,
            "language": config.language,
            "device": config.device,
            "compute_type": config.compute_type,
            "beam_size": config.beam_size,
            "initial_prompt": config.initial_prompt,
            "vad_filter": config.vad_filter,
            "stt_backend": "worker",
        },
        "prior_29": {
            "subprocess_average_seconds": DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS,
            "case_scores": DEFAULT_PRIOR_CASE_SCORES,
        },
        "cases": [
            {
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "audio_file": case.audio_file.as_posix(),
            }
            for case in cases
        ],
    }


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-buffer-handoff")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure persistent-worker file vs buffer audio handoff latency."
    )
    parser.add_argument("--suite", default=str(DEFAULT_SUITE))
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT_ROOT))
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--run-id", default=default_run_id())
    parser.add_argument("--sample-id", action="append", dest="sample_ids")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--language", default="ko")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--initial-prompt", default="")
    parser.add_argument("--no-vad-filter", action="store_true")
    parser.add_argument("--report-output")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    suite_path = baseline.resolve_suite(args.suite)
    input_root = Path(args.input_root)
    run_root = Path(args.run_root)
    sample_ids = args.sample_ids or list(DEFAULT_SAMPLE_IDS)
    config = config_from_args(args)

    if args.dry_run:
        print(
            json.dumps(
                render_dry_run(
                    suite_path=suite_path,
                    input_root=input_root,
                    run_root=run_root,
                    run_id=args.run_id,
                    sample_ids=sample_ids,
                    config=config,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    result = run_audio_handoff_latency(
        suite_path=suite_path,
        input_root=input_root,
        run_root=run_root,
        run_id=args.run_id,
        sample_ids=sample_ids,
        config=config,
        force=args.force,
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
