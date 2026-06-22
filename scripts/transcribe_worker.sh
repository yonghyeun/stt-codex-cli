#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${STT_PYTHON_BIN:-$repo_root/.venv/bin/python}"
site_packages="${STT_SITE_PACKAGES:-$repo_root/.venv/lib/python3.12/site-packages}"

if [[ ! -x "$python_bin" ]]; then
  echo "Python venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cuda_lib_dirs=(
  "$site_packages/nvidia/cublas/lib"
  "$site_packages/nvidia/cudnn/lib"
)

for cuda_lib_dir in "${cuda_lib_dirs[@]}"; do
  if [[ -d "$cuda_lib_dir" ]]; then
    export LD_LIBRARY_PATH="$cuda_lib_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  fi
done

exec "$python_bin" "$repo_root/scripts/transcribe_worker.py" "$@"
