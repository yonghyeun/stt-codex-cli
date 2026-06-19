#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/record.sh [duration_seconds]

Records microphone input to a WAV file under output/recordings/.

Environment:
  STT_RECORD_DEVICE    ALSA device. Default: default
  STT_RECORD_RATE      Sample rate. Default: 16000
  STT_RECORD_CHANNELS  Channel count. Default: 1
  STT_RECORD_FORMAT    ALSA sample format. Default: S16_LE
  STT_OUTPUT_DIR       Output directory. Default: output/recordings
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

duration="${1:-5}"

if ! [[ "$duration" =~ ^[1-9][0-9]*$ ]]; then
  echo "duration_seconds must be a positive integer: $duration" >&2
  exit 2
fi

if ! command -v arecord >/dev/null 2>&1; then
  echo "arecord is required but was not found." >&2
  exit 1
fi

device="${STT_RECORD_DEVICE:-default}"
rate="${STT_RECORD_RATE:-16000}"
channels="${STT_RECORD_CHANNELS:-1}"
format="${STT_RECORD_FORMAT:-S16_LE}"
output_dir="${STT_OUTPUT_DIR:-output/recordings}"

mkdir -p "$output_dir"

timestamp="$(date +%Y%m%d-%H%M%S)"
output_file="$output_dir/recording-$timestamp.wav"

echo "recording: ${duration}s -> $output_file" >&2
arecord \
  -D "$device" \
  -f "$format" \
  -r "$rate" \
  -c "$channels" \
  -d "$duration" \
  "$output_file"

echo "$output_file"
