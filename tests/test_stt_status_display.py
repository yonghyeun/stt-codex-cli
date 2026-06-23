from __future__ import annotations

import unittest

from stt_core.status import (
    ParentStatusMessage,
    compact_parent_status,
    summarize_stt_error,
)


class ParentStatusMessageTest(unittest.TestCase):
    def test_compacts_recording_lifecycle_for_user_status_bar(self) -> None:
        self.assertEqual(
            compact_parent_status("recording started: in-memory audio buffer"),
            ParentStatusMessage("STT recording | Ctrl+T stop"),
        )
        self.assertEqual(
            compact_parent_status("recording stopped: elapsed=0.58s"),
            ParentStatusMessage("STT transcribing | 0.58s audio"),
        )
        self.assertEqual(
            compact_parent_status("transcribing..."),
            ParentStatusMessage("STT transcribing | wait"),
        )

    def test_compacts_injection_empty_and_short_recording_outcomes(self) -> None:
        self.assertEqual(
            compact_parent_status(
                "injected transcript 11 chars; review text, then press Enter to send"
            ),
            ParentStatusMessage("STT inserted 11 chars | Enter to send"),
        )
        self.assertEqual(
            compact_parent_status("empty transcript; nothing injected"),
            ParentStatusMessage("STT empty: 인식된 말 없음 | Ctrl+T retry"),
        )
        self.assertEqual(
            compact_parent_status("recording too short: 0.08s < 0.15s; skipped STT"),
            ParentStatusMessage("STT skipped: 녹음이 너무 짧음 | Ctrl+T retry"),
        )

    def test_hides_verbose_lifecycle_noise_in_default_mode(self) -> None:
        self.assertIsNone(compact_parent_status("released in-memory audio buffer"))
        self.assertIsNone(compact_parent_status("deleted temporary audio"))
        self.assertIsNone(compact_parent_status("stt: language=ko probability=1.000"))

    def test_summarizes_worker_failures_for_user_action(self) -> None:
        self.assertEqual(
            summarize_stt_error(
                "STT worker failed: CUDA failed with error out of memory"
            ),
            "GPU memory 부족",
        )
        self.assertEqual(
            compact_parent_status(
                "stt error: STT worker failed: CUDA failed with error out of memory"
            ),
            ParentStatusMessage("STT failed: GPU memory 부족 | Ctrl+T retry"),
        )


if __name__ == "__main__":
    unittest.main()
