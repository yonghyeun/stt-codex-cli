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

    def test_phonetic_transcript_match_uses_normalized_text(self) -> None:
        result = run_stt_accuracy_suite.evaluate_case(
            case_id="code-switch-001",
            sample_id="cmd-0001",
            category="code_switch",
            metrics=["phonetic_transcript_match", "insertion_safe"],
            expected="브이원 기준 확인해줘",
            actual="비원 기준 확인해줘",
            raw_file="raw/cmd-0001.txt",
            recovered_file="recovered/cmd-0001.txt",
        )

        self.assertFalse(result["metrics"]["phonetic_transcript_match"]["passed"])
        self.assertIn("phonetic_transcript_mismatch", result["failure_types"])
        self.assertTrue(result["metrics"]["insertion_safe"]["passed"])

    def test_case_result_includes_text_comparison_and_quantitative_quality(self) -> None:
        result = run_stt_accuracy_suite.evaluate_case(
            case_id="code-switch-001",
            sample_id="cmd-0001",
            category="code_switch",
            metrics=["latin_token_preservation", "insertion_safe"],
            expected="abc def",
            actual="abc xyz",
            raw_file="raw/cmd-0001.txt",
            recovered_file="recovered/cmd-0001.txt",
        )

        self.assertEqual(result["text_comparison"]["expected_text"], "abc def")
        self.assertEqual(result["text_comparison"]["raw_text"], "abc xyz")
        self.assertEqual(result["text_comparison"]["recovered_text"], "abc xyz")
        self.assertEqual(result["text_comparison"]["normalized_expected"], "abcdef")
        self.assertEqual(result["text_comparison"]["normalized_raw"], "abcxyz")

        quality = result["quality"]
        self.assertEqual(quality["edit_distance"], 3)
        self.assertAlmostEqual(quality["char_error_rate"], 0.4286)
        self.assertEqual(quality["normalized_edit_distance"], 3)
        self.assertAlmostEqual(quality["normalized_char_error_rate"], 0.5)
        self.assertAlmostEqual(quality["text_similarity"], 0.5)
        self.assertAlmostEqual(quality["word_error_rate"], 0.5)
        self.assertAlmostEqual(quality["critical_token_precision"], 0.5)
        self.assertAlmostEqual(quality["critical_token_recall"], 0.5)
        self.assertAlmostEqual(quality["critical_token_f1"], 0.5)
        self.assertAlmostEqual(quality["case_score"], 0.55)
        self.assertEqual(quality["critical_tokens"]["expected"], ["abc", "def"])
        self.assertEqual(quality["critical_tokens"]["preserved"], ["abc"])
        self.assertEqual(quality["critical_tokens"]["missing"], ["def"])
        self.assertEqual(quality["critical_tokens"]["unexpected"], ["xyz"])

    def test_result_json_includes_quality_summary(self) -> None:
        plan = run_stt_accuracy_suite.RunPlan(
            suite_id="codex-command-accuracy-v1",
            input_set="speech/v1",
            run_id="summary-test",
            run_root=Path("runs"),
            run_dir=Path("runs") / "summary-test",
            config=run_stt_accuracy_suite.RunConfig(
                model="large-v3",
                device="cuda",
                compute_type="float16",
                language="ko",
                beam_size=5,
                initial_prompt=None,
                token_recovery="none",
            ),
            cases=[],
        )
        case_results = [
            run_stt_accuracy_suite.evaluate_case(
                case_id="code-switch-001",
                sample_id="cmd-0001",
                category="code_switch",
                metrics=["latin_token_preservation", "insertion_safe"],
                expected="abc def",
                actual="abc xyz",
                raw_file="raw/cmd-0001.txt",
                recovered_file="recovered/cmd-0001.txt",
            ),
            run_stt_accuracy_suite.evaluate_case(
                case_id="code-switch-002",
                sample_id="cmd-0002",
                category="code_switch",
                metrics=["latin_token_preservation", "insertion_safe"],
                expected="hello",
                actual="hello",
                raw_file="raw/cmd-0002.txt",
                recovered_file="recovered/cmd-0002.txt",
            ),
        ]

        result_json = run_stt_accuracy_suite.build_result_json(
            plan,
            case_results,
            elapsed_seconds=1.234,
        )

        self.assertEqual(result_json["quality_summary"]["average_case_score"], 0.775)
        self.assertEqual(result_json["quality_summary"]["average_text_similarity"], 0.75)
        self.assertEqual(
            result_json["quality_summary"]["average_normalized_char_error_rate"],
            0.25,
        )
        self.assertEqual(result_json["quality_summary"]["average_critical_token_f1"], 0.75)

    def test_active_suite_uses_phonetic_transcript_metric_for_v1(self) -> None:
        manifest_path = (
            REPO_ROOT
            / "evals"
            / "stt_accuracy"
            / "suites"
            / "codex-command-accuracy-v1"
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        preservation_metrics = {
            "latin_token_preservation",
            "file_path_preservation",
            "cli_option_preservation",
            "code_identifier_preservation",
        }
        for case in manifest["cases"]:
            metrics = set(case["metrics"])
            self.assertIn("phonetic_transcript_match", metrics)
            self.assertIn("insertion_safe", metrics)
            self.assertTrue(metrics.isdisjoint(preservation_metrics), case["case_id"])

    def test_speech_v1_samples_use_korean_phonetic_expected_policy(self) -> None:
        samples_root = REPO_ROOT / "evals" / "inputs" / "speech" / "v1" / "samples"
        latin_pattern = re.compile(r"[A-Za-z]")

        for metadata_path in sorted(samples_root.glob("cmd-*/metadata.json")):
            sample_dir = metadata_path.parent
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            expected_text = (sample_dir / "expected.txt").read_text(encoding="utf-8")

            self.assertEqual(
                metadata["expected_text_policy"],
                "korean_phonetic_transcript",
                metadata["sample_id"],
            )
            self.assertNotRegex(expected_text, latin_pattern, metadata["sample_id"])

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
