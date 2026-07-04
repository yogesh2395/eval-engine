"""
scripts/check_justification_completeness.py — mechanical design/execution-leakage checker.

Deterministic. No judgment call. Enforces the Unit A contract: every non-N/A
dimension in `criterion_scores` MUST carry a non-empty entry in
`dimension_justifications`. A scored dimension with no attached observation/
quote is a design-execution leak (a score with no evidence trail) — this
script is the "should-have-caught-it" mechanism referenced in the Unit B plan.

Usage:
    python3 scripts/check_justification_completeness.py <scorer_output.json>

Exit codes:
    0 — PASS: every non-N/A dimension has a non-empty justification.
    1 — FAIL: at least one non-N/A dimension is missing its justification.

The core logic is exposed as `check_completeness()` so callers (tests, the
process-monitor stage wrapper, the validator) can invoke it in-process
without a subprocess call. No side effects at import time.
"""

import json
import sys

# Heuristic quote-like characters. Advisory only — never changes exit status.
_QUOTE_CHARS = ('"', "'", "‘", "’", "“", "”")


def check_completeness(criterion_scores: dict, dimension_justifications: dict) -> dict:
    """
    Pure function — no I/O.

    Args:
        criterion_scores: dict of {dimension: score}. Score may be an int,
            float, or the string "N/A" (case-insensitive, whitespace-tolerant).
        dimension_justifications: dict of {dimension: justification text}.
            A missing key is treated as {} by the caller (see main()).

    Returns:
        {
          "status": "PASS" | "FAIL",
          "missing": [sorted dimension names scored but not justified],
          "quote_warnings": [sorted dimension names justified but with no
                              detectable verbatim quote span],
          "checked": int (count of non-N/A dimensions considered),
        }
    """
    criterion_scores = criterion_scores or {}
    dimension_justifications = dimension_justifications or {}

    non_na = {
        dim
        for dim, score in criterion_scores.items()
        if str(score).strip().upper() != "N/A"
    }

    justified = {
        dim
        for dim, text in dimension_justifications.items()
        if isinstance(text, str) and text.strip() != ""
    }

    missing = sorted(non_na - justified)

    quote_warnings = sorted(
        dim
        for dim in non_na
        if dim in justified
        and not any(ch in dimension_justifications[dim] for ch in _QUOTE_CHARS)
    )

    status = "FAIL" if missing else "PASS"

    return {
        "status": status,
        "missing": missing,
        "quote_warnings": quote_warnings,
        "checked": len(non_na),
    }


def main(argv):
    """
    CLI entry point. `argv` excludes the program name (i.e. sys.argv[1:]).
    Returns the intended process exit code (0 or 1); does not call sys.exit
    itself so it stays testable.
    """
    if len(argv) != 1:
        print(
            "Usage: python3 scripts/check_justification_completeness.py "
            "<scorer_output.json>",
            file=sys.stderr,
        )
        return 1

    path = argv[0]
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not read/parse {path!r}: {exc}", file=sys.stderr)
        return 1

    criterion_scores = data.get("criterion_scores", {}) or {}
    dimension_justifications = data.get("dimension_justifications", {}) or {}

    result = check_completeness(criterion_scores, dimension_justifications)

    for dim in result["missing"]:
        score = criterion_scores.get(dim)
        print(f"LEAK: dimension '{dim}' scored {score} with no attached justification")

    for dim in result["quote_warnings"]:
        print(f"WARN: dimension '{dim}' justification has no detectable verbatim quote")

    if result["status"] == "PASS":
        print(f"PASS: all {result['checked']} non-N/A dimensions justified")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
