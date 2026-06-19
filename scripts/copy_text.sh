#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/copy_text.sh [--backend auto|xclip|wl-copy] [--no-verify] [text ...]

Copies text to the system clipboard.

If text is omitted, stdin is used.

Environment:
  STT_CLIPBOARD_BACKEND  Clipboard backend. Default: auto
USAGE
}

backend="${STT_CLIPBOARD_BACKEND:-auto}"
verify=1
text_parts=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --backend)
      if [[ $# -lt 2 ]]; then
        echo "--backend requires a value: auto, xclip, or wl-copy" >&2
        exit 2
      fi
      backend="$2"
      shift 2
      ;;
    --backend=*)
      backend="${1#*=}"
      shift
      ;;
    --no-verify)
      verify=0
      shift
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        text_parts+=("$1")
        shift
      done
      ;;
    -*)
      echo "unknown option: $1" >&2
      exit 2
      ;;
    *)
      text_parts+=("$1")
      shift
      ;;
  esac
done

case "$backend" in
  auto|xclip|wl-copy)
    ;;
  *)
    echo "invalid backend: $backend" >&2
    echo "expected one of: auto, xclip, wl-copy" >&2
    exit 2
    ;;
esac

if [[ "${#text_parts[@]}" -gt 0 ]]; then
  text="${text_parts[*]}"
else
  if [[ -t 0 ]]; then
    echo "text is required when stdin is empty" >&2
    exit 2
  fi
  text="$(cat)"
fi

if [[ -z "$text" ]]; then
  echo "text must not be empty" >&2
  exit 2
fi

resolve_backend() {
  if [[ "$backend" != "auto" ]]; then
    echo "$backend"
    return
  fi

  if [[ -n "${WAYLAND_DISPLAY:-}" ]] && command -v wl-copy >/dev/null 2>&1 && command -v wl-paste >/dev/null 2>&1; then
    echo "wl-copy"
    return
  fi

  if command -v xclip >/dev/null 2>&1; then
    echo "xclip"
    return
  fi

  if command -v wl-copy >/dev/null 2>&1 && command -v wl-paste >/dev/null 2>&1; then
    echo "wl-copy"
    return
  fi

  echo "no supported clipboard backend found. Install xclip or wl-clipboard." >&2
  exit 1
}

copy_with_backend() {
  case "$resolved_backend" in
    xclip)
      if ! command -v xclip >/dev/null 2>&1; then
        echo "xclip is required but was not found." >&2
        exit 1
      fi
      if ! printf '%s' "$text" | xclip -selection clipboard -in >/dev/null 2>&1; then
        echo "xclip failed to copy text to clipboard." >&2
        exit 1
      fi
      ;;
    wl-copy)
      if ! command -v wl-copy >/dev/null 2>&1; then
        echo "wl-copy is required but was not found." >&2
        exit 1
      fi
      printf '%s' "$text" | wl-copy
      ;;
    *)
      echo "unsupported resolved backend: $resolved_backend" >&2
      exit 1
      ;;
  esac
}

read_with_backend() {
  case "$resolved_backend" in
    xclip)
      xclip -selection clipboard -out
      ;;
    wl-copy)
      if ! command -v wl-paste >/dev/null 2>&1; then
        echo "wl-paste is required for verification but was not found." >&2
        exit 1
      fi
      wl-paste --no-newline
      ;;
    *)
      echo "unsupported resolved backend: $resolved_backend" >&2
      exit 1
      ;;
  esac
}

resolved_backend="$(resolve_backend)"
copy_with_backend

if [[ "$verify" -eq 1 ]]; then
  copied_text="$(read_with_backend)"
  if [[ "$copied_text" != "$text" ]]; then
    echo "clipboard verification failed" >&2
    exit 1
  fi
fi

printf '%s\n' "$text"
echo "copied: backend=$resolved_backend verified=$([[ "$verify" -eq 1 ]] && echo true || echo false) chars=${#text}" >&2
