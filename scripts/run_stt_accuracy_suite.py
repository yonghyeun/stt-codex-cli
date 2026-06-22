#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import string
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


DEFAULT_SUITE = Path("evals/stt_accuracy/suites/codex-command-accuracy-v1/manifest.json")
DEFAULT_INPUT_ROOT = Path("evals/inputs/speech/v1")
DEFAULT_RUN_ROOT = Path("evals/stt_accuracy/runs")
DEFAULT_MODEL = "large-v3"
DEFAULT_LANGUAGE = "ko"
DEFAULT_DEVICE = "cuda"
DEFAULT_COMPUTE_TYPE = "float16"
PUNCTUATION_TABLE = str.maketrans(
    "",
    "",
    string.punctuation + "，。！？、…·“”‘’「」『』《》〈〉",
)


class ContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    model: str
    device: str
    compute_type: str
    language: str
    beam_size: int
    initial_prompt: str | None
    token_recovery: str

    def to_json(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "beam_size": self.beam_size,
            "initial_prompt": self.initial_prompt,
            "token_recovery": self.token_recovery,
        }


@dataclass(frozen=True)
class CasePlan:
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
class RunPlan:
    suite_id: str
    input_set: str
    run_id: str
    run_root: Path
    run_dir: Path
    config: RunConfig
    cases: list[CasePlan]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"required file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"invalid json: {path}: {error}") from error


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = text.translate(PUNCTUATION_TABLE)
    return re.sub(r"\s+", "", text)


def transcript_has_text(text: str) -> bool:
    return any(char.isalnum() for char in text)


def is_punctuation_only(text: str) -> bool:
    return bool(text.strip()) and not transcript_has_text(text)


def unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def latin_tokens(text: str) -> list[str]:
    pattern = r"(?<![A-Za-z0-9_])(?:[A-Za-z][A-Za-z0-9_]*(?:[./:-][A-Za-z0-9_]+)*)(?![A-Za-z0-9_])"
    return unique_in_order(re.findall(pattern, text))


def cli_option_tokens(text: str) -> list[str]:
    return unique_in_order(re.findall(r"--[A-Za-z0-9][A-Za-z0-9_-]*", text))


def file_path_tokens(text: str) -> list[str]:
    tokens = latin_tokens(text)
    return [
        token
        for token in tokens
        if "/" in token or re.search(r"\.[A-Za-z0-9]{1,8}$", token)
    ]


def code_identifier_tokens(text: str) -> list[str]:
    tokens = latin_tokens(text)
    return [
        token
        for token in tokens
        if "_" in token
        or "." in token
        or token.endswith("()")
        or token[0].islower()
    ]


def missing_tokens(expected_tokens: list[str], actual: str) -> list[str]:
    normalized_actual = normalize(actual)
    missing: list[str] = []
    for token in expected_tokens:
        if normalize(token) not in normalized_actual:
            missing.append(token)
    return missing


def edit_distance(expected: Sequence[Any], actual: Sequence[Any]) -> int:
    previous = list(range(len(actual) + 1))
    for expected_index, expected_item in enumerate(expected, start=1):
        current = [expected_index]
        for actual_index, actual_item in enumerate(actual, start=1):
            insertion = current[actual_index - 1] + 1
            deletion = previous[actual_index] + 1
            substitution = previous[actual_index - 1] + (
                0 if expected_item == actual_item else 1
            )
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def error_rate(distance: int, expected_length: int, actual_length: int) -> float:
    if expected_length == 0:
        return 0.0 if actual_length == 0 else 1.0
    return round(distance / expected_length, 4)


def similarity(distance: int, expected_length: int, actual_length: int) -> float:
    denominator = max(expected_length, actual_length)
    if denominator == 0:
        return 1.0
    return round(1.0 - (distance / denominator), 4)


def ratio_or_none(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None and recall is None:
        return None
    if not precision or not recall:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def average_or_none(values: list[float | None]) -> float | None:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 4)


def build_critical_token_quality(expected: str, actual: str) -> dict[str, Any]:
    expected_tokens = latin_tokens(expected)
    actual_tokens = latin_tokens(actual)
    normalized_actual = normalize(actual)
    expected_terms = set(normalize(token) for token in expected_tokens)
    preserved = [
        token for token in expected_tokens if normalize(token) in normalized_actual
    ]
    missing = [
        token for token in expected_tokens if normalize(token) not in normalized_actual
    ]
    matched_actual = [
        token for token in actual_tokens if normalize(token) in expected_terms
    ]
    unexpected = [
        token for token in actual_tokens if normalize(token) not in expected_terms
    ]
    precision = ratio_or_none(len(matched_actual), len(actual_tokens))
    recall = ratio_or_none(len(preserved), len(expected_tokens))

    if expected_tokens and not actual_tokens:
        precision = 0.0
    if actual_tokens and not expected_tokens:
        recall = 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1_score(precision, recall),
        "tokens": {
            "expected": expected_tokens,
            "preserved": preserved,
            "missing": missing,
            "unexpected": unexpected,
        },
    }


def build_quality(expected: str, actual: str) -> dict[str, Any]:
    normalized_expected = normalize(expected)
    normalized_actual = normalize(actual)
    distance = edit_distance(expected, actual)
    normalized_distance = edit_distance(normalized_expected, normalized_actual)
    word_distance = edit_distance(expected.split(), actual.split())
    critical_token_quality = build_critical_token_quality(expected, actual)
    token_f1 = critical_token_quality["f1"]
    text_similarity = similarity(
        normalized_distance,
        len(normalized_expected),
        len(normalized_actual),
    )
    insertion_safe_score = (
        1.0 if transcript_has_text(actual) and not is_punctuation_only(actual) else 0.0
    )
    hallucination_penalty = min(
        0.2,
        len(critical_token_quality["tokens"]["unexpected"]) * 0.05,
    )
    if token_f1 is None:
        case_score = (0.8 * text_similarity) + (0.2 * insertion_safe_score)
    else:
        case_score = (
            (0.4 * text_similarity)
            + (0.4 * token_f1)
            + (0.2 * insertion_safe_score)
            - hallucination_penalty
        )

    return {
        "edit_distance": distance,
        "char_error_rate": error_rate(distance, len(expected), len(actual)),
        "normalized_edit_distance": normalized_distance,
        "normalized_char_error_rate": error_rate(
            normalized_distance,
            len(normalized_expected),
            len(normalized_actual),
        ),
        "text_similarity": text_similarity,
        "word_error_rate": error_rate(
            word_distance,
            len(expected.split()),
            len(actual.split()),
        ),
        "critical_token_precision": critical_token_quality["precision"],
        "critical_token_recall": critical_token_quality["recall"],
        "critical_token_f1": token_f1,
        "case_score": round(max(0.0, min(1.0, case_score)), 4),
        "critical_tokens": critical_token_quality["tokens"],
    }


def metric_result(passed: bool, **details: Any) -> dict[str, Any]:
    return {"passed": passed, **details}


def evaluate_case(
    *,
    case_id: str,
    sample_id: str,
    category: str,
    metrics: list[str],
    expected: str,
    actual: str,
    recovered: str | None = None,
    raw_file: str,
    recovered_file: str,
) -> dict[str, Any]:
    recovered_text = actual if recovered is None else recovered
    exact_match = expected == actual
    normalized_match = normalize(expected) == normalize(actual)
    metric_results: dict[str, Any] = {
        "exact_match": metric_result(exact_match),
        "normalized_match": metric_result(normalized_match),
    }
    failure_types: list[str] = []

    if not actual.strip():
        failure_types.append("empty_transcript")
    elif is_punctuation_only(actual):
        failure_types.append("punctuation_only")

    if "korean_command_match" in metrics:
        passed = normalized_match
        metric_results["korean_command_match"] = metric_result(passed)
        if not passed:
            failure_types.append("korean_command_mismatch")

    if "phonetic_transcript_match" in metrics:
        passed = normalized_match
        metric_results["phonetic_transcript_match"] = metric_result(passed)
        if not passed:
            failure_types.append("phonetic_transcript_mismatch")

    if "latin_token_preservation" in metrics:
        tokens = latin_tokens(expected)
        missing = missing_tokens(tokens, actual)
        passed = len(missing) == 0
        metric_results["latin_token_preservation"] = metric_result(
            passed,
            expected_tokens=tokens,
            missing_tokens=missing,
        )
        if not passed:
            failure_types.append("latin_token_loss")

    if "file_path_preservation" in metrics:
        tokens = file_path_tokens(expected)
        missing = missing_tokens(tokens, actual)
        passed = len(missing) == 0
        metric_results["file_path_preservation"] = metric_result(
            passed,
            expected_tokens=tokens,
            missing_tokens=missing,
        )
        if not passed:
            failure_types.append("file_path_loss")

    if "cli_option_preservation" in metrics:
        tokens = cli_option_tokens(expected)
        missing = missing_tokens(tokens, actual)
        passed = len(missing) == 0
        metric_results["cli_option_preservation"] = metric_result(
            passed,
            expected_tokens=tokens,
            missing_tokens=missing,
        )
        if not passed:
            failure_types.append("cli_option_loss")

    if "code_identifier_preservation" in metrics:
        tokens = code_identifier_tokens(expected)
        missing = missing_tokens(tokens, actual)
        passed = len(missing) == 0
        metric_results["code_identifier_preservation"] = metric_result(
            passed,
            expected_tokens=tokens,
            missing_tokens=missing,
        )
        if not passed:
            failure_types.append("code_identifier_loss")

    if "insertion_safe" in metrics:
        passed = transcript_has_text(actual) and not is_punctuation_only(actual)
        metric_results["insertion_safe"] = metric_result(passed)
        if not passed:
            failure_types.append("insertion_unsafe")

    expected_terms = set(normalize(token) for token in latin_tokens(expected))
    unexpected_latin = [
        token
        for token in latin_tokens(actual)
        if normalize(token) not in expected_terms
    ]
    if unexpected_latin:
        failure_types.append("hallucination")
        metric_results["hallucination"] = metric_result(
            False,
            unexpected_latin_tokens=unexpected_latin,
        )
    else:
        metric_results["hallucination"] = metric_result(True, unexpected_latin_tokens=[])

    return {
        "case_id": case_id,
        "sample_id": sample_id,
        "category": category,
        "text_comparison": {
            "expected_text": expected,
            "raw_text": actual,
            "recovered_text": recovered_text,
            "normalized_expected": normalize(expected),
            "normalized_raw": normalize(actual),
            "normalized_recovered": normalize(recovered_text),
        },
        "quality": build_quality(expected, recovered_text),
        "metrics": metric_results,
        "failure_types": unique_in_order(failure_types),
        "raw_file": raw_file,
        "recovered_file": recovered_file,
    }


def relative_to_run_dir(path: Path, run_dir: Path) -> str:
    return path.relative_to(run_dir).as_posix()


def validate_manifest_link(suite: dict[str, Any], input_manifest: dict[str, Any]) -> None:
    suite_input = suite.get("input_set")
    manifest_input = input_manifest.get("input_set")
    if suite_input != manifest_input:
        raise ContractError(
            f"input_set mismatch: suite={suite_input!r} input_manifest={manifest_input!r}"
        )


def build_plan(
    *,
    suite_path: Path,
    input_root: Path,
    run_root: Path,
    run_id: str,
    config: RunConfig,
) -> RunPlan:
    suite = load_json(suite_path)
    input_manifest = load_json(input_root / "manifest.json")
    validate_manifest_link(suite, input_manifest)

    sample_ids = set(input_manifest.get("sample_ids", []))
    run_dir = run_root / run_id
    cases: list[CasePlan] = []
    errors: list[str] = []

    for case in suite.get("cases", []):
        case_id = str(case.get("case_id", ""))
        sample_id = str(case.get("sample_id", ""))
        category = str(case.get("category", ""))
        metrics = [str(metric) for metric in case.get("metrics", [])]
        sample_dir = input_root / "samples" / sample_id
        audio_file = sample_dir / "audio.wav"
        expected_file = sample_dir / "expected.txt"
        metadata_file = sample_dir / "metadata.json"

        if not case_id:
            errors.append("case missing case_id")
        if sample_id not in sample_ids:
            errors.append(f"{case_id}: sample_id not in input manifest: {sample_id}")
        for required_file in (audio_file, expected_file, metadata_file):
            if not required_file.exists():
                errors.append(f"{case_id}: required file not found: {required_file}")

        if expected_file.exists():
            expected = expected_file.read_text(encoding="utf-8").strip()
        else:
            expected = ""

        cases.append(
            CasePlan(
                case_id=case_id,
                sample_id=sample_id,
                category=category,
                metrics=metrics,
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

    return RunPlan(
        suite_id=str(suite["suite_id"]),
        input_set=str(suite["input_set"]),
        run_id=run_id,
        run_root=run_root,
        run_dir=run_dir,
        config=config,
        cases=cases,
    )


def render_dry_run(plan: RunPlan) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": "dry-run",
        "suite_id": plan.suite_id,
        "input_set": plan.input_set,
        "run_id": plan.run_id,
        "run_dir": plan.run_dir.as_posix(),
        "config": plan.config.to_json(),
        "case_count": len(plan.cases),
        "cases": [
            {
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "category": case.category,
                "metrics": case.metrics,
                "audio_file": case.audio_file.as_posix(),
                "expected_file": case.expected_file.as_posix(),
                "metadata_file": case.metadata_file.as_posix(),
                "raw_file": relative_to_run_dir(case.raw_file, plan.run_dir),
                "recovered_file": relative_to_run_dir(case.recovered_file, plan.run_dir),
            }
            for case in plan.cases
        ],
    }


def transcribe_audio(audio_file: Path, config: RunConfig, model: Any) -> tuple[str, float]:
    from transcribe import initial_prompt_arg, language_arg

    started_at = time.monotonic()
    segments, _ = model.transcribe(
        str(audio_file),
        language=language_arg(config.language),
        beam_size=config.beam_size,
        initial_prompt=initial_prompt_arg(config.initial_prompt),
        vad_filter=True,
        condition_on_previous_text=False,
    )
    transcript = " ".join(
        segment.text.strip() for segment in segments if segment.text.strip()
    ).strip()
    return transcript, time.monotonic() - started_at


def write_run_artifacts(plan: RunPlan) -> dict[str, Any]:
    from faster_whisper import WhisperModel

    started_at = datetime.now(timezone.utc)
    plan.run_dir.mkdir(parents=True, exist_ok=False)
    (plan.run_dir / "raw").mkdir()
    (plan.run_dir / "recovered").mkdir()

    model = WhisperModel(
        plan.config.model,
        device=plan.config.device,
        compute_type=plan.config.compute_type,
    )

    case_results: list[dict[str, Any]] = []
    total_elapsed = 0.0
    for case in plan.cases:
        actual, elapsed = transcribe_audio(case.audio_file, plan.config, model)
        total_elapsed += elapsed
        case.raw_file.write_text(actual + "\n", encoding="utf-8")
        case.recovered_file.write_text(actual + "\n", encoding="utf-8")
        result = evaluate_case(
            case_id=case.case_id,
            sample_id=case.sample_id,
            category=case.category,
            metrics=case.metrics,
            expected=case.expected,
            actual=actual,
            raw_file=relative_to_run_dir(case.raw_file, plan.run_dir),
            recovered_file=relative_to_run_dir(case.recovered_file, plan.run_dir),
        )
        result["elapsed_seconds"] = round(elapsed, 3)
        case_results.append(result)

    result_json = build_result_json(plan, case_results, total_elapsed)
    metadata_json = build_metadata_json(plan, started_at, datetime.now(timezone.utc))
    (plan.run_dir / "result.json").write_text(
        json.dumps(result_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (plan.run_dir / "metadata.json").write_text(
        json.dumps(metadata_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result_json


def build_result_json(
    plan: RunPlan,
    case_results: list[dict[str, Any]],
    elapsed_seconds: float,
) -> dict[str, Any]:
    category_summary: dict[str, dict[str, int]] = {}
    failure_summary: dict[str, int] = {}
    for result in case_results:
        category = result["category"]
        summary = category_summary.setdefault(category, {"total": 0, "failed": 0})
        summary["total"] += 1
        if result["failure_types"]:
            summary["failed"] += 1
        for failure_type in result["failure_types"]:
            failure_summary[failure_type] = failure_summary.get(failure_type, 0) + 1

    return {
        "schema_version": 1,
        "suite_id": plan.suite_id,
        "input_set": plan.input_set,
        "run_id": plan.run_id,
        "config": plan.config.to_json(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "total": len(case_results),
        "failed": sum(1 for result in case_results if result["failure_types"]),
        "category_summary": category_summary,
        "failure_summary": failure_summary,
        "quality_summary": {
            "average_case_score": average_or_none(
                [result["quality"]["case_score"] for result in case_results]
            ),
            "average_text_similarity": average_or_none(
                [result["quality"]["text_similarity"] for result in case_results]
            ),
            "average_normalized_char_error_rate": average_or_none(
                [
                    result["quality"]["normalized_char_error_rate"]
                    for result in case_results
                ]
            ),
            "average_critical_token_f1": average_or_none(
                [result["quality"]["critical_token_f1"] for result in case_results]
            ),
        },
        "cases": case_results,
    }


def build_metadata_json(
    plan: RunPlan,
    started_at: datetime,
    completed_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": plan.run_id,
        "suite_id": plan.suite_id,
        "input_set": plan.input_set,
        "started_at_utc": started_at.isoformat(),
        "completed_at_utc": completed_at.isoformat(),
        "config": plan.config.to_json(),
        "artifact_contract": {
            "raw": "raw/<sample_id>.txt",
            "recovered": "recovered/<sample_id>.txt",
            "result": "result.json",
            "metadata": "metadata.json",
        },
    }


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-stt-accuracy-baseline")


def resolve_suite(value: str) -> Path:
    path = Path(value)
    if path.exists() or "/" in value:
        return path
    return Path("evals/stt_accuracy/suites") / value / "manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or dry-run the Codex command STT accuracy suite."
    )
    parser.add_argument("--suite", default=str(DEFAULT_SUITE), help="Suite id or manifest path.")
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT_ROOT), help="Input set root.")
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT), help="Run artifact root.")
    parser.add_argument("--run-id", default=default_run_id(), help="Run artifact id.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--compute-type", default=DEFAULT_COMPUTE_TYPE)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--initial-prompt", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print plan only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = RunConfig(
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        beam_size=args.beam_size,
        initial_prompt=args.initial_prompt,
        token_recovery="none",
    )

    try:
        plan = build_plan(
            suite_path=resolve_suite(args.suite),
            input_root=Path(args.input_root),
            run_root=Path(args.run_root),
            run_id=args.run_id,
            config=config,
        )
        if args.dry_run:
            print(json.dumps(render_dry_run(plan), ensure_ascii=False, indent=2))
            return 0
        result = write_run_artifacts(plan)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ContractError as error:
        print(f"contract error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
