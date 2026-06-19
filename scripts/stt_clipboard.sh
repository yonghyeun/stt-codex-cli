#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: scripts/stt_clipboard.sh [options] audio_file [transcribe options...]

Transcribes an audio file, optionally recovers workspace tokens, and copies the
final text to the clipboard.

Wrapper options must appear before audio_file:
  --no-recovery                 Skip token recovery.
  --memory PATH                 Token recovery memory JSON.
  --min-confidence VALUE        Minimum token recovery confidence. Default: 0.8
  --clipboard-backend BACKEND   Clipboard backend: auto, xclip, or wl-copy.
  --no-copy-verify              Skip clipboard readback verification.
  --output-transcript PATH      Write raw STT transcript to PATH.
  --output-recovered PATH       Write final recovered text to PATH.
  -h, --help                    Show this help.

All arguments after audio_file are passed to scripts/transcribe.sh.

Examples:
  scripts/stt_clipboard.sh audio.wav
  scripts/stt_clipboard.sh audio.wav --model large-v3 --device cuda --compute-type float16
  scripts/stt_clipboard.sh --no-recovery audio.wav --model tiny --device cpu --compute-type int8
USAGE
}

recovery=1
memory_path=""
min_confidence="${STT_TOKEN_MIN_CONFIDENCE:-0.8}"
clipboard_backend="${STT_CLIPBOARD_BACKEND:-auto}"
copy_verify=1
output_transcript=""
output_recovered=""
audio_file=""
transcribe_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --no-recovery)
      recovery=0
      shift
      ;;
    --memory)
      if [[ $# -lt 2 ]]; then
        echo "--memory requires a path" >&2
        exit 2
      fi
      memory_path="$2"
      shift 2
      ;;
    --memory=*)
      memory_path="${1#*=}"
      shift
      ;;
    --min-confidence)
      if [[ $# -lt 2 ]]; then
        echo "--min-confidence requires a value" >&2
        exit 2
      fi
      min_confidence="$2"
      shift 2
      ;;
    --min-confidence=*)
      min_confidence="${1#*=}"
      shift
      ;;
    --clipboard-backend)
      if [[ $# -lt 2 ]]; then
        echo "--clipboard-backend requires a value" >&2
        exit 2
      fi
      clipboard_backend="$2"
      shift 2
      ;;
    --clipboard-backend=*)
      clipboard_backend="${1#*=}"
      shift
      ;;
    --no-copy-verify)
      copy_verify=0
      shift
      ;;
    --output-transcript)
      if [[ $# -lt 2 ]]; then
        echo "--output-transcript requires a path" >&2
        exit 2
      fi
      output_transcript="$2"
      shift 2
      ;;
    --output-transcript=*)
      output_transcript="${1#*=}"
      shift
      ;;
    --output-recovered)
      if [[ $# -lt 2 ]]; then
        echo "--output-recovered requires a path" >&2
        exit 2
      fi
      output_recovered="$2"
      shift 2
      ;;
    --output-recovered=*)
      output_recovered="${1#*=}"
      shift
      ;;
    --)
      shift
      if [[ $# -lt 1 ]]; then
        echo "audio_file is required after --" >&2
        exit 2
      fi
      audio_file="$1"
      shift
      transcribe_args=("$@")
      break
      ;;
    -*)
      echo "unknown wrapper option before audio_file: $1" >&2
      echo "put transcribe options after audio_file" >&2
      exit 2
      ;;
    *)
      audio_file="$1"
      shift
      transcribe_args=("$@")
      break
      ;;
  esac
done

if [[ -z "$audio_file" ]]; then
  echo "audio_file is required" >&2
  exit 2
fi

if [[ ! -f "$audio_file" ]]; then
  echo "audio_file not found: $audio_file" >&2
  exit 2
fi

write_text_file() {
  local path="$1"
  local text="$2"
  mkdir -p "$(dirname "$path")"
  printf '%s\n' "$text" > "$path"
}

echo "step=transcribe audio=$audio_file" >&2
transcript="$("$repo_root/scripts/transcribe.sh" "$audio_file" "${transcribe_args[@]}")"

if [[ -z "$transcript" ]]; then
  echo "transcript is empty" >&2
  exit 1
fi

if [[ -n "$output_transcript" ]]; then
  write_text_file "$output_transcript" "$transcript"
fi

final_text="$transcript"
if [[ "$recovery" -eq 1 ]]; then
  recover_args=("--min-confidence" "$min_confidence")
  if [[ -n "$memory_path" ]]; then
    recover_args+=("--memory" "$memory_path")
  fi
  echo "step=recover_tokens enabled=true" >&2
  final_text="$("$repo_root/scripts/recover_tokens.py" "${recover_args[@]}" "$transcript")"
else
  echo "step=recover_tokens enabled=false" >&2
fi

if [[ -z "$final_text" ]]; then
  echo "final text is empty" >&2
  exit 1
fi

if [[ -n "$output_recovered" ]]; then
  write_text_file "$output_recovered" "$final_text"
fi

copy_args=("--backend" "$clipboard_backend")
if [[ "$copy_verify" -eq 0 ]]; then
  copy_args+=("--no-verify")
fi

echo "step=copy_clipboard backend=$clipboard_backend verify=$([[ "$copy_verify" -eq 1 ]] && echo true || echo false)" >&2
"$repo_root/scripts/copy_text.sh" "${copy_args[@]}" "$final_text"
