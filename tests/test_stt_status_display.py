from __future__ import annotations

import unittest
from io import StringIO

from stt_core.status import (
    ParentStatusMessage,
    compact_parent_status,
    summarize_stt_error,
)
from stt_runtime.terminal import TerminalStatusRenderer, adjusted_child_size


class ParentStatusMessageTest(unittest.TestCase):
    def test_compacts_recording_lifecycle_for_user_status_bar(self) -> None:
        self.assertEqual(
            compact_parent_status("recording started: in-memory audio buffer"),
            ParentStatusMessage("STT recording 중 | Ctrl+T stop | Esc cancel"),
        )
        self.assertEqual(
            compact_parent_status("recording progress: elapsed=5.20s max=60s"),
            ParentStatusMessage(
                "STT recording 중 00:05 / 01:00 | Ctrl+T stop | Esc cancel"
            ),
        )
        self.assertEqual(
            compact_parent_status("recording canceled: elapsed=0.42s"),
            ParentStatusMessage("STT canceled | Ctrl+T retry"),
        )
        self.assertEqual(
            compact_parent_status("recording stopped: elapsed=0.58s"),
            ParentStatusMessage("STT transcribing | 0.58s audio"),
        )
        self.assertEqual(
            compact_parent_status("transcribing..."),
            ParentStatusMessage("STT transcribing | wait"),
        )
        self.assertEqual(
            compact_parent_status("starting stt daemon..."),
            ParentStatusMessage("STT daemon starting | wait"),
        )

    def test_compacts_daemon_queue_status_for_user_status_bar(self) -> None:
        self.assertEqual(
            compact_parent_status("daemon queue: queued 2/4"),
            ParentStatusMessage("STT queued 2/4 | wait"),
        )
        self.assertEqual(
            compact_parent_status("daemon queue: queued 1/3"),
            ParentStatusMessage("STT queued 1/3 | next"),
        )
        self.assertEqual(
            compact_parent_status("daemon queue: running"),
            ParentStatusMessage("STT running | wait"),
        )
        self.assertEqual(
            compact_parent_status("daemon queue: unknown"),
            ParentStatusMessage("STT transcribing | queue unknown"),
        )

    def test_compacts_injection_empty_and_short_recording_outcomes(self) -> None:
        self.assertEqual(
            compact_parent_status(
                "injected transcript 11 chars; review text, then press Enter to send"
            ),
            ParentStatusMessage("STT inserted 11 chars | Enter to send"),
        )
        self.assertEqual(
            compact_parent_status("submitted transcript 11 chars"),
            ParentStatusMessage("STT submitted 11 chars"),
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


class TerminalStatusRendererTest(unittest.TestCase):
    def test_adjusted_child_size_reserves_status_bar_row(self) -> None:
        self.assertEqual(adjusted_child_size(24, 80, reserved_rows=1), (23, 80))
        self.assertEqual(adjusted_child_size(1, 80, reserved_rows=1), (1, 80))

    def test_interactive_renderer_reserves_parent_panel_and_status_rows(self) -> None:
        renderer = TerminalStatusRenderer(
            stream=StringIO(),
            enabled=True,
            color=False,
            debug=False,
            interactive=True,
            terminal_size=lambda: (24, 40),
            parent_panel=("parent", "panel"),
        )

        self.assertEqual(renderer.reserved_rows, 3)
        self.assertEqual(adjusted_child_size(24, 80, reserved_rows=3), (21, 80))

    def test_interactive_renderer_draws_parent_panel_at_top(self) -> None:
        stream = StringIO()
        renderer = TerminalStatusRenderer(
            stream=stream,
            enabled=True,
            color=False,
            debug=False,
            interactive=True,
            terminal_size=lambda: (24, 40),
            parent_panel=("parent", "panel"),
        )

        renderer.render_parent_panel()

        self.assertEqual(
            stream.getvalue(),
            "\033[1;1H\033[2Kparent\033[2;1H\033[2Kpanel\033[3;1H",
        )

    def test_interactive_renderer_clips_parent_panel_to_leave_child_and_status_rows(
        self,
    ) -> None:
        stream = StringIO()
        renderer = TerminalStatusRenderer(
            stream=stream,
            enabled=True,
            color=False,
            debug=False,
            interactive=True,
            terminal_size=lambda: (3, 40),
            parent_panel=("parent", "panel", "extra"),
        )

        renderer.render_parent_panel()

        self.assertEqual(
            stream.getvalue(),
            "\033[1;1H\033[2Kparent\033[2;1H",
        )

    def test_debug_renderer_does_not_reserve_parent_panel_rows(self) -> None:
        renderer = TerminalStatusRenderer(
            stream=StringIO(),
            enabled=True,
            color=False,
            debug=True,
            interactive=True,
            terminal_size=lambda: (24, 40),
            parent_panel=("parent", "panel"),
        )

        self.assertEqual(renderer.reserved_rows, 0)

    def test_interactive_renderer_updates_bottom_line_without_newline(self) -> None:
        stream = StringIO()
        renderer = TerminalStatusRenderer(
            stream=stream,
            enabled=True,
            color=False,
            debug=False,
            interactive=True,
            terminal_size=lambda: (24, 40),
        )

        renderer("recording started: in-memory audio buffer")

        self.assertEqual(
            stream.getvalue(),
            "\033[s\033[24;1H\033[2KSTT recording 중 | Ctrl+T stop | Esc c...\033[u",
        )

    def test_interactive_renderer_clamps_zero_sized_terminal_rows(self) -> None:
        stream = StringIO()
        renderer = TerminalStatusRenderer(
            stream=stream,
            enabled=True,
            color=False,
            debug=False,
            interactive=True,
            terminal_size=lambda: (0, 0),
        )

        renderer("recording started: in-memory audio buffer")

        self.assertEqual(
            stream.getvalue(),
            "\033[s\033[1;1H\033[2KSTT recording 중 | Ctrl+T stop | Esc cancel\033[u",
        )

    def test_default_renderer_hides_verbose_status_noise(self) -> None:
        stream = StringIO()
        renderer = TerminalStatusRenderer(
            stream=stream,
            enabled=True,
            color=False,
            debug=False,
            interactive=False,
            terminal_size=lambda: (24, 80),
        )

        renderer("released in-memory audio buffer")
        renderer("stt: language=ko probability=1.000")

        self.assertEqual(stream.getvalue(), "")

    def test_debug_renderer_emits_raw_parent_lines(self) -> None:
        stream = StringIO()
        renderer = TerminalStatusRenderer(
            stream=stream,
            enabled=True,
            color=False,
            debug=True,
            interactive=False,
            terminal_size=lambda: (24, 80),
        )

        renderer("stt: language=ko probability=1.000")

        self.assertEqual(
            stream.getvalue(),
            "[stt-parent] stt: language=ko probability=1.000\n",
        )


if __name__ == "__main__":
    unittest.main()
