# Issue 6 Migration Audit

Temporary working audit for #6.

## Goal

- Move `scripts/stt_codex.py` responsibilities into mini-layer modules.
- Keep the current CLI options and user-facing behavior unchanged.
- Keep `scripts/stt_codex.py` as a thin entrypoint and orchestration surface.

## Current Source Map

- `scripts/stt_codex.py`
  - CLI option parsing.
  - key sequence parsing.
  - Codex command argument construction.
  - parent status printing.
  - cwd validation.
  - terminal raw mode.
  - child PTY spawn and passthrough loop.
  - SIGWINCH window-size sync.
  - `arecord` process lifecycle.
  - temporary audio file lifecycle.
  - `scripts/transcribe.sh` subprocess call.
  - transcript text detection.
  - transcript injection into child PTY.
  - optional run artifact persistence.

## Target Module Map

- `stt_core/`
  - pure transcript judgment such as empty or punctuation-only detection.
  - pure run metadata shape building.
  - pure key or command policy only if it has no runtime dependency.
- `stt_runtime/`
  - terminal raw mode and window-size sync.
  - child PTY spawn, wait status decoding, and child reaping.
  - temporary audio file creation and cleanup.
  - `arecord` recording adapter.
  - `scripts/transcribe.sh` subprocess adapter.
  - run artifact file writes.
- `stt_features/`
  - fixed-text injection flow.
  - push-to-talk STT flow.
  - recording stop -> transcribe -> inject -> optional save sequence.
  - interrupted recording cleanup flow.
- `scripts/stt_codex.py`
  - CLI parser and default option compatibility.
  - dependency construction.
  - top-level `main()`.

## Behavior Invariants

- Default STT trigger remains `Ctrl+T`.
- Codex child command still gets `--no-alt-screen` by default.
- Child output is not transformed.
- Parent status uses `[stt-parent]`.
- Empty or punctuation-only transcript is not injected.
- Enter is never sent automatically.
- Default run deletes temporary audio.
- `--save-run` is required before audio, transcript, and metadata are stored under `output/runs/`.
- `--keep-audio` keeps temporary audio for debugging.

## Verification Plan

- Characterization tests before behavior-moving refactor.
- `python3 -m unittest`.
- `python3 -m py_compile scripts/stt_codex.py stt_core/*.py stt_runtime/*.py stt_features/*.py`.
- `scripts/stt_codex.py --help`.
- If runtime dependencies are available, run fixture or wrapper smoke verification and record the result.

## Refactor Notes

- Avoid changing CLI parser option names, defaults, choices, or help text unless a test catches an intentional compatibility update.
- Avoid moving `argparse.Namespace` deep into core modules; prefer small config dataclasses where needed.
- Keep low-level OS calls out of `stt_features`.
- Keep `stt_runtime` free of `scripts` imports.
- Use `REPO_ROOT` or explicit paths from the script layer when a runtime adapter needs repo-local command paths.
