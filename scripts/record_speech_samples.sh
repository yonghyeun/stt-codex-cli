#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/record_speech_samples.sh [options] <sample_id>...

Generator-style recorder for speech input samples.

Default behavior:
  Select the first sample without audio.wav from <sample_id>...
  Show its expected.txt
  Record one WAV with scripts/push_to_talk.py --record-only
  Move it to evals/inputs/speech/v1/samples/<sample_id>/audio.wav

Options:
  --input-root PATH      Speech input root. Default: evals/inputs/speech/v1
  --sample-id ID         Record this exact sample id
  --force                Overwrite the selected sample's audio.wav
  --print-next           Print the next selected sample and exit
  --dry-run              Print the selected target without recording
  --backend BACKEND      push_to_talk backend. Default: stdin-repeat
  --trigger-key KEY      stdin-repeat trigger key. Default: t
  --max-duration SEC     Max recording duration. Default: push_to_talk default
  --min-duration SEC     Min recording duration. Default: push_to_talk default
  --release-gap SEC      Stop gap for stdin-repeat. Default: push_to_talk default
  --listen-timeout SEC   Wait time for trigger before failing
  -h, --help             Show this help

For stdin-repeat backend:
  Press and hold/repeat the trigger key to record.
  Stop pressing it to end recording.

Example:
  scripts/record_speech_samples.sh \
    cmd-0009 cmd-0010 cmd-0011 cmd-0012 cmd-0013 cmd-0014 cmd-0015 cmd-0016
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
input_root="evals/inputs/speech/v1"
selected_sample_id=""
force=0
print_next=0
dry_run=0
backend="stdin-repeat"
trigger_key="t"
max_duration=""
min_duration=""
release_gap=""
listen_timeout=""
sample_ids=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-root)
      input_root="${2:-}"
      if [[ -z "$input_root" ]]; then
        echo "--input-root requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    --sample-id)
      selected_sample_id="${2:-}"
      if [[ -z "$selected_sample_id" ]]; then
        echo "--sample-id requires an id" >&2
        exit 2
      fi
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    --print-next)
      print_next=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --backend)
      backend="${2:-}"
      if [[ -z "$backend" ]]; then
        echo "--backend requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    --trigger-key)
      trigger_key="${2:-}"
      if [[ -z "$trigger_key" ]]; then
        echo "--trigger-key requires a key" >&2
        exit 2
      fi
      shift 2
      ;;
    --max-duration)
      max_duration="${2:-}"
      if [[ -z "$max_duration" ]]; then
        echo "--max-duration requires seconds" >&2
        exit 2
      fi
      shift 2
      ;;
    --min-duration)
      min_duration="${2:-}"
      if [[ -z "$min_duration" ]]; then
        echo "--min-duration requires seconds" >&2
        exit 2
      fi
      shift 2
      ;;
    --release-gap)
      release_gap="${2:-}"
      if [[ -z "$release_gap" ]]; then
        echo "--release-gap requires seconds" >&2
        exit 2
      fi
      shift 2
      ;;
    --listen-timeout)
      listen_timeout="${2:-}"
      if [[ -z "$listen_timeout" ]]; then
        echo "--listen-timeout requires seconds" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        sample_ids+=("$1")
        shift
      done
      ;;
    -*)
      echo "unknown option: $1" >&2
      exit 2
      ;;
    *)
      sample_ids+=("$1")
      shift
      ;;
  esac
done

if [[ "${#sample_ids[@]}" -eq 0 && -z "$selected_sample_id" ]]; then
  echo "at least one sample_id is required" >&2
  usage >&2
  exit 2
fi

input_root_path="$repo_root/$input_root"
if [[ "$input_root" = /* ]]; then
  input_root_path="$input_root"
fi

if [[ ! -d "$input_root_path/samples" ]]; then
  echo "input samples directory not found: $input_root_path/samples" >&2
  exit 1
fi

sample_exists() {
  local sample_id="$1"
  [[ -d "$input_root_path/samples/$sample_id" && -f "$input_root_path/samples/$sample_id/expected.txt" ]]
}

choose_next_sample() {
  if [[ -n "$selected_sample_id" ]]; then
    if ! sample_exists "$selected_sample_id"; then
      echo "sample not found or missing expected.txt: $selected_sample_id" >&2
      exit 1
    fi
    if [[ -f "$input_root_path/samples/$selected_sample_id/audio.wav" && "$force" -ne 1 ]]; then
      echo "audio.wav already exists for $selected_sample_id; pass --force to overwrite" >&2
      exit 1
    fi
    printf '%s\n' "$selected_sample_id"
    return 0
  fi

  local sample_id
  for sample_id in "${sample_ids[@]}"; do
    if ! sample_exists "$sample_id"; then
      echo "sample not found or missing expected.txt: $sample_id" >&2
      exit 1
    fi
    if [[ ! -f "$input_root_path/samples/$sample_id/audio.wav" ]]; then
      printf '%s\n' "$sample_id"
      return 0
    fi
  done

  echo "no next sample: all listed samples already have audio.wav" >&2
  exit 0
}

sample_id="$(choose_next_sample)"
sample_dir="$input_root_path/samples/$sample_id"
expected_file="$sample_dir/expected.txt"
output_file="$sample_dir/audio.wav"

echo "sample_id=$sample_id"
echo "expected:"
sed -n '1p' "$expected_file"
echo "target=$output_file"

if [[ "$print_next" -eq 1 || "$dry_run" -eq 1 ]]; then
  exit 0
fi

tmp_dir="$repo_root/output/recordings/speech-samples"
push_args=(
  "$repo_root/scripts/push_to_talk.py"
  --record-only
  --backend "$backend"
  --trigger-key "$trigger_key"
  --output-dir "$tmp_dir"
)

if [[ -n "$max_duration" ]]; then
  push_args+=(--max-duration "$max_duration")
fi
if [[ -n "$min_duration" ]]; then
  push_args+=(--min-duration "$min_duration")
fi
if [[ -n "$release_gap" ]]; then
  push_args+=(--release-gap "$release_gap")
fi
if [[ -n "$listen_timeout" ]]; then
  push_args+=(--listen-timeout "$listen_timeout")
fi

recording="$("${push_args[@]}")"
if [[ -z "$recording" || ! -f "$recording" ]]; then
  echo "recording file was not created: $recording" >&2
  exit 1
fi

mv "$recording" "$output_file"
echo "wrote=$output_file"
