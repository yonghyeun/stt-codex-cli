from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import measure_audio_handoff_latency as handoff
from scripts import measure_stt_latency_baseline as baseline
from stt_runtime.transcription import TranscriptionConfig


def write_minimal_input(root: Path) -> tuple[Path, Path]:
    input_root = root / "evals" / "inputs" / "speech" / "v1"
    sample_dir = input_root / "samples" / "cmd-0002"
    suite_path = root / "suite.json"
    sample_dir.mkdir(parents=True)
    (sample_dir / "audio.wav").write_bytes(b"RIFF fake wav")
    (sample_dir / "expected.txt").write_text("현재 변경사항 확인해줘\n", encoding="utf-8")
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


class AudioHandoffLatencyTest(unittest.TestCase):
    def test_render_dry_run_lists_file_and_buffer_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root, suite_path = write_minimal_input(root)

            plan = handoff.render_dry_run(
                suite_path=suite_path,
                input_root=input_root,
                run_root=root / "runs",
                run_id="dry-run",
                sample_ids=["cmd-0002"],
                config=TranscriptionConfig(
                    model="large-v3",
                    language="ko",
                    device="cuda",
                    compute_type="float16",
                    beam_size=5,
                    initial_prompt=None,
                    vad_filter=True,
                ),
            )

            self.assertEqual(plan["handoff_modes"], ["file", "buffer"])
            self.assertEqual(
                plan["prior_29"]["subprocess_average_seconds"],
                handoff.DEFAULT_PRIOR_SUBPROCESS_AVERAGE_SECONDS,
            )
            self.assertEqual(plan["cases"][0]["sample_id"], "cmd-0002")

    def test_build_case_result_reports_prior_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            case = baseline.LatencyCase(
                case_id="korean-command-002",
                sample_id="cmd-0002",
                category="korean_command",
                metrics=["phonetic_transcript_match", "insertion_safe"],
                expected="현재 변경사항 확인해줘",
                audio_file=Path("audio.wav"),
                expected_file=Path("expected.txt"),
                metadata_file=Path("metadata.json"),
                raw_file=root / "raw" / "cmd-0002.txt",
                recovered_file=root / "recovered" / "cmd-0002.txt",
            )

            result = handoff.build_case_result(
                case=case,
                mode="buffer",
                run=handoff.HandoffRun(
                    transcript="현재 변경사항 확인해줘",
                    elapsed_seconds=1.25,
                ),
                run_dir=root,
            )

            self.assertEqual(result["handoff"], "buffer")
            self.assertEqual(result["latency"]["worker_request_elapsed_seconds"], 1.25)
            self.assertEqual(result["prior_29"]["case_score"], 1.0)
            self.assertEqual(result["prior_29"]["case_score_delta"], 0.0)
            self.assertTrue((root / "buffer" / "raw" / "cmd-0002.txt").exists())


if __name__ == "__main__":
    unittest.main()
