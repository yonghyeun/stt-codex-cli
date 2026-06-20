from __future__ import annotations

from pathlib import Path


def is_codex_command(command: str) -> bool:
    return Path(command).name == "codex"


def should_add_codex_no_alt_screen(
    command: str,
    command_args: list[str],
    *,
    codex_alt_screen: bool,
) -> bool:
    return (
        is_codex_command(command)
        and not codex_alt_screen
        and "--no-alt-screen" not in command_args
    )


def child_argv(
    command: str,
    command_args: list[str],
    *,
    codex_alt_screen: bool,
) -> list[str]:
    argv_args = list(command_args)
    if should_add_codex_no_alt_screen(
        command,
        argv_args,
        codex_alt_screen=codex_alt_screen,
    ):
        argv_args.insert(0, "--no-alt-screen")
    return [command, *argv_args]


def format_command(argv: list[str]) -> str:
    return " ".join(argv)
