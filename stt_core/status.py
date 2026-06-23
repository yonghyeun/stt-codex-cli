from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParentStatusMessage:
    text: str


def compact_parent_status(message: str) -> ParentStatusMessage | None:
    normalized = " ".join(message.strip().split())
    if not normalized:
        return None

    if normalized.startswith("recording started:"):
        return ParentStatusMessage("STT recording 중 | Ctrl+T stop")

    stopped_match = re.match(r"recording stopped: elapsed=([0-9.]+)s", normalized)
    if stopped_match:
        return ParentStatusMessage(f"STT transcribing | {stopped_match.group(1)}s audio")

    if normalized == "transcribing...":
        return ParentStatusMessage("STT transcribing | wait")

    if normalized == "starting stt worker...":
        return ParentStatusMessage("STT loading model | wait")

    if normalized == "starting stt daemon...":
        return ParentStatusMessage("STT daemon starting | wait")

    queued_match = re.match(r"daemon queue: queued ([0-9]+)/([0-9]+)", normalized)
    if queued_match:
        suffix = "next" if queued_match.group(1) == "1" else "wait"
        return ParentStatusMessage(
            f"STT queued {queued_match.group(1)}/{queued_match.group(2)} | {suffix}"
        )

    if normalized == "daemon queue: running":
        return ParentStatusMessage("STT running | wait")

    if normalized == "daemon queue: unknown":
        return ParentStatusMessage("STT transcribing | queue unknown")

    injected_match = re.match(r"injected transcript ([0-9]+) chars;", normalized)
    if injected_match:
        return ParentStatusMessage(
            f"STT inserted {injected_match.group(1)} chars | Enter to send"
        )

    fixed_injected_match = re.match(r"injected ([0-9]+) chars;", normalized)
    if fixed_injected_match:
        return ParentStatusMessage(
            f"STT inserted {fixed_injected_match.group(1)} chars | Enter to send"
        )

    if normalized == "empty transcript; nothing injected":
        return ParentStatusMessage("STT empty: 인식된 말 없음 | Ctrl+T retry")

    if normalized.startswith("recording too short:"):
        return ParentStatusMessage("STT skipped: 녹음이 너무 짧음 | Ctrl+T retry")

    if normalized.startswith("max duration reached:"):
        return ParentStatusMessage("STT stopping: 최대 녹음 시간 도달")

    if normalized.startswith("stt error:"):
        return ParentStatusMessage(
            f"STT failed: {summarize_stt_error(normalized.removeprefix('stt error:').strip())} | Ctrl+T retry"
        )

    return None


def summarize_stt_error(error: str) -> str:
    normalized = " ".join(error.strip().split())
    lower = normalized.lower()
    if "out of memory" in lower or "cuda" in lower and "memory" in lower:
        return "GPU memory 부족"
    if "worker stopped without response" in lower:
        return "worker 응답 없음"
    if "worker closed before accepting request" in lower:
        return "worker 연결 종료"
    if "worker exited before request" in lower:
        return "worker 조기 종료"
    if "audio bytes" in lower or "audio input" in lower:
        return "audio 입력 없음"
    if "exit code" in lower:
        return normalized
    return normalized or "unknown error"
