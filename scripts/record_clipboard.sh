#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: scripts/record_clipboard.sh [options] [duration_seconds] [-- transcribe options...]

Records microphone input, transcribes it, optionally recovers workspace tokens,
and copies the final text to the clipboard.

Options:
  --duration SECONDS           Recording duration. Default: 5
  --record-only                Record and print the WAV path, then stop.
  --no-recovery                Skip token recovery.
  --memory PATH                Token recovery memory JSON.
  --min-confidence VALUE       Minimum token recovery confidence. Default: 0.8
  --clipboard-backend BACKEND  Clipboard backend: auto, xclip, or wl-copy.
  --no-copy-verify             Skip clipboard readback verification.
  --output-transcript PATH     Write raw STT transcript to PATH.
  --output-recovered PATH      Write final recovered text to PATH.
  -h, --help                   Show this help.

All arguments after -- are passed to scripts/transcribe.sh.

Examples:
  scripts/record_clipboard.sh
  scripts/record_clipboard.sh --duration 5 -- --model large-v3 --device cuda --compute-type float16
  scripts/record_clipboard.sh 3 -- --model tiny --device cpu --compute-type int8
  scripts/record_clipboard.sh --record-only --duration 1
USAGE
}

duration="${STT_RECORD_DURATION:-5}"
duration_set=0
record_only=0
recovery=1
memory_path=""
min_confidence="${STT_TOKEN_MIN_CONFIDENCE:-0.8}"
clipboard_backend="${STT_CLIPBOARD_BACKEND:-auto}"
copy_verify=1
output_transcript=""
output_recovered=""
transcribe_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --duration)
      if [[ $# -lt 2 ]]; then
        echo "--duration requires a positive integer" >&2
        exit 2
      fi
      duration="$2"
      duration_set=1
      shift 2
      ;;
    --duration=*)
      duration="${1#*=}"
      duration_set=1
      shift
      ;;
    --record-only)
      record_only=1
      shift
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
      transcribe_args=("$@")
      break
      ;;
    -*)
      echo "unknown wrapper option before --: $1" >&2
      echo "put transcribe options after --" >&2
      exit 2
      ;;
    *)
      if [[ "$duration_set" -eq 1 ]]; then
        echo "unexpected argument before --: $1" >&2
        exit 2
      fi
      duration="$1"
      duration_set=1
      shift
      ;;
  esac
done

if ! [[ "$duration" =~ ^[1-9][0-9]*$ ]]; then
  echo "duration_seconds must be a positive integer: $duration" >&2
  exit 2
fi

echo "step=record duration=${duration}s" >&2
recording="$("$repo_root/scripts/record.sh" "$duration")"

if [[ -z "$recording" || ! -f "$recording" ]]; then
  echo "recording file was not created: $recording" >&2
  exit 1
fi

echo "recording=$recording" >&2

if [[ "$record_only" -eq 1 ]]; then
  printf '%s\n' "$recording"
  exit 0
fi

stt_args=()
if [[ "$recovery" -eq 0 ]]; then
  stt_args+=("--no-recovery")
fi
if [[ -n "$memory_path" ]]; then
  stt_args+=("--memory" "$memory_path")
fi
stt_args+=("--min-confidence" "$min_confidence")
stt_args+=("--clipboard-backend" "$clipboard_backend")
if [[ "$copy_verify" -eq 0 ]]; then
  stt_args+=("--no-copy-verify")
fi
if [[ -n "$output_transcript" ]]; then
  stt_args+=("--output-transcript" "$output_transcript")
fi
if [[ -n "$output_recovered" ]]; then
  stt_args+=("--output-recovered" "$output_recovered")
fi

"$repo_root/scripts/stt_clipboard.sh" "${stt_args[@]}" "$recording" "${transcribe_args[@]}"
