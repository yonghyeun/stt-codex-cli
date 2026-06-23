#!/usr/bin/env bash

stt_primary_worktree() {
  local repo_root="$1"
  local git_output

  if ! command -v git >/dev/null 2>&1; then
    return 0
  fi

  git_output="$(git -C "$repo_root" worktree list --porcelain 2>/dev/null || true)"
  if [[ -z "$git_output" ]]; then
    return 0
  fi

  local line
  local current_worktree=""
  local first_worktree=""
  local main_worktree=""

  while IFS= read -r line; do
    case "$line" in
      worktree\ *)
        current_worktree="${line#worktree }"
        if [[ -z "$first_worktree" ]]; then
          first_worktree="$current_worktree"
        fi
        ;;
      branch\ refs/heads/main)
        main_worktree="$current_worktree"
        ;;
    esac
  done <<< "$git_output"

  if [[ -n "$main_worktree" ]]; then
    printf '%s\n' "$main_worktree"
    return 0
  fi

  if [[ -n "$first_worktree" ]]; then
    printf '%s\n' "$first_worktree"
  fi
}

stt_default_site_packages_for_python() {
  local python_bin="$1"
  local venv_root
  local site_packages
  local candidate

  venv_root="$(cd "$(dirname "$python_bin")/.." && pwd)"
  site_packages=""

  for candidate in "$venv_root"/lib/python3*/site-packages; do
    if [[ -d "$candidate" ]]; then
      site_packages="$candidate"
      break
    fi
  done

  if [[ -z "$site_packages" ]]; then
    site_packages="$venv_root/lib/python3.12/site-packages"
  fi

  printf '%s\n' "$site_packages"
}

resolve_stt_python_env() {
  local repo_root="$1"
  local python_bin=""
  local site_packages=""
  local checked=()

  if [[ -n "${STT_PYTHON_BIN:-}" ]]; then
    python_bin="$STT_PYTHON_BIN"
    checked+=("$python_bin")
  else
    local candidates=("$repo_root/.venv/bin/python")
    local primary_worktree
    primary_worktree="$(stt_primary_worktree "$repo_root")"
    if [[ -n "$primary_worktree" && "$primary_worktree" != "$repo_root" ]]; then
      candidates+=("$primary_worktree/.venv/bin/python")
    fi

    local candidate
    for candidate in "${candidates[@]}"; do
      checked+=("$candidate")
      if [[ -x "$candidate" ]]; then
        python_bin="$candidate"
        break
      fi
    done
  fi

  if [[ -z "$python_bin" || ! -x "$python_bin" ]]; then
    printf 'Python venv not found. Checked: %s\n' "${checked[*]}" >&2
    printf 'Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n' >&2
    printf 'Or set STT_PYTHON_BIN to a prepared workspace venv.\n' >&2
    return 1
  fi

  site_packages="${STT_SITE_PACKAGES:-$(stt_default_site_packages_for_python "$python_bin")}"

  STT_RESOLVED_PYTHON_BIN="$python_bin"
  STT_RESOLVED_SITE_PACKAGES="$site_packages"
  export STT_RESOLVED_PYTHON_BIN
  export STT_RESOLVED_SITE_PACKAGES
}
