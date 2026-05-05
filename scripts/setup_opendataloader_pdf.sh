#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_opendataloader_pdf.sh [--check-only]

What it does:
  1. Verifies Java 11+ is available, which OpenDataLoader PDF requires.
  2. Verifies uv is available.
  3. Installs the project with the PDF extra via `uv sync --extra pdf`.

Options:
  --check-only   Only verify prerequisites. Do not install dependencies.
EOF
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: $command_name" >&2
    return 1
  fi
}

check_java_version() {
  require_command java

  local version_output
  version_output="$(java -version 2>&1 | head -n 1)"
  local major_version
  major_version="$(
    printf '%s' "$version_output" \
      | sed -E 's/.*version "([0-9]+)(\.[0-9]+)?(\.[0-9_]+)?".*/\1/'
  )"

  if [[ -z "$major_version" || "$major_version" == "$version_output" ]]; then
    echo "Could not determine Java version from: $version_output" >&2
    return 1
  fi

  if (( major_version < 11 )); then
    echo "Java 11+ is required for OpenDataLoader PDF. Found: $version_output" >&2
    return 1
  fi

  echo "Java check passed: $version_output"
}

check_uv() {
  require_command uv
  echo "uv check passed: $(uv --version)"
}

install_pdf_extra() {
  echo "Installing project dependencies with PDF extra..."
  (
    cd "$ROOT_DIR"
    uv sync --extra pdf
  )
}

main() {
  local check_only="false"

  while (($# > 0)); do
    case "$1" in
      --check-only)
        check_only="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done

  check_java_version
  check_uv

  if [[ "$check_only" == "true" ]]; then
    echo "Prerequisite checks completed."
    exit 0
  fi

  install_pdf_extra
  echo "OpenDataLoader PDF prerequisites are ready."
}

main "$@"
