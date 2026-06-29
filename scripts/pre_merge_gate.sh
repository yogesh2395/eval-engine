#!/usr/bin/env bash
# pre_merge_gate.sh — gate script that must pass before merging to main
#
# Checks:
#   1. pytest tests/          — all unit tests pass
#   2. security sweep         — no credentials or sensitive patterns in changed files
#   3. open D-entry scan      — no unresolved architectural decisions or TODO:D- markers
#
# Usage:
#   ./scripts/pre_merge_gate.sh              # compares HEAD against main
#   ./scripts/pre_merge_gate.sh --staged     # scans only staged (git add) files
#
# Exit codes: 0 = PASS, 1 = FAIL

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGED_ONLY=false
FAIL=0
WARN=0

if [[ "${1:-}" == "--staged" ]]; then
    STAGED_ONLY=true
fi

# ── helpers ────────────────────────────────────────────────────────────────────

pass()  { echo "  PASS: $*"; }
fail()  { echo "  FAIL: $*"; FAIL=1; }
warn()  { echo "  WARN: $*"; WARN=1; }
header(){ echo ""; echo "--- [$1/3] $2 ---"; }

# ── collect changed files ──────────────────────────────────────────────────────

if $STAGED_ONLY; then
    CHANGED_FILES=$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null || true)
else
    # Changed vs main (or HEAD~1 as fallback when on main)
    BASE=$(git -C "$REPO_ROOT" merge-base HEAD origin/main 2>/dev/null \
           || git -C "$REPO_ROOT" merge-base HEAD main 2>/dev/null \
           || echo "HEAD~1")
    CHANGED_FILES=$(git -C "$REPO_ROOT" diff --name-only "$BASE" HEAD 2>/dev/null || true)
fi

# ── 1. pytest ─────────────────────────────────────────────────────────────────

echo "=== Pre-merge gate ==="
header 1 "pytest tests/"

if cd "$REPO_ROOT" && python -m pytest tests/ -q --tb=short 2>&1; then
    pass "all tests"
else
    fail "pytest returned non-zero — fix tests before merging"
fi

# ── 2. Security sweep ─────────────────────────────────────────────────────────

header 2 "Security sweep"

SECURITY_FAIL=0

# Patterns: each entry is "SEVERITY|PATTERN_LABEL|GREP_REGEX"
declare -a PATTERNS=(
    "CRITICAL|Anthropic key token|sk-ant-[a-zA-Z0-9]{10,}"
    "CRITICAL|ANTHROPIC_API_KEY hardcoded|ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*['\"][^'\"\$]"
    "HIGH|API_KEY literal|API_KEY[[:space:]]*=[[:space:]]*['\"][^\$]"
    "HIGH|password literal|[Pp]assword[[:space:]]*=[[:space:]]*['\"][^\$]"
    "HIGH|token literal|[[:space:]]token[[:space:]]*=[[:space:]]*['\"][^\$]"
    "HIGH|secret literal|[[:space:]]secret[[:space:]]*=[[:space:]]*['\"][^\$]"
    "MEDIUM|env var mutation|os\.environ\[.ANTHROPIC_API_KEY.\][[:space:]]*="
)

# Files to skip for security scan (docs, examples, gitignore-listed)
SKIP_PATTERNS=(".gitignore" ".env.example" "setup_keychain.sh")

for rel_file in $CHANGED_FILES; do
    full="$REPO_ROOT/$rel_file"
    [[ -f "$full" ]] || continue

    # Skip .env.example and similar
    skip=false
    for sp in "${SKIP_PATTERNS[@]}"; do
        [[ "$rel_file" == *"$sp"* ]] && skip=true && break
    done
    $skip && continue

    # Flag .env file itself if tracked
    if [[ "$(basename "$rel_file")" == ".env" ]]; then
        echo "  BLOCK [CRITICAL] $rel_file: .env file should not be tracked in git"
        SECURITY_FAIL=1
        continue
    fi

    # Flag secrets.* files
    if [[ "$(basename "$rel_file")" == secrets.* ]]; then
        echo "  BLOCK [CRITICAL] $rel_file: secrets file should not be tracked in git"
        SECURITY_FAIL=1
        continue
    fi

    # Skip binary files
    if file "$full" 2>/dev/null | grep -q "binary"; then
        continue
    fi

    for entry in "${PATTERNS[@]}"; do
        IFS='|' read -r severity label pattern <<< "$entry"
        while IFS= read -r match; do
            [[ -z "$match" ]] && continue
            lineno=$(echo "$match" | cut -d: -f1)
            snippet=$(echo "$match" | cut -d: -f2- | sed 's/^[[:space:]]*//')
            echo "  BLOCK [$severity] $rel_file:$lineno — $label: $snippet"
            SECURITY_FAIL=1
        done < <(grep -nE "$pattern" "$full" 2>/dev/null || true)
    done
done

if [[ $SECURITY_FAIL -eq 0 ]]; then
    pass "no credentials or sensitive patterns detected"
else
    fail "security findings above — remove secrets before merging"
fi

# ── 3. Open D-entry check ─────────────────────────────────────────────────────

header 3 "Open D-entry check"

D_ISSUES=0
TRACKER="$REPO_ROOT/decisions_tracker.md"

# Check for TODO:D- markers in Python / shell / YAML source files
while IFS= read -r -d '' f; do
    rel="${f#$REPO_ROOT/}"
    while IFS= read -r match; do
        [[ -z "$match" ]] && continue
        lineno=$(echo "$match" | cut -d: -f1)
        snippet=$(echo "$match" | cut -d: -f2- | sed 's/^[[:space:]]*//')
        warn "unresolved D-entry marker: $rel:$lineno — $snippet"
        D_ISSUES=1
    done < <(grep -nE '#[[:space:]]*(TODO|STUB|FIXME)[[:space:]]*:?[[:space:]]*D-[0-9]+' "$f" 2>/dev/null || true)
done < <(find "$REPO_ROOT" -type f \
    \( -name "*.py" -o -name "*.sh" -o -name "*.yaml" -o -name "*.yml" \) \
    ! -path "*/.claude/worktrees/*" ! -path "*/__pycache__/*" -print0)

# Check decisions_tracker.md for entries with Status not Locked or Superseded
if [[ -f "$TRACKER" ]]; then
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        warn "non-locked D-entry in decisions_tracker.md: $line"
        D_ISSUES=1
    done < <(grep -E '\*\*Status:\*\*[[:space:]]*(Open|Pending|Draft|WIP)' "$TRACKER" 2>/dev/null || true)
fi

if [[ $D_ISSUES -eq 0 ]]; then
    pass "no open D-entry markers"
else
    echo "  (D-entry warnings are non-blocking — review before release)"
fi

# ── Result ────────────────────────────────────────────────────────────────────

echo ""
echo "=== Gate result ==="
if [[ $FAIL -eq 0 ]]; then
    if [[ $WARN -eq 1 ]]; then
        echo "PASS (with warnings) — tests and security clean; review D-entry warnings above"
    else
        echo "PASS — all checks clear, safe to merge"
    fi
    exit 0
else
    echo "FAIL — fix the above before merging to main"
    exit 1
fi
