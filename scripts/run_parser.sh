#!/usr/bin/env bash
# Wrapper: reads API key from Keychain, runs parser. Key never appears in command args or output.
# Usage: bash scripts/run_parser.sh <file_path>
set -e

if [[ -z "$1" ]]; then
  echo "Usage: run_parser.sh <file_path>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Read key from Keychain silently — never echo, never export to subshell visible in ps
ANTHROPIC_API_KEY=$(security find-generic-password -s eval-engine -a anthropic -w 2>/dev/null)
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
  echo "Error: API key not found in Keychain. Run: bash scripts/setup_keychain.sh" >&2
  exit 1
fi

export ANTHROPIC_API_KEY
PYTHONPATH="$REPO_DIR/.pip_deps" python3 "$SCRIPT_DIR/parse_transcript.py" "$1"
