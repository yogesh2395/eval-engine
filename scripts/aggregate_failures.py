#!/usr/bin/env python3
"""
aggregate_failures.py — Aggregates parser-evaluator outputs from a run directory
into a failure_summary.json for the parser-fixer agent.

Usage:
    python3 scripts/aggregate_failures.py logs/runs/<timestamp>/
Output:
    logs/failures/failure_summary_<timestamp>.json  (relative to CWD)
    Also prints the output path to stdout.
"""

import sys
import json
import os
from collections import defaultdict

DIMENSIONS = [
    "field_completeness",
    "information_loss",
    "boundary_accuracy",
    "speaker_attribution",
    "verbatim_constraint",
]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/aggregate_failures.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = os.path.abspath(sys.argv[1])

    if not os.path.isdir(run_dir):
        print(f"Error: run directory does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    run_ts = os.path.basename(run_dir.rstrip("/\\"))

    # Walk run directory — collect all case subdirs that contain eval_output.json
    eval_entries = []
    try:
        entries = sorted(os.scandir(run_dir), key=lambda e: e.name)
    except PermissionError as exc:
        print(f"Error: cannot read run directory: {exc}", file=sys.stderr)
        sys.exit(1)

    for entry in entries:
        if not entry.is_dir():
            continue
        eval_path = os.path.join(entry.path, "eval_output.json")
        if os.path.isfile(eval_path):
            eval_entries.append((entry.name, eval_path, entry.path))

    if not eval_entries:
        print(f"Error: no eval_output.json files found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Pass 1 — read every eval_output.json, separate errors from valids   #
    # ------------------------------------------------------------------ #
    errored_cases = []
    valid_cases = []  # list of (case_id, eval_data, case_category)

    for case_id, eval_path, case_dir in eval_entries:
        try:
            with open(eval_path) as fh:
                eval_data = json.load(fh)
        except Exception as exc:
            print(f"[aggregate] {case_id} → READ_ERROR ({exc})", file=sys.stderr)
            errored_cases.append(case_id)
            continue

        if "error" in eval_data:
            errored_cases.append(case_id)
            print(
                f"[aggregate] {case_id} → ERROR ({str(eval_data['error'])[:60]})",
                file=sys.stderr,
            )
            continue

        # Read sibling parse_output.json for case_category
        parse_path = os.path.join(case_dir, "parse_output.json")
        case_category = "Unknown"
        if os.path.isfile(parse_path):
            try:
                with open(parse_path) as fh:
                    parse_data = json.load(fh)
                case_category = parse_data.get("case_category") or "Unknown"
            except Exception:
                pass

        verdict = eval_data.get("verdict", "UNKNOWN")
        failures = eval_data.get("failures", [])
        failure_types = [f["error_type"] for f in failures if f.get("error_type")]

        if failure_types:
            print(
                f"[aggregate] {case_id} → {verdict} ({', '.join(failure_types)})",
                file=sys.stderr,
            )
        else:
            print(f"[aggregate] {case_id} → {verdict}", file=sys.stderr)

        valid_cases.append((case_id, eval_data, case_category))

    # ------------------------------------------------------------------ #
    # Pass 2 — aggregate                                                   #
    # ------------------------------------------------------------------ #
    n_evaluated = len(valid_cases)
    n_errored = len(errored_cases)

    if n_evaluated == 0:
        pass_rate = None
    else:
        n_pass = sum(1 for _, d, _ in valid_cases if d.get("verdict") == "PASS")
        pass_rate = round(n_pass / n_evaluated, 4)

    # --- failure_patterns ---
    error_type_counts: dict[str, int] = defaultdict(int)
    error_type_fields: dict[str, set] = defaultdict(set)
    error_type_cases: dict[str, list] = defaultdict(list)
    # best example: keyed by error_type → {"example": str, "detail": str}
    error_type_best: dict[str, dict] = {}

    for case_id, eval_data, _ in valid_cases:
        for failure in eval_data.get("failures", []):
            et = failure.get("error_type", "UNKNOWN")
            error_type_counts[et] += 1

            if failure.get("field"):
                error_type_fields[et].add(failure["field"])

            if case_id not in error_type_cases[et]:
                error_type_cases[et].append(case_id)

            example = failure.get("example") or ""
            if example:
                current_best = error_type_best.get(et, {}).get("example", "")
                if len(example) > len(current_best):
                    error_type_best[et] = {
                        "example": example,
                        "detail": failure.get("detail", ""),
                    }

    # Build failure_patterns sorted by frequency descending
    failure_patterns = []
    for et, count in sorted(error_type_counts.items(), key=lambda x: -x[1]):
        best = error_type_best.get(et, {})
        failure_patterns.append(
            {
                "error_type": et,
                "frequency": count,
                "affected_fields": sorted(error_type_fields[et]),
                "example_cases": error_type_cases[et],
                "example_detail": best.get("example", ""),
            }
        )

    # --- dimension_pass_rates ---
    if n_evaluated > 0:
        dim_pass_counts: dict[str, int] = defaultdict(int)
        for _, eval_data, _ in valid_cases:
            checks = eval_data.get("checks", {})
            for dim in DIMENSIONS:
                if checks.get(dim) == "PASS":
                    dim_pass_counts[dim] += 1

        dimension_pass_rates = {
            dim: round(dim_pass_counts[dim] / n_evaluated, 4) for dim in DIMENSIONS
        }
        worst_dimension = min(dimension_pass_rates, key=lambda d: dimension_pass_rates[d])
    else:
        dimension_pass_rates = {dim: None for dim in DIMENSIONS}
        worst_dimension = None

    # --- worst_category ---
    category_stats: dict[str, list] = defaultdict(lambda: [0, 0])  # [passes, total]
    for _, eval_data, cat in valid_cases:
        category_stats[cat][1] += 1
        if eval_data.get("verdict") == "PASS":
            category_stats[cat][0] += 1

    worst_category = "Unknown"
    if category_stats:

        def _cat_pass_rate(item):
            passes, total = item[1]
            return passes / total if total > 0 else 1.0

        worst_category = min(category_stats.items(), key=_cat_pass_rate)[0]

    # --- improvement_hints (deduped, insertion-order) ---
    seen_hints: set = set()
    improvement_hints = []
    for _, eval_data, _ in valid_cases:
        for hint in eval_data.get("improvement_hints", []):
            if hint and hint not in seen_hints:
                seen_hints.add(hint)
                improvement_hints.append(hint)

    # --- improvement_priority ---
    improvement_priority = [
        et for et, _ in sorted(error_type_counts.items(), key=lambda x: -x[1])
    ]

    # ------------------------------------------------------------------ #
    # Build output document                                                #
    # ------------------------------------------------------------------ #
    output = {
        "run_dir": run_dir,
        "run_ts": run_ts,
        "cases_evaluated": n_evaluated,
        "cases_errored": n_errored,
        "pass_rate": pass_rate,
        "failure_patterns": failure_patterns,
        "dimension_pass_rates": dimension_pass_rates,
        "worst_dimension": worst_dimension,
        "worst_category": worst_category,
        "improvement_hints": improvement_hints,
        "improvement_priority": improvement_priority,
        "errored_cases": errored_cases,
    }

    # Write to logs/failures/ relative to CWD
    output_dir = os.path.join(os.getcwd(), "logs", "failures")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"failure_summary_{run_ts}.json")

    with open(output_path, "w") as fh:
        json.dump(output, fh, indent=2)

    # Print output path to stdout (single line, machine-readable)
    print(output_path)


if __name__ == "__main__":
    main()
