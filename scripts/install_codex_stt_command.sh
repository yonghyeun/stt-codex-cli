#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/install_codex_stt_command.sh [--dry-run] [--target <path>] [--root <path>] [--force]

Installs a codex-stt launcher command.

Defaults:
  --target  ${HOME}/.local/bin/codex-stt
  --root    ${HOME}/stt-codex-cli

The installed launcher uses CODEX_STT_ROOT at runtime when set:
  CODEX_STT_ROOT=/path/to/stt-codex-cli codex-stt --help
EOF
}

dry_run=0
force=0
target="${HOME}/.local/bin/codex-stt"
default_root='${HOME}/stt-codex-cli'
root="${default_root}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    --target)
      if [[ $# -lt 2 ]]; then
        echo "error: --target requires a path" >&2
        exit 2
      fi
      target="$2"
      shift 2
      ;;
    --root)
      if [[ $# -lt 2 ]]; then
        echo "error: --root requires a path" >&2
        exit 2
      fi
      root="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

target_dir="$(dirname "$target")"
launcher_content="$(
  cat <<EOF
#!/usr/bin/env bash
set -euo pipefail

repo_root="\${CODEX_STT_ROOT:-${root}}"
entrypoint="\${repo_root}/scripts/stt_codex.py"

if [[ ! -x "\${entrypoint}" ]]; then
  echo "codex-stt: STT wrapper not found or not executable: \${entrypoint}" >&2
  echo "codex-stt: set CODEX_STT_ROOT to the stt-codex-cli repo root if needed" >&2
  exit 1
fi

cd "\${repo_root}"
exec "\${entrypoint}" "\$@"
EOF
)"

if [[ "${dry_run}" -eq 1 ]]; then
  echo "Would install: ${target}"
  echo "Would create directory: ${target_dir}"
  echo
  echo "${launcher_content}"
  exit 0
fi

if [[ -e "${target}" && "${force}" -ne 1 ]]; then
  existing_content="$(cat "${target}")"
  if [[ "${existing_content}" != "${launcher_content}" ]]; then
    echo "error: target exists with different content: ${target}" >&2
    echo "hint: use --force to overwrite" >&2
    exit 1
  fi
fi

mkdir -p "${target_dir}"
printf '%s\n' "${launcher_content}" > "${target}"
chmod +x "${target}"

echo "Installed: ${target}"
if [[ ":${PATH}:" != *":${target_dir}:"* ]]; then
  echo "warning: ${target_dir} is not in PATH" >&2
fi
echo "Try: codex-stt --help"
