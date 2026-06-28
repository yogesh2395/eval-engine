#!/usr/bin/env bash
# One-time setup: store Anthropic API key in macOS Keychain.
# After running this, scripts read the key with:
#   export ANTHROPIC_API_KEY=$(security find-generic-password -s eval-engine -a anthropic -w)
#
# Key is stored in your login Keychain (encrypted at rest, unlocked by your macOS password).
# No file on disk. Not readable by other users or processes without Keychain access.
#
# Usage: bash scripts/setup_keychain.sh

set -e

echo "Enter your Anthropic API key (starts with sk-ant-):"
read -rs API_KEY
echo

if [[ -z "$API_KEY" ]]; then
  echo "Error: empty key." >&2
  exit 1
fi

if [[ "$API_KEY" != sk-ant-* ]]; then
  echo "Warning: key does not start with 'sk-ant-' — proceeding anyway."
fi

# -U: update if already exists
security add-generic-password \
  -s "eval-engine" \
  -a "anthropic" \
  -w "$API_KEY" \
  -U

echo "Key stored in Keychain under service='eval-engine', account='anthropic'."
echo ""
echo "To use in a shell session:"
echo "  export ANTHROPIC_API_KEY=\$(security find-generic-password -s eval-engine -a anthropic -w)"
echo ""
echo "To use in scripts (add to ~/.zshrc or export before running):"
echo "  export ANTHROPIC_API_KEY=\$(security find-generic-password -s eval-engine -a anthropic -w)"
