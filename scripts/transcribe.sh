#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "$repo_root/scripts/stt_python_env.sh"
resolve_stt_python_env "$repo_root"

python_bin="$STT_RESOLVED_PYTHON_BIN"
site_packages="$STT_RESOLVED_SITE_PACKAGES"

cuda_lib_dirs=(
  "$site_packages/nvidia/cublas/lib"
  "$site_packages/nvidia/cudnn/lib"
)

for cuda_lib_dir in "${cuda_lib_dirs[@]}"; do
  if [[ -d "$cuda_lib_dir" ]]; then
    export LD_LIBRARY_PATH="$cuda_lib_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  fi
done

exec "$python_bin" "$repo_root/scripts/transcribe.py" "$@"
