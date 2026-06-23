from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from scripts import evaluate_beam_vad_tradeoff as tradeoff


def write_minimal_input(root: Path) -> tuple[Path, Path]:
    input_root = root / "evals" / "inputs" / "speech" / "v1"
    sample_dir = input_root / "samples" / "cmd-0002"
    suite_path = root / "suite.json"
    sample_dir.mkdir(parents=True)
    (sample_dir / "audio.wav").write_bytes(b"RIFF fake wav")
    (sample_dir / "expected.txt").write_text("hello\n", encoding="utf-8")
    (sample_dir / "metadata.json").write_text(
        json.dumps({"sample_id": "cmd-0002"}),
        encoding="utf-8",
    )
    (input_root / "manifest.json").write_text(
        json.dumps(
            {
                "input_set": "speech/v1",
                "version": 1,
                "sample_ids": ["cmd-0002"],
            }
        ),
        encoding="utf-8",
    )
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "codex-command-accuracy-v1",
                "input_set": "speech/v1",
                "cases": [
                    {
                        "case_id": "korean-command-002",
                        "sample_id": "cmd-0002",
                        "category": "korean_command",
                        "metrics": ["phonetic_transcript_match", "insertion_safe"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return input_root, suite_path


def make_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "run_id_prefix": "unit-beam-vad",
        "model": "large-v3",
        "device": "cuda",
        "compute_type": "float16",
        "language": "ko",
        "initial_prompt": "",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class BeamVadTradeoffTest(unittest.TestCase):
    def test_render_dry_run_lists_fixed_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root, suite_path = write_minimal_input(root)

            plan = tradeoff.render_dry_run(
                args=make_args(),
                suite_path=suite_path,
                input_root=input_root,
                run_root=root / "runs",
                sample_ids=["cmd-0002"],
            )

            self.assertEqual(plan["coverage"], "fixed-smoke-only")
            self.assertEqual(
                [combo["combo_id"] for combo in plan["combos"]],
                ["beam5-vad-on", "beam1-vad-on", "beam5-vad-off", "beam1-vad-off"],
            )
            self.assertEqual(plan["cases"][0]["sample_id"], "cmd-0002")

    def test_case_floor_decision_uses_29_fixed_smoke_score(self) -> None:
        passing_case = {
            "sample_id": "cmd-0018",
            "text_comparison": {"raw_text": "transcript"},
            "quality": {"case_score": 0.3147},
        }
        failing_case = {
            "sample_id": "cmd-0018",
            "text_comparison": {"raw_text": "transcript"},
            "quality": {"case_score": 0.10},
        }

        self.assertEqual(tradeoff.case_floor_decision(passing_case), "pass")
        self.assertEqual(
            tradeoff.case_floor_decision(failing_case),
            "fail_quality_regression",
        )

    def test_summarize_combo_reports_default_and_29_latency_deltas(self) -> None:
        result = {
            "run_id": "unit-beam1-vad-on",
            "combo": {
                "combo_id": "beam1-vad-on",
                "beam_size": 1,
                "vad_filter": True,
            },
            "latency_summary": {
                "averages": {
                    "subprocess_elapsed_seconds": 5.0,
                    "decode_elapsed_seconds": 1.0,
                }
            },
            "quality_summary": {
                "average_case_score": 1.0,
                "average_normalized_char_error_rate": 0.0,
                "average_text_similarity": 1.0,
                "average_critical_token_f1": 1.0,
            },
            "cases": [
                {
                    "sample_id": "cmd-0002",
                    "text_comparison": {"raw_text": "hello"},
                    "quality": {"case_score": 1.0},
                }
            ],
        }

        summary = tradeoff.summarize_combo(result, default_average=6.0)

        self.assertEqual(summary["latency_delta_vs_default_seconds"], -1.0)
        self.assertEqual(summary["latency_delta_vs_prior_29_seconds"], -0.956)
        self.assertEqual(summary["floor_decision"], "pass")
        self.assertEqual(
            summary["speed_profile_decision"],
            "fixed-smoke-only-candidate",
        )


if __name__ == "__main__":
    unittest.main()
