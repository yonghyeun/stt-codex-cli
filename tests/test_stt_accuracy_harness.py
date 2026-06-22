from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts import run_stt_accuracy_suite


REPO_ROOT = Path(__file__).resolve().parents[1]


class SttAccuracyHarnessTest(unittest.TestCase):
    def test_dry_run_builds_case_plan_without_writing_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "evals" / "inputs" / "speech" / "v1"
            sample_dir = input_root / "samples" / "cmd-0001"
            suite_path = root / "evals" / "stt_accuracy" / "suites" / "suite" / "manifest.json"
            run_root = root / "evals" / "stt_accuracy" / "runs"

            sample_dir.mkdir(parents=True)
            suite_path.parent.mkdir(parents=True)
            (sample_dir / "audio.wav").write_bytes(b"fake wav")
            (sample_dir / "expected.txt").write_text(
                "scripts/transcribe.sh --model large-v3 실행해줘\n",
                encoding="utf-8",
            )
            (sample_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "sample_id": "cmd-0001",
                        "prompt_id": "P01",
                        "category": "cli_option",
                        "recording_status": "recorded",
                    }
                ),
                encoding="utf-8",
            )
            (input_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "input_set": "speech/v1",
                        "version": 1,
                        "sample_ids": ["cmd-0001"],
                    }
                ),
                encoding="utf-8",
            )
            suite_path.write_text(
                json.dumps(
                    {
                        "suite_id": "codex-command-accuracy-v1",
                        "input_set": "speech/v1",
                        "version": 1,
                        "cases": [
                            {
                                "case_id": "cli-option-001",
                                "sample_id": "cmd-0001",
                                "category": "cli_option",
                                "metrics": ["cli_option_preservation", "insertion_safe"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            plan = run_stt_accuracy_suite.build_plan(
                suite_path=suite_path,
                input_root=input_root,
                run_root=run_root,
                run_id="20260621-baseline-contract",
                config=run_stt_accuracy_suite.RunConfig(
                    model="large-v3",
                    device="cuda",
                    compute_type="float16",
                    language="ko",
                    beam_size=5,
                    initial_prompt=None,
                    token_recovery="none",
                ),
            )

            dry_run = run_stt_accuracy_suite.render_dry_run(plan)

            self.assertEqual(dry_run["mode"], "dry-run")
            self.assertEqual(dry_run["case_count"], 1)
            self.assertEqual(dry_run["cases"][0]["case_id"], "cli-option-001")
            self.assertEqual(dry_run["cases"][0]["sample_id"], "cmd-0001")
            self.assertEqual(dry_run["cases"][0]["raw_file"], "raw/cmd-0001.txt")
            self.assertEqual(dry_run["cases"][0]["recovered_file"], "recovered/cmd-0001.txt")
            self.assertFalse(run_root.exists())

    def test_missing_audio_is_a_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "evals" / "inputs" / "speech" / "v1"
            sample_dir = input_root / "samples" / "cmd-0001"
            suite_path = root / "manifest.json"

            sample_dir.mkdir(parents=True)
            (sample_dir / "expected.txt").write_text("README 수정해\n", encoding="utf-8")
            (sample_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "sample_id": "cmd-0001",
                        "prompt_id": "P01",
                        "category": "korean_command",
                        "recording_status": "recorded",
                    }
                ),
                encoding="utf-8",
            )
            (input_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "input_set": "speech/v1",
                        "version": 1,
                        "sample_ids": ["cmd-0001"],
                    }
                ),
                encoding="utf-8",
            )
            suite_path.write_text(
                json.dumps(
                    {
                        "suite_id": "codex-command-accuracy-v1",
                        "input_set": "speech/v1",
                        "version": 1,
                        "cases": [
                            {
                                "case_id": "korean-command-001",
                                "sample_id": "cmd-0001",
                                "category": "korean_command",
                                "metrics": ["korean_command_match"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(run_stt_accuracy_suite.ContractError, "audio.wav"):
                run_stt_accuracy_suite.build_plan(
                    suite_path=suite_path,
                    input_root=input_root,
                    run_root=root / "runs",
                    run_id="missing-audio",
                    config=run_stt_accuracy_suite.RunConfig(
                        model="large-v3",
                        device="cuda",
                        compute_type="float16",
                        language="ko",
                        beam_size=5,
                        initial_prompt=None,
                        token_recovery="none",
                    ),
                )

    def test_failure_taxonomy_marks_missing_cli_option_and_latin_token(self) -> None:
        result = run_stt_accuracy_suite.evaluate_case(
            case_id="cli-option-001",
            sample_id="cmd-0001",
            category="cli_option",
            metrics=["cli_option_preservation", "latin_token_preservation", "insertion_safe"],
            expected="--stt-model large-v3 --stt-device cuda 조합으로 실행해줘",
            actual="모델 라지 브이 쓰리 쿠다 조합으로 실행해줘",
            raw_file="raw/cmd-0001.txt",
            recovered_file="recovered/cmd-0001.txt",
        )

        self.assertFalse(result["metrics"]["cli_option_preservation"]["passed"])
        self.assertFalse(result["metrics"]["latin_token_preservation"]["passed"])
        self.assertIn("cli_option_loss", result["failure_types"])
        self.assertIn("latin_token_loss", result["failure_types"])
        self.assertTrue(result["metrics"]["insertion_safe"]["passed"])

    def test_local_eval_contract_docs_do_not_depend_on_remote_workflow_terms(self) -> None:
        docs = [
            REPO_ROOT / "evals" / "README.md",
            REPO_ROOT / "evals" / "inputs" / "speech" / "v1" / "manifest.json",
            REPO_ROOT / "evals" / "stt_accuracy" / "README.md",
            REPO_ROOT / "evals" / "stt_accuracy" / "reports" / "README.md",
            REPO_ROOT / "evals" / "stt_accuracy" / "reports" / "2026-06-21-governance.md",
            REPO_ROOT
            / "evals"
            / "stt_accuracy"
            / "reports"
            / "2026-06-21-corpus-collection.md",
            REPO_ROOT
            / "evals"
            / "stt_accuracy"
            / "suites"
            / "codex-command-accuracy-v1"
            / "README.md",
        ]
        forbidden = re.compile(
            r"(Phase\s*\d|phase|leaf|#\d+|GitHub issue|issue graph|remote|handoff)",
            re.IGNORECASE,
        )

        violations: list[str] = []
        for doc in docs:
            text = doc.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if forbidden.search(line):
                    violations.append(f"{doc.relative_to(REPO_ROOT)}:{line_number}: {line}")

        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
