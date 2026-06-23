from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import stt_codex
from stt_core.transcription_prompt import DEFAULT_KOREAN_PHONETIC_INITIAL_PROMPT


def make_args(**overrides: object) -> argparse.Namespace:
    values = {
        "cmd": "codex",
        "cmd_args": [],
        "codex_alt_screen": False,
        "quiet_parent": True,
        "no_color": True,
        "run_output_dir": "output/runs",
        "save_run": False,
        "keep_audio": False,
        "stt_model": "large-v3",
        "stt_language": "ko",
        "stt_device": "auto",
        "stt_compute_type": "auto",
        "stt_beam_size": 5,
        "stt_no_vad_filter": False,
        "stt_initial_prompt": stt_codex.DEFAULT_STT_INITIAL_PROMPT,
        "cwd": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class KeySequenceTest(unittest.TestCase):
    def test_named_and_ctrl_keys_parse_to_bytes(self) -> None:
        self.assertEqual(stt_codex.parse_key_sequence("ctrl+t"), b"\x14")
        self.assertEqual(stt_codex.parse_key_sequence("tab"), b"\t")
        self.assertEqual(stt_codex.parse_key_sequence("enter"), b"\r")
        self.assertEqual(stt_codex.parse_key_sequence("x"), b"x")

    def test_invalid_key_sequence_raises_argparse_error(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            stt_codex.parse_key_sequence("")
        with self.assertRaises(argparse.ArgumentTypeError):
            stt_codex.parse_key_sequence("ctrl+1")
        with self.assertRaises(argparse.ArgumentTypeError):
            stt_codex.parse_key_sequence("spacebar")


class ChildCommandTest(unittest.TestCase):
    def test_codex_child_gets_no_alt_screen_by_default(self) -> None:
        args = make_args(cmd="codex", cmd_args=[])

        self.assertEqual(stt_codex.child_argv(args), ["codex", "--no-alt-screen"])

    def test_codex_child_does_not_duplicate_no_alt_screen(self) -> None:
        args = make_args(cmd="codex", cmd_args=["--no-alt-screen", "--model", "gpt-5"])

        self.assertEqual(
            stt_codex.child_argv(args),
            ["codex", "--no-alt-screen", "--model", "gpt-5"],
        )

    def test_non_codex_child_is_not_modified(self) -> None:
        args = make_args(cmd="python3", cmd_args=["-q"])

        self.assertEqual(stt_codex.child_argv(args), ["python3", "-q"])


class TranscriptPolicyTest(unittest.TestCase):
    def test_transcript_has_text_requires_alphanumeric_content(self) -> None:
        self.assertFalse(stt_codex.transcript_has_text(""))
        self.assertFalse(stt_codex.transcript_has_text("   "))
        self.assertFalse(stt_codex.transcript_has_text(".,!?"))
        self.assertTrue(stt_codex.transcript_has_text("안녕하세요"))
        self.assertTrue(stt_codex.transcript_has_text("bug 123"))


class InitialPromptDefaultTest(unittest.TestCase):
    def test_stt_codex_default_prompt_uses_korean_phonetic_policy(self) -> None:
        self.assertEqual(
            stt_codex.DEFAULT_STT_INITIAL_PROMPT,
            DEFAULT_KOREAN_PHONETIC_INITIAL_PROMPT,
        )


class PttReleaseGapContractTest(unittest.TestCase):
    def parse_with(
        self,
        argv: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> argparse.Namespace:
        with (
            patch.object(sys, "argv", ["stt_codex.py", *(argv or [])]),
            patch.dict(os.environ, env or {}, clear=True),
        ):
            return stt_codex.parse_args()

    def test_default_release_gap_uses_single_fast_stop_value(self) -> None:
        args = self.parse_with()

        self.assertFalse(hasattr(args, "ptt_profile"))
        self.assertEqual(args.release_gap, stt_codex.DEFAULT_RELEASE_GAP)
        self.assertEqual(args.release_gap, 0.35)

    def test_ptt_profile_env_is_not_a_configuration_surface(self) -> None:
        args = self.parse_with(env={"STT_PTT_PROFILE": "accuracy"})

        self.assertEqual(args.release_gap, 0.35)

    def test_ptt_profile_cli_option_is_removed(self) -> None:
        with self.assertRaises(SystemExit):
            self.parse_with(["--ptt-profile", "speed"])

    def test_release_gap_env_overrides_default(self) -> None:
        args = self.parse_with(env={"STT_PTT_RELEASE_GAP": "0.9"})

        self.assertEqual(args.release_gap, 0.9)

    def test_explicit_release_gap_overrides_env(self) -> None:
        args = self.parse_with(
            argv=["--release-gap", "0.2"],
            env={"STT_PTT_RELEASE_GAP": "0.9"},
        )

        self.assertEqual(args.release_gap, 0.2)


class RuntimeDefaultContractTest(unittest.TestCase):
    def parse_with(
        self,
        argv: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> argparse.Namespace:
        with (
            patch.object(sys, "argv", ["stt_codex.py", *(argv or [])]),
            patch.dict(os.environ, env or {}, clear=True),
        ):
            return stt_codex.parse_args()

    def test_default_runtime_uses_worker_and_buffer_handoff(self) -> None:
        args = self.parse_with()

        self.assertEqual(args.stt_backend, "worker")
        self.assertEqual(args.audio_handoff, "auto")
        self.assertEqual(stt_codex.resolve_audio_handoff(args), "buffer")

    def test_save_or_debug_audio_preserves_file_handoff(self) -> None:
        self.assertEqual(
            stt_codex.resolve_audio_handoff(self.parse_with(["--save-run"])),
            "file",
        )
        self.assertEqual(
            stt_codex.resolve_audio_handoff(self.parse_with(["--keep-audio"])),
            "file",
        )

    def test_subprocess_override_uses_file_handoff(self) -> None:
        args = self.parse_with(["--stt-backend", "subprocess"])

        self.assertEqual(args.stt_backend, "subprocess")
        self.assertEqual(stt_codex.resolve_audio_handoff(args), "file")


class RunArtifactTest(unittest.TestCase):
    def test_save_run_disabled_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_file = Path(temp_dir) / "audio.wav"
            output_dir = Path(temp_dir) / "runs"
            audio_file.write_bytes(b"fake wav")
            args = make_args(save_run=False, run_output_dir=str(output_dir))

            result = stt_codex.save_run_artifacts(
                args,
                audio_file,
                "안녕하세요",
                started_at=datetime(2026, 6, 20, 1, 2, 3, 456000, tzinfo=timezone.utc),
                elapsed=1.234,
                injected=True,
                outcome="injected",
            )

            self.assertIsNone(result)
            self.assertFalse(output_dir.exists())
            self.assertTrue(audio_file.exists())

    def test_save_run_writes_audio_transcript_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_file = Path(temp_dir) / "audio.wav"
            output_dir = Path(temp_dir) / "runs"
            audio_file.write_bytes(b"fake wav")
            args = make_args(save_run=True, run_output_dir=str(output_dir))

            run_dir = stt_codex.save_run_artifacts(
                args,
                audio_file,
                "안녕하세요",
                started_at=datetime(2026, 6, 20, 1, 2, 3, 456000, tzinfo=timezone.utc),
                elapsed=1.234,
                injected=True,
                outcome="injected",
            )

            self.assertIsNotNone(run_dir)
            assert run_dir is not None
            self.assertEqual(run_dir.name, "20260620-010203-456-stt-codex")
            self.assertFalse(audio_file.exists())
            self.assertEqual((run_dir / "audio.wav").read_bytes(), b"fake wav")
            self.assertEqual((run_dir / "transcript.txt").read_text(encoding="utf-8"), "안녕하세요\n")

            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["outcome"], "injected")
            self.assertTrue(metadata["injected"])
            self.assertEqual(metadata["transcript_chars"], 5)
            self.assertTrue(metadata["transcript_has_text"])
            self.assertEqual(metadata["audio_file"], "audio.wav")
            self.assertEqual(metadata["transcript_file"], "transcript.txt")
            self.assertEqual(
                metadata["stt"]["initial_prompt"],
                stt_codex.DEFAULT_STT_INITIAL_PROMPT,
            )
            self.assertEqual(metadata["child"]["command"], ["codex", "--no-alt-screen"])


if __name__ == "__main__":
    unittest.main()
