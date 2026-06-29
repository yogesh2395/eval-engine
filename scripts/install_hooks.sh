#!/usr/bin/env bash
# install_hooks.sh — install git hooks for this repo
# Run once after cloning, or after any update to scripts/hooks/
#
# Usage: ./scripts/install_hooks.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_SRC="$REPO_ROOT/scripts/hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [[ ! -d "$HOOKS_DST" ]]; then
    echo "ERROR: .git/hooks not found — run from a git repository root"
    exit 1
fi

for hook in "$HOOKS_SRC"/*; do
    name="$(basename "$hook")"
    dst="$HOOKS_DST/$name"
    cp "$hook" "$dst"
    chmod +x "$dst"
    echo "  installed: .git/hooks/$name"
done

echo ""
echo "Hooks installed. Validator sign-off (logs/validator_pass.flag) is"
echo "required before committing logic files. See scripts/hooks/pre-commit."
