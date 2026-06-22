from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import measure_stt_latency_baseline as latency


class SttLatencyBaselineTest(unittest.TestCase):
    def test_parse_reported_elapsed_seconds_from_transcribe_stderr(self) -> None:
        stderr = (
            "loading model: model=large-v3 device=cuda compute_type=float16\n"
            "transcribed: language=ko probability=0.997 duration=3.10s elapsed=1.23s\n"
        )

        self.assertEqual(latency.parse_reported_elapsed_seconds(stderr), 1.23)

    def test_load_latency_cases_validates_only_requested_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "evals" / "inputs" / "speech" / "v1"
            sample_1 = input_root / "samples" / "cmd-0002"
            sample_2 = input_root / "samples" / "cmd-0018"
            suite_path = root / "suite.json"

            sample_1.mkdir(parents=True)
            sample_2.mkdir(parents=True)
            (sample_1 / "audio.wav").write_bytes(b"fake wav")
            (sample_1 / "expected.txt").write_text("변경사항 확인해줘\n", encoding="utf-8")
            (sample_1 / "metadata.json").write_text(
                json.dumps({"sample_id": "cmd-0002"}),
                encoding="utf-8",
            )
            (sample_2 / "expected.txt").write_text("누락 sample\n", encoding="utf-8")
            (sample_2 / "metadata.json").write_text(
                json.dumps({"sample_id": "cmd-0018"}),
                encoding="utf-8",
            )
            (input_root / "manifest.json").write_text(
                json.dumps(
                    {
                        "input_set": "speech/v1",
                        "version": 1,
                        "sample_ids": ["cmd-0002", "cmd-0018"],
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
                            },
                            {
                                "case_id": "code-identifier-002",
                                "sample_id": "cmd-0018",
                                "category": "code_identifier",
                                "metrics": ["phonetic_transcript_match", "insertion_safe"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            cases = latency.load_latency_cases(
                suite_path=suite_path,
                input_root=input_root,
                run_dir=root / "runs" / "latency",
                sample_ids=["cmd-0002"],
            )

            self.assertEqual([case.sample_id for case in cases], ["cmd-0002"])
            self.assertEqual(cases[0].raw_file.as_posix(), f"{root}/runs/latency/raw/cmd-0002.txt")

    def test_build_case_result_separates_latency_and_quality_comparison(self) -> None:
        case = latency.LatencyCase(
            case_id="korean-command-002",
            sample_id="cmd-0002",
            category="korean_command",
            metrics=["phonetic_transcript_match", "insertion_safe"],
            expected="현재 변경사항 확인하고 위험한 파일이 있는지 봐줘",
            audio_file=Path("inputs/cmd-0002/audio.wav"),
            expected_file=Path("inputs/cmd-0002/expected.txt"),
            metadata_file=Path("inputs/cmd-0002/metadata.json"),
            raw_file=Path("runs/latency/raw/cmd-0002.txt"),
            recovered_file=Path("runs/latency/recovered/cmd-0002.txt"),
        )
        transcription = latency.TranscriptionRun(
            transcript="현재 변경사항 확인하고 위험한 파일이 있는지 봐줘",
            stdout="현재 변경사항 확인하고 위험한 파일이 있는지 봐줘\n",
            stderr="transcribed: language=ko probability=0.990 duration=2.00s elapsed=1.50s\n",
            returncode=0,
            subprocess_elapsed_seconds=1.75,
            timing={
                "internal_elapsed_seconds": 1.5,
                "model_load_elapsed_seconds": 1.1,
                "decode_elapsed_seconds": 0.35,
                "audio_duration_seconds": 2.0,
            },
        )

        result = latency.build_case_result(case, transcription)

        self.assertEqual(result["sample_id"], "cmd-0002")
        self.assertEqual(result["latency"]["subprocess_elapsed_seconds"], 1.75)
        self.assertEqual(result["latency"]["transcribe_internal_elapsed_seconds"], 1.5)
        self.assertEqual(result["latency"]["model_load_elapsed_seconds"], 1.1)
        self.assertEqual(result["latency"]["decode_elapsed_seconds"], 0.35)
        self.assertIn("quality_eval_elapsed_seconds", result["latency"])
        self.assertEqual(result["quality"]["case_score"], 1.0)
        self.assertEqual(result["failure_types"], [])


if __name__ == "__main__":
    unittest.main()
