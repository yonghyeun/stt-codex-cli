#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_stt_accuracy_suite as accuracy


DEFAULT_SUITE = Path("evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.json")
DEFAULT_INPUT_ROOT = Path("evals/inputs/speech/v1")
DEFAULT_RUN_ROOT = Path("evals/stt_accuracy/runs")
DEFAULT_TRANSCRIBE_COMMAND = Path("scripts/transcribe.sh")
DEFAULT_BASELINE_RESULT = Path(
    "evals/stt_accuracy/runs/"
    "20260622-corrected-corpus-baseline-large-v3-cuda-float16-r2/result.json"
)
DEFAULT_SAMPLE_IDS = ("cmd-0002", "cmd-0018", "cmd-0021", "cmd-0024")


class ContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class LatencyConfig:
    model: str
    device: str
    compute_type: str
    language: str
    beam_size: int
    initial_prompt: str | None
    vad_filter: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "beam_size": self.beam_size,
            "initial_prompt": self.initial_prompt,
            "vad_filter": self.vad_filter,
            "token_recovery": "none",
        }


@dataclass(frozen=True)
class LatencyCase:
    case_id: str
    sample_id: str
    category: str
    metrics: list[str]
    expected: str
    audio_file: Path
    expected_file: Path
    metadata_file: Path
    raw_file: Path
    recovered_file: Path


@dataclass(frozen=True)
class TranscriptionRun:
    transcript: str
    stdout: str
    stderr: str
    returncode: int
    subprocess_elapsed_seconds: float
    timing: dict[str, Any]


Runner = Callable[[LatencyCase, LatencyConfig, Path], TranscriptionRun]


def round_elapsed(value: float) -> float:
    return round(value, 6)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"required file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"invalid json: {path}: {error}") from error


def resolve_suite(value: str) -> Path:
    path = Path(value)
    if path.exists() or "/" in value:
        return path
    return Path("evals/stt_accuracy/suites") / value / "manifest.json"


def parse_reported_elapsed_seconds(stderr: str) -> float | None:
    matches = re.findall(r"\belapsed=([0-9]+(?:\.[0-9]+)?)s\b", stderr)
    if not matches:
        return None
    return float(matches[-1])


def load_latency_cases(
    *,
    suite_path: Path,
    input_root: Path,
    run_dir: Path,
    sample_ids: Sequence[str],
) -> list[LatencyCase]:
    suite = load_json(suite_path)
    input_manifest = load_json(input_root / "manifest.json")
    accuracy.validate_manifest_link(suite, input_manifest)

    requested = list(sample_ids)
    known_samples = set(input_manifest.get("sample_ids", []))
    cases_by_sample = {str(case.get("sample_id", "")): case for case in suite.get("cases", [])}
    errors: list[str] = []
    latency_cases: list[LatencyCase] = []

    for sample_id in requested:
        if sample_id not in known_samples:
            errors.append(f"sample_id not in input manifest: {sample_id}")
            continue
        case = cases_by_sample.get(sample_id)
        if not case:
            errors.append(f"sample_id not in suite cases: {sample_id}")
            continue

        sample_dir = input_root / "samples" / sample_id
        audio_file = sample_dir / "audio.wav"
        expected_file = sample_dir / "expected.txt"
        metadata_file = sample_dir / "metadata.json"
        for required_file in (audio_file, expected_file, metadata_file):
            if not required_file.exists():
                errors.append(f"{sample_id}: required file not found: {required_file}")

        expected = expected_file.read_text(encoding="utf-8").strip() if expected_file.exists() else ""
        latency_cases.append(
            LatencyCase(
                case_id=str(case.get("case_id", "")),
                sample_id=sample_id,
                category=str(case.get("category", "")),
                metrics=[str(metric) for metric in case.get("metrics", [])],
                expected=expected,
                audio_file=audio_file,
                expected_file=expected_file,
                metadata_file=metadata_file,
                raw_file=run_dir / "raw" / f"{sample_id}.txt",
                recovered_file=run_dir / "recovered" / f"{sample_id}.txt",
            )
        )

    if errors:
        raise ContractError("\n".join(errors))
    return latency_cases


def build_transcribe_command(
    *,
    transcribe_command: Path,
    case: LatencyCase,
    config: LatencyConfig,
    timing_file: Path,
) -> list[str]:
    command = [
        str(transcribe_command),
        str(case.audio_file),
        "--model",
        config.model,
        "--device",
        config.device,
        "--compute-type",
        config.compute_type,
        "--language",
        config.language,
        "--beam-size",
        str(config.beam_size),
        "--output",
        str(case.raw_file),
        "--timing-json",
        str(timing_file),
        "--initial-prompt",
        "" if config.initial_prompt is None else config.initial_prompt,
    ]
    command.append("--vad-filter" if config.vad_filter else "--no-vad-filter")
    return command


def run_transcribe_subprocess(
    *,
    transcribe_command: Path,
    case: LatencyCase,
    config: LatencyConfig,
    run_dir: Path,
) -> TranscriptionRun:
    timing_file = run_dir / "timing" / f"{case.sample_id}.json"
    command = build_transcribe_command(
        transcribe_command=transcribe_command,
        case=case,
        config=config,
        timing_file=timing_file,
    )
    started_at = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    subprocess_elapsed = time.monotonic() - started_at
    if completed.returncode != 0:
        raise ContractError(
            f"transcribe failed for {case.sample_id} with exit {completed.returncode}\n"
            f"stderr:\n{completed.stderr}"
        )

    if case.raw_file.exists():
        transcript = case.raw_file.read_text(encoding="utf-8").strip()
    else:
        transcript = completed.stdout.strip()
        case.raw_file.parent.mkdir(parents=True, exist_ok=True)
        case.raw_file.write_text(transcript + "\n", encoding="utf-8")
    case.recovered_file.parent.mkdir(parents=True, exist_ok=True)
    case.recovered_file.write_text(transcript + "\n", encoding="utf-8")

    timing: dict[str, Any] = {}
    if timing_file.exists():
        timing = load_json(timing_file)
    else:
        reported_elapsed = parse_reported_elapsed_seconds(completed.stderr)
        if reported_elapsed is not None:
            timing["internal_elapsed_seconds"] = reported_elapsed

    return TranscriptionRun(
        transcript=transcript,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
        subprocess_elapsed_seconds=round_elapsed(subprocess_elapsed),
        timing=timing,
    )


def timing_value(timing: dict[str, Any], key: str) -> float | None:
    value = timing.get(key)
    if isinstance(value, int | float):
        return round_elapsed(float(value))
    return None


def build_case_result(case: LatencyCase, transcription: TranscriptionRun) -> dict[str, Any]:
    quality_started_at = time.monotonic()
    result = accuracy.evaluate_case(
        case_id=case.case_id,
        sample_id=case.sample_id,
        category=case.category,
        metrics=case.metrics,
        expected=case.expected,
        actual=transcription.transcript,
        raw_file=case.raw_file.name,
        recovered_file=case.recovered_file.name,
    )
    quality_elapsed = time.monotonic() - quality_started_at

    latency = {
        "subprocess_elapsed_seconds": round_elapsed(
            transcription.subprocess_elapsed_seconds
        ),
        "transcribe_internal_elapsed_seconds": timing_value(
            transcription.timing,
            "internal_elapsed_seconds",
        ),
        "model_load_elapsed_seconds": timing_value(
            transcription.timing,
            "model_load_elapsed_seconds",
        ),
        "decode_elapsed_seconds": timing_value(
            transcription.timing,
            "decode_elapsed_seconds",
        ),
        "transcribe_call_elapsed_seconds": timing_value(
            transcription.timing,
            "transcribe_call_elapsed_seconds",
        ),
        "segment_iteration_elapsed_seconds": timing_value(
            transcription.timing,
            "segment_iteration_elapsed_seconds",
        ),
        "output_write_elapsed_seconds": timing_value(
            transcription.timing,
            "output_write_elapsed_seconds",
        ),
        "quality_eval_elapsed_seconds": round_elapsed(quality_elapsed),
    }
    result["latency"] = latency
    result["transcribe_info"] = {
        "audio_duration_seconds": timing_value(
            transcription.timing,
            "audio_duration_seconds",
        ),
        "detected_language": transcription.timing.get("detected_language"),
        "language_probability": timing_value(
            transcription.timing,
            "language_probability",
        ),
        "segment_count": transcription.timing.get("segment_count"),
    }
    result["artifacts"] = {
        "audio_file": case.audio_file.as_posix(),
        "raw_file": case.raw_file.as_posix(),
        "recovered_file": case.recovered_file.as_posix(),
    }
    return result


def average_numeric(values: Sequence[float | int | None]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, int | float)]
    if not numbers:
        return None
    return round_elapsed(sum(numbers) / len(numbers))


def summarize_latency(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "subprocess_elapsed_seconds",
        "transcribe_internal_elapsed_seconds",
        "model_load_elapsed_seconds",
        "decode_elapsed_seconds",
        "quality_eval_elapsed_seconds",
    )
    averages = {
        key: average_numeric([case["latency"].get(key) for case in case_results])
        for key in keys
    }
    totals = {
        key: round_elapsed(
            sum(
                float(case["latency"][key])
                for case in case_results
                if isinstance(case["latency"].get(key), int | float)
            )
        )
        for key in keys
    }
    return {"averages": averages, "totals": totals}


def load_baseline_reference(
    baseline_result: Path,
    sample_ids: Sequence[str],
    expected_by_sample: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not baseline_result.exists():
        return {"path": baseline_result.as_posix(), "exists": False}
    result = load_json(baseline_result)
    cases: dict[str, Any] = {}
    for sample_id in sample_ids:
        matching = next(
            (case for case in result.get("cases", []) if case.get("sample_id") == sample_id),
            None,
        )
        if matching is None:
            continue
        quality = matching.get("quality", {})
        current_expected = (expected_by_sample or {}).get(sample_id)
        baseline_expected = matching.get("text_comparison", {}).get("expected_text")
        cases[sample_id] = {
            "case_id": matching.get("case_id"),
            "category": matching.get("category"),
            "elapsed_seconds": matching.get("elapsed_seconds"),
            "failure_types": matching.get("failure_types", []),
            "case_score": quality.get("case_score"),
            "text_similarity": quality.get("text_similarity"),
            "normalized_char_error_rate": quality.get("normalized_char_error_rate"),
            "critical_token_f1": quality.get("critical_token_f1"),
            "expected_matches_current_input": (
                None if current_expected is None else baseline_expected == current_expected
            ),
        }
    return {
        "path": baseline_result.as_posix(),
        "exists": True,
        "run_id": result.get("run_id"),
        "total": result.get("total"),
        "failed": result.get("failed"),
        "quality_summary": result.get("quality_summary", {}),
        "cases": cases,
    }


def build_result_json(
    *,
    run_id: str,
    suite_path: Path,
    suite_id: str,
    input_set: str,
    input_root: Path,
    run_dir: Path,
    config: LatencyConfig,
    sample_ids: Sequence[str],
    case_results: list[dict[str, Any]],
    baseline_reference: dict[str, Any],
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "suite_id": suite_id,
        "suite_path": suite_path.as_posix(),
        "input_set": input_set,
        "input_root": input_root.as_posix(),
        "sample_ids": list(sample_ids),
        "run_dir": run_dir.as_posix(),
        "started_at_utc": started_at.isoformat(),
        "completed_at_utc": completed_at.isoformat(),
        "elapsed_seconds": round_elapsed((completed_at - started_at).total_seconds()),
        "config": config.to_json(),
        "baseline_reference": baseline_reference,
        "latency_summary": summarize_latency(case_results),
        "quality_summary": {
            "average_case_score": accuracy.average_or_none(
                [case["quality"]["case_score"] for case in case_results]
            ),
            "average_text_similarity": accuracy.average_or_none(
                [case["quality"]["text_similarity"] for case in case_results]
            ),
            "average_normalized_char_error_rate": accuracy.average_or_none(
                [
                    case["quality"]["normalized_char_error_rate"]
                    for case in case_results
                ]
            ),
            "average_critical_token_f1": accuracy.average_or_none(
                [case["quality"]["critical_token_f1"] for case in case_results]
            ),
        },
        "cases": case_results,
        "measurement_boundaries": {
            "file_based_only": True,
            "recording_stop_measured": False,
            "pty_injection_measured": False,
            "temp_audio_cleanup_measured": False,
            "subprocess_elapsed_seconds": (
                "Wall time around scripts/transcribe.sh, including shell, venv setup, "
                "Python startup, model load, decode, and transcript file write."
            ),
            "transcribe_internal_elapsed_seconds": (
                "scripts/transcribe.py internal elapsed time from model-load start "
                "through transcript output write."
            ),
            "decode_elapsed_seconds": (
                "faster-whisper transcribe call plus segment iteration; inference is "
                "mostly realized while iterating segments."
            ),
            "quality_eval_elapsed_seconds": (
                "Existing stt accuracy comparison after transcript capture."
            ),
        },
    }


def format_seconds(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.3f}"
    return "n/a"


def format_score(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.4f}"
    return "n/a"


def render_report(result: dict[str, Any]) -> str:
    baseline = result["baseline_reference"]
    lines = [
        "# STT Latency Baseline",
        "",
        "## Scope",
        "",
        "- Issue: `#29` under umbrella `#28`.",
        "- Measurement path: file-based `scripts/transcribe.sh` subprocess.",
        f"- Fixed smoke input set: `{', '.join(result['sample_ids'])}`.",
        "- Non-scope: persistent worker, adapter split, buffer handoff, release gap, beam/VAD experiments.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "STT_PYTHON_BIN=/path/to/.venv/bin/python \\",
        "STT_SITE_PACKAGES=/path/to/.venv/lib/python3.12/site-packages \\",
        "scripts/measure_stt_latency_baseline.py \\",
        f"  --run-id {result['run_id']} \\",
        f"  --input-root {result['input_root']} \\",
        f"  --baseline-result {baseline['path']} \\",
        f"  --model {result['config']['model']} \\",
        f"  --device {result['config']['device']} \\",
        f"  --compute-type {result['config']['compute_type']} \\",
        f"  --language {result['config']['language']} \\",
        "  --report-output evals/stt_accuracy/reports/2026-06-23-latency-baseline.md",
        "```",
        "",
        "If ignored WAV artifacts are absent in the current worktree, pass `--input-root`",
        "pointing at a local speech/v1 input root that contains `audio.wav` files.",
        "If the current worktree has no `.venv`, use `STT_PYTHON_BIN` and",
        "`STT_SITE_PACKAGES` to point `scripts/transcribe.sh` at an existing venv.",
        "",
        "## Config",
        "",
        f"- `run_id`: `{result['run_id']}`.",
        f"- `suite_id`: `{result['suite_id']}`.",
        f"- `input_set`: `{result['input_set']}`.",
        f"- `input_root`: `{result['input_root']}`.",
        f"- `run_dir`: `{result['run_dir']}`.",
        f"- `model`: `{result['config']['model']}`.",
        f"- `device`: `{result['config']['device']}`.",
        f"- `compute_type`: `{result['config']['compute_type']}`.",
        f"- `language`: `{result['config']['language']}`.",
        f"- `beam_size`: `{result['config']['beam_size']}`.",
        f"- `vad_filter`: `{result['config']['vad_filter']}`.",
        "",
        "## Accuracy Floor",
        "",
        "- Fixed smoke set에서 empty transcript 추가 발생 금지.",
        "- `cmd-0002`: exact 또는 normalized equivalent 유지.",
        "- `cmd-0018`: 현재 `speech/v1` 한글 음가 expected 기준으로 추가 악화 방지.",
        "- `cmd-0021`: 현재 `speech/v1` 한글 음가 expected 기준으로 추가 악화 방지.",
        "- `cmd-0024`: 현재 `speech/v1` 한글 음가 expected 기준으로 추가 악화 방지.",
        "- 후속 speed leaf의 fixed smoke 비교 기준은 이 report의 current-input case result다.",
        "- corrected corpus baseline artifact와 current `expected.txt`가 다르면 per-case quality delta를 직접 비교하지 않는다.",
        "- 전체 suite 실행 leaf: `average_case_score` 상대 5% 초과 하락 금지.",
        "- 전체 suite 실행 leaf: `average_normalized_char_error_rate` 상대 10% 초과 악화 금지.",
        "",
        "## Baseline Reference",
        "",
        f"- path: `{baseline['path']}`.",
    ]
    if baseline.get("exists"):
        quality_summary = baseline.get("quality_summary", {})
        expected_mismatches = [
            sample_id
            for sample_id, case in baseline.get("cases", {}).items()
            if case.get("expected_matches_current_input") is False
        ]
        lines.extend(
            [
                f"- run id: `{baseline.get('run_id')}`.",
                f"- total/failed: `{baseline.get('total')}` / `{baseline.get('failed')}`.",
                f"- average_case_score: `{format_score(quality_summary.get('average_case_score'))}`.",
                f"- average_text_similarity: `{format_score(quality_summary.get('average_text_similarity'))}`.",
                f"- average_normalized_char_error_rate: `{format_score(quality_summary.get('average_normalized_char_error_rate'))}`.",
                f"- average_critical_token_f1: `{format_score(quality_summary.get('average_critical_token_f1'))}`.",
            ]
        )
        if expected_mismatches:
            lines.append(
                "- warning: baseline reference `expected_text` differs from current "
                f"`expected.txt` for `{', '.join(expected_mismatches)}`; latency "
                "numbers are directly comparable, but quality deltas need contract review."
            )
    else:
        lines.append("- status: not present in this worktree.")

    lines.extend(
        [
            "",
            "## Latency Summary",
            "",
            "| field | average seconds | total seconds |",
            "| --- | ---: | ---: |",
        ]
    )
    summary = result["latency_summary"]
    for key, average in summary["averages"].items():
        lines.append(
            f"| `{key}` | {format_seconds(average)} | {format_seconds(summary['totals'].get(key))} |"
        )

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| sample | category | audio s | subprocess s | internal s | model load s | decode s | quality s | case score | failures | baseline score |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    baseline_cases = baseline.get("cases", {})
    for case in result["cases"]:
        sample_id = case["sample_id"]
        latency = case["latency"]
        transcribe_info = case["transcribe_info"]
        baseline_case = baseline_cases.get(sample_id, {})
        failures = ", ".join(case.get("failure_types", [])) or "none"
        lines.append(
            "| "
            f"{sample_id} | "
            f"{case['category']} | "
            f"{format_seconds(transcribe_info.get('audio_duration_seconds'))} | "
            f"{format_seconds(latency.get('subprocess_elapsed_seconds'))} | "
            f"{format_seconds(latency.get('transcribe_internal_elapsed_seconds'))} | "
            f"{format_seconds(latency.get('model_load_elapsed_seconds'))} | "
            f"{format_seconds(latency.get('decode_elapsed_seconds'))} | "
            f"{format_seconds(latency.get('quality_eval_elapsed_seconds'))} | "
            f"{format_score(case['quality'].get('case_score'))} | "
            f"{failures} | "
            f"{format_score(baseline_case.get('case_score'))} |"
        )

    lines.extend(
        [
            "",
            "## Measurement Boundary",
            "",
            "- Measured: `scripts/transcribe.sh` subprocess wall time.",
            "- Measured: `scripts/transcribe.py` internal model load, decode, output write timing via `--timing-json`.",
            "- Measured separately: transcript quality comparison using the existing STT accuracy harness.",
            "- Not measured in this file-based run: `arecord` stop, live temp WAV creation, PTY injection, temp audio cleanup.",
            "- Full CUDA suite not rerun for this leaf; fixed smoke set is the #28 governance comparison surface.",
            "",
        ]
    )
    return "\n".join(lines)


def run_latency_baseline(
    *,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    run_id: str,
    sample_ids: Sequence[str],
    config: LatencyConfig,
    baseline_result: Path,
    transcribe_command: Path,
    force: bool,
    runner: Runner | None = None,
) -> dict[str, Any]:
    suite = load_json(suite_path)
    run_dir = run_root / run_id
    if run_dir.exists() and not force:
        raise ContractError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "raw").mkdir(exist_ok=True)
    (run_dir / "recovered").mkdir(exist_ok=True)
    (run_dir / "timing").mkdir(exist_ok=True)

    cases = load_latency_cases(
        suite_path=suite_path,
        input_root=input_root,
        run_dir=run_dir,
        sample_ids=sample_ids,
    )
    selected_runner = runner
    if selected_runner is None:
        selected_runner = lambda case, cfg, rd: run_transcribe_subprocess(
            transcribe_command=transcribe_command,
            case=case,
            config=cfg,
            run_dir=rd,
        )

    started_at = datetime.now(timezone.utc)
    case_results: list[dict[str, Any]] = []
    for case in cases:
        transcription = selected_runner(case, config, run_dir)
        case_results.append(build_case_result(case, transcription))
    completed_at = datetime.now(timezone.utc)

    expected_by_sample = {case.sample_id: case.expected for case in cases}
    baseline_reference = load_baseline_reference(
        baseline_result,
        sample_ids,
        expected_by_sample,
    )
    result = build_result_json(
        run_id=run_id,
        suite_path=suite_path,
        suite_id=str(suite["suite_id"]),
        input_set=str(suite["input_set"]),
        input_root=input_root,
        run_dir=run_dir,
        config=config,
        sample_ids=sample_ids,
        case_results=case_results,
        baseline_reference=baseline_reference,
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
    config: LatencyConfig,
    baseline_result: Path,
) -> dict[str, Any]:
    run_dir = run_root / run_id
    cases = load_latency_cases(
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
        "config": config.to_json(),
        "sample_ids": list(sample_ids),
        "baseline_reference": load_baseline_reference(
            baseline_result,
            sample_ids,
            {case.sample_id: case.expected for case in cases},
        ),
        "cases": [
            {
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "category": case.category,
                "metrics": case.metrics,
                "audio_file": case.audio_file.as_posix(),
                "raw_file": case.raw_file.as_posix(),
                "recovered_file": case.recovered_file.as_posix(),
            }
            for case in cases
        ],
    }


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-stt-latency-baseline")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure file-based STT latency for the fixed #28 smoke set."
    )
    parser.add_argument("--suite", default=str(DEFAULT_SUITE), help="Suite id or manifest path.")
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT_ROOT), help="Speech input root.")
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT), help="Run artifact root.")
    parser.add_argument("--run-id", default=default_run_id(), help="Run artifact id.")
    parser.add_argument(
        "--sample-id",
        dest="sample_ids",
        action="append",
        help="Sample id to measure. Repeat to override the default fixed set.",
    )
    parser.add_argument("--model", default=accuracy.DEFAULT_MODEL)
    parser.add_argument("--device", default=accuracy.DEFAULT_DEVICE)
    parser.add_argument("--compute-type", default=accuracy.DEFAULT_COMPUTE_TYPE)
    parser.add_argument("--language", default=accuracy.DEFAULT_LANGUAGE)
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--initial-prompt", default=None)
    vad_group = parser.add_mutually_exclusive_group()
    vad_group.add_argument("--vad-filter", dest="vad_filter", action="store_true", default=True)
    vad_group.add_argument("--no-vad-filter", dest="vad_filter", action="store_false")
    parser.add_argument("--baseline-result", default=str(DEFAULT_BASELINE_RESULT))
    parser.add_argument("--transcribe-command", default=str(DEFAULT_TRANSCRIBE_COMMAND))
    parser.add_argument("--report-output", help="Optional Markdown report output path.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without loading model.")
    parser.add_argument("--force", action="store_true", help="Allow writing to an existing run dir.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    sample_ids = args.sample_ids or list(DEFAULT_SAMPLE_IDS)
    config = LatencyConfig(
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        beam_size=args.beam_size,
        initial_prompt=args.initial_prompt,
        vad_filter=args.vad_filter,
    )
    suite_path = resolve_suite(args.suite)
    input_root = Path(args.input_root)
    run_root = Path(args.run_root)
    baseline_result = Path(args.baseline_result)
    transcribe_command = Path(args.transcribe_command)

    try:
        if args.dry_run:
            dry_run = render_dry_run(
                suite_path=suite_path,
                input_root=input_root,
                run_root=run_root,
                run_id=args.run_id,
                sample_ids=sample_ids,
                config=config,
                baseline_result=baseline_result,
            )
            print(json.dumps(dry_run, ensure_ascii=False, indent=2))
            return 0

        result = run_latency_baseline(
            suite_path=suite_path,
            input_root=input_root,
            run_root=run_root,
            run_id=args.run_id,
            sample_ids=sample_ids,
            config=config,
            baseline_result=baseline_result,
            transcribe_command=transcribe_command,
            force=args.force,
        )
        if args.report_output:
            report_path = Path(args.report_output)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_report(result), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ContractError as error:
        print(f"contract error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
