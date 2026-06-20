from __future__ import annotations


def transcript_has_text(transcript: str) -> bool:
    return any(character.isalnum() for character in transcript)
