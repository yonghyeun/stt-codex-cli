from __future__ import annotations


class KeySequenceError(ValueError):
    """Raised when an inject key sequence cannot be parsed."""


def parse_key_sequence(value: str) -> bytes:
    normalized = value.strip().lower()
    if not normalized:
        raise KeySequenceError("--inject-key must not be empty")

    named_keys = {
        "tab": b"\t",
        "esc": b"\x1b",
        "escape": b"\x1b",
        "space": b" ",
        "enter": b"\r",
    }
    if normalized in named_keys:
        return named_keys[normalized]

    if normalized.startswith("ctrl+"):
        key = normalized.removeprefix("ctrl+")
        if len(key) != 1 or not ("a" <= key <= "z"):
            raise KeySequenceError(
                "ctrl key syntax must be ctrl+<a-z>, for example ctrl+t"
            )
        return bytes([ord(key) - ord("a") + 1])

    if len(value) == 1:
        return value.encode()

    raise KeySequenceError(
        "inject key must be a single character, named key, or ctrl+<a-z>"
    )
