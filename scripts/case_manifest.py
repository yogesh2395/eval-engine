#!/usr/bin/env python3
"""
case_manifest.py — stratified random sampling of training cases.

CLI:
    python3 scripts/case_manifest.py [--n N] [--seed SEED] [--list]

Stdout: JSON list of case objects.
Stderr: [case_manifest] N=15 seed=42 categories={Profitability:3, M&A:2, ...}

Never reads from examples/testing_set/.
Raises ValueError + exits non-zero if any returned path is under testing_set.
"""

import sys
import os
import json
import re
import argparse
import random
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────
REPO_ROOT    = Path(__file__).resolve().parent.parent
TRAINING_DIR = REPO_ROOT / "examples" / "training_set"
TESTING_DIR  = REPO_ROOT / "examples" / "testing_set"
INDEX_PATH   = TRAINING_DIR / "INDEX.md"

# ── letter → canonical category name ──────────────────────────────────────
CATEGORY_MAP = {
    "A": "Profitability",
    "B": "Market Entry",
    "C": "Pricing",
    "D": "Growth Strategy",
    "E": "M&A",
    "F": "Unconventional Cases",
}
MAJOR_CATEGORIES = list(CATEGORY_MAP.values())


# ── parsing ────────────────────────────────────────────────────────────────

def parse_index():
    """Parse INDEX.md table → list of dicts with case_id, path, sector, difficulty."""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    cases = []
    # Match data rows: | 2 | [Name](cases/c02_foo.md) | Sector | Difficulty |
    row_re = re.compile(
        r"^\|\s*\d+\s*\|"            # | num |
        r"\s*\[([^\]]+)\]\(([^)]+)\)\s*\|"  # | [Name](rel_path) |
        r"\s*([^|]+)\s*\|"           # | Sector |
        r"\s*([^|]+)\s*\|",          # | Difficulty |
        re.MULTILINE,
    )
    for m in row_re.finditer(content):
        rel_path   = m.group(2).strip()   # e.g. "cases/c02_lease_fee.md"
        sector     = m.group(3).strip()
        difficulty = m.group(4).strip()

        filename = os.path.basename(rel_path)          # c02_lease_fee.md
        case_id  = filename.split("_")[0]              # c02

        # Relative path from repo root (used in output JSON)
        out_path = str(Path("examples/training_set") / rel_path)
        # Absolute path (used internally for file reads)
        full_path = str(TRAINING_DIR / rel_path)

        cases.append({
            "case_id":    case_id,
            "path":       out_path,
            "sector":     sector,
            "difficulty": difficulty,
            "_full_path": full_path,   # stripped before output
        })

    return cases


def extract_category(file_path: str) -> str:
    """Extract canonical category name from a case file's ## Metadata block."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return "Unknown"

    m = re.search(r"-\s+\*\*Category:\*\*\s+([A-Z])\.\s+(.+)", content)
    if m:
        letter   = m.group(1)
        raw_name = m.group(2).strip()
        return CATEGORY_MAP.get(letter, raw_name)

    return "Unknown"


def build_all_cases():
    """Return all training cases with category populated; _full_path stripped."""
    cases = parse_index()
    for case in cases:
        case["category"] = extract_category(case["_full_path"])
        del case["_full_path"]
    return cases


# ── sampling ───────────────────────────────────────────────────────────────

def stratified_sample(cases, n, seed):
    """
    Stratified random sample.

    When N >= number of major categories present in corpus:
      - Phase 1: guarantee exactly 1 case per major category.
      - Phase 2: fill remaining slots weighted by corpus category frequency.
    When N < number of major categories: weighted random sample (no Phase 1).

    Returns a shuffled list of length n.
    """
    rng = random.Random(seed)

    # Index by category
    by_category = {}
    for case in cases:
        by_category.setdefault(case["category"], []).append(case)

    selected = []
    selected_ids = set()

    cats_present = [c for c in MAJOR_CATEGORIES if c in by_category]
    if n >= len(cats_present):
        # Phase 1 — one guaranteed pick per major category (only when n >= #categories)
        for cat in cats_present:
            pick = rng.choice(by_category[cat])
            selected.append(pick)
            selected_ids.add(pick["case_id"])

    # Phase 2 — fill remaining slots with weighted sampling without replacement
    remaining = n - len(selected)
    if remaining > 0:
        pool = [c for c in cases if c["case_id"] not in selected_ids]
        cat_freq = {cat: len(lst) for cat, lst in by_category.items()}
        weights  = [cat_freq.get(c["category"], 1) for c in pool]

        for _ in range(min(remaining, len(pool))):
            (chosen,) = rng.choices(pool, weights=weights, k=1)
            idx = pool.index(chosen)
            selected.append(chosen)
            selected_ids.add(chosen["case_id"])
            pool.pop(idx)
            weights.pop(idx)

    rng.shuffle(selected)
    return selected


# ── guard ──────────────────────────────────────────────────────────────────

def _assert_no_testing_set(cases):
    """Raise ValueError and exit non-zero if any path is under testing_set."""
    testing_str = str(TESTING_DIR.resolve())
    for case in cases:
        p = case["path"]
        abs_p = str((REPO_ROOT / p).resolve()) if not Path(p).is_absolute() else str(Path(p).resolve())
        if abs_p.startswith(testing_str):
            raise ValueError(f"BUG: testing_set path in output: {p}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Training case manifest: stratified random sampler"
    )
    parser.add_argument("--n",    type=int,  default=15, help="Cases to sample (default: 15)")
    parser.add_argument("--seed", type=int,  default=42, help="Random seed (default: 42)")
    parser.add_argument("--list", action="store_true",   help="List all cases, no sampling")
    args = parser.parse_args()

    all_cases = build_all_cases()

    if args.list:
        output = all_cases
    else:
        n = args.n
        if n > len(all_cases):
            print(
                f"[case_manifest] ERROR: --n={n} exceeds corpus size ({len(all_cases)})",
                file=sys.stderr,
            )
            sys.exit(1)

        output = stratified_sample(all_cases, n, args.seed)

        try:
            _assert_no_testing_set(output)
        except ValueError as exc:
            print(f"[case_manifest] ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

        # Stderr summary
        cat_counts: dict[str, int] = {}
        for c in output:
            cat_counts[c["category"]] = cat_counts.get(c["category"], 0) + 1
        cat_str = ", ".join(f"{k}:{v}" for k, v in sorted(cat_counts.items()))
        print(f"[case_manifest] N={n} seed={args.seed} categories={{{cat_str}}}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
