#!/usr/bin/env bash
# install_hooks.sh — install git hooks for this repo
# Run once after cloning, or after any update to scripts/hooks/
#
# Usage: ./scripts/install_hooks.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_SRC="$REPO_ROOT/scripts/hooks"

# Resolve the shared hooks dir via the common git dir so this also works from a
# git worktree (where .git is a file, not a directory). --git-common-dir points
# at the main repo's .git for every worktree; hooks live there and are shared.
COMMON_DIR="$(cd "$REPO_ROOT" && git rev-parse --git-common-dir 2>/dev/null || true)"
if [[ -z "$COMMON_DIR" ]]; then
    echo "ERROR: not inside a git repository — run from a checkout or worktree"
    exit 1
fi
case "$COMMON_DIR" in
    /*) ;;                               # already absolute
    *)  COMMON_DIR="$REPO_ROOT/$COMMON_DIR" ;;
esac
HOOKS_DST="$COMMON_DIR/hooks"
mkdir -p "$HOOKS_DST"

for hook in "$HOOKS_SRC"/*; do
    name="$(basename "$hook")"
    dst="$HOOKS_DST/$name"
    cp "$hook" "$dst"
    chmod +x "$dst"
    echo "  installed: $dst"
done

echo ""
echo "Hooks installed. Validator sign-off (logs/validator_pass.flag) is"
echo "required before committing logic files. See scripts/hooks/pre-commit."
