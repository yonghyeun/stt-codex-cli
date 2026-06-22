from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import render_stt_accuracy_result


class SttAccuracyResultRendererTest(unittest.TestCase):
    def test_render_markdown_summarizes_quality_and_cases(self) -> None:
        result = {
            "schema_version": 1,
            "suite_id": "codex-command-accuracy-v1",
            "input_set": "speech/v1",
            "run_id": "run-001",
            "config": {
                "model": "large-v3",
                "device": "cuda",
                "compute_type": "float16",
                "language": "ko",
            },
            "elapsed_seconds": 12.345,
            "total": 2,
            "failed": 1,
            "category_summary": {
                "code_switch": {"total": 2, "failed": 1},
            },
            "failure_summary": {
                "latin_token_loss": 1,
            },
            "quality_summary": {
                "average_case_score": 0.75,
                "average_text_similarity": 0.8,
                "average_normalized_char_error_rate": 0.2,
                "average_critical_token_f1": 0.7,
            },
            "cases": [
                {
                    "case_id": "code-switch-001",
                    "sample_id": "cmd-0001",
                    "category": "code_switch",
                    "text_comparison": {
                        "expected_text": "STT accuracy eval 확인해줘",
                        "raw_text": "STT 어큐러시 이벨 확인해줘",
                        "recovered_text": "STT 어큐러시 이벨 확인해줘",
                    },
                    "quality": {
                        "case_score": 0.5,
                        "text_similarity": 0.6,
                        "normalized_char_error_rate": 0.4,
                        "critical_token_f1": 0.25,
                    },
                    "failure_types": ["latin_token_loss"],
                },
                {
                    "case_id": "code-switch-002",
                    "sample_id": "cmd-0002",
                    "category": "code_switch",
                    "text_comparison": {
                        "expected_text": "manifest 확인해줘",
                        "raw_text": "manifest 확인해줘",
                        "recovered_text": "manifest 확인해줘",
                    },
                    "quality": {
                        "case_score": 1.0,
                        "text_similarity": 1.0,
                        "normalized_char_error_rate": 0.0,
                        "critical_token_f1": 1.0,
                    },
                    "failure_types": [],
                },
            ],
        }

        markdown = render_stt_accuracy_result.render_markdown(result)

        self.assertIn("# STT Accuracy Result", markdown)
        self.assertIn("- `run_id`: `run-001`", markdown)
        self.assertIn("| average_case_score | 0.7500 |", markdown)
        self.assertIn("| code_switch | 2 | 1 | 50.00% |", markdown)
        self.assertIn("| latin_token_loss | 1 |", markdown)
        self.assertIn(
            "| code-switch-001 | cmd-0001 | code_switch | 0.5000 | 0.6000 | 0.4000 | 0.2500 | latin_token_loss | STT accuracy eval 확인해줘 | STT 어큐러시 이벨 확인해줘 |",
            markdown,
        )
        self.assertNotIn("### code-switch-001", markdown)

    def test_render_markdown_routes_metric_contract_descriptions(self) -> None:
        result = {
            "schema_version": 1,
            "suite_id": "codex-command-accuracy-v1",
            "input_set": "speech/v1",
            "run_id": "run-001",
            "config": {},
            "elapsed_seconds": 1.0,
            "total": 1,
            "failed": 1,
            "category_summary": {},
            "failure_summary": {
                "latin_token_loss": 1,
            },
            "quality_summary": {
                "average_case_score": 0.75,
                "average_text_similarity": 0.8,
                "average_normalized_char_error_rate": 0.2,
                "average_critical_token_f1": 0.7,
            },
            "cases": [],
        }

        markdown = render_stt_accuracy_result.render_markdown(result)

        self.assertIn("## Metric Contract", markdown)
        self.assertIn(
            "| average_case_score | case_score | 높을수록 좋음 |", markdown
        )
        self.assertIn(
            "| average_normalized_char_error_rate | normalized_char_error_rate | 낮을수록 좋음 |",
            markdown,
        )
        self.assertIn(
            "| latin_token_loss | expected의 Latin-script token 보존 실패. |",
            markdown,
        )

    def test_default_metric_contract_covers_renderer_summary_and_failures(self) -> None:
        contract = render_stt_accuracy_result.load_metric_contract()

        quality_metrics = contract["quality_metrics"]
        summary_routes = contract["summary_routes"]
        failure_types = contract["failure_types"]

        for summary_key in (
            "average_case_score",
            "average_text_similarity",
            "average_normalized_char_error_rate",
            "average_critical_token_f1",
        ):
            source_metric = summary_routes[summary_key]
            self.assertIn(source_metric, quality_metrics)
            self.assertIn("description", quality_metrics[source_metric])
            self.assertIn("direction", quality_metrics[source_metric])

        for failure_type in (
            "korean_command_mismatch",
            "latin_token_loss",
            "file_path_loss",
            "cli_option_loss",
            "code_identifier_loss",
            "hallucination",
            "empty_transcript",
            "punctuation_only",
            "insertion_unsafe",
        ):
            self.assertIn(failure_type, failure_types)
            self.assertIn("description", failure_types[failure_type])

    def test_render_markdown_can_include_full_text_blocks(self) -> None:
        result = {
            "schema_version": 1,
            "suite_id": "codex-command-accuracy-v1",
            "input_set": "speech/v1",
            "run_id": "run-001",
            "config": {},
            "elapsed_seconds": 1.0,
            "total": 1,
            "failed": 1,
            "category_summary": {},
            "failure_summary": {},
            "quality_summary": {},
            "cases": [
                {
                    "case_id": "case-001",
                    "sample_id": "cmd-0001",
                    "category": "code_switch",
                    "text_comparison": {
                        "expected_text": "expected text",
                        "raw_text": "raw text",
                        "recovered_text": "recovered text",
                    },
                    "quality": {},
                    "failure_types": ["latin_token_loss"],
                }
            ],
        }

        markdown = render_stt_accuracy_result.render_markdown(result, show_text=True)

        self.assertIn("### case-001 / cmd-0001", markdown)
        self.assertIn("```text\nexpected text\n```", markdown)
        self.assertIn("```text\nraw text\n```", markdown)
        self.assertIn("```text\nrecovered text\n```", markdown)

    def test_main_reads_result_json_and_prints_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "suite_id": "suite",
                        "input_set": "speech/v1",
                        "run_id": "run-001",
                        "config": {},
                        "elapsed_seconds": 1.0,
                        "total": 0,
                        "failed": 0,
                        "category_summary": {},
                        "failure_summary": {},
                        "quality_summary": {},
                        "cases": [],
                    }
                ),
                encoding="utf-8",
            )

            output = render_stt_accuracy_result.main_to_text([str(result_path)])

        self.assertIn("- `run_id`: `run-001`", output)


if __name__ == "__main__":
    unittest.main()
