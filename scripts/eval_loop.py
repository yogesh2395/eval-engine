#!/usr/bin/env python3
"""
eval_loop.py — runs the full parse→eval pipeline on a manifest of training cases.

CLI:
    python3 scripts/eval_loop.py [--max-cases N] [--seed SEED]
    python3 scripts/eval_loop.py --manifest path/to/manifest.json
    python3 scripts/eval_loop.py --confirm-full-run   # runs all training cases (D-033)

For each case:
  a. detect_format.py  (subprocess) → logs/runs/<ts>/<case_id>/format_detection.json
  b. preprocess_input.py (subprocess) → logs/runs/<ts>/<case_id>/preprocessed.txt
  c. transcript-parser agent (claude CLI) → logs/runs/<ts>/<case_id>/parse_output.json
  d. parser-evaluator agent (claude CLI) → logs/runs/<ts>/<case_id>/eval_output.json

Writes logs/runs/<ts>/summary.json and prints a one-line summary to stdout.
Never reads from examples/testing_set/.

Uses the `claude` CLI (Pro auth) — no ANTHROPIC_API_KEY required.
"""

import sys
import os
import re
import json
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime

# ── repo paths ─────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
TESTING_DIR = REPO_ROOT / "examples" / "testing_set"
LOGS_DIR    = REPO_ROOT / "logs" / "runs"


# ── shared JSON extraction ─────────────────────────────────────────────────

def _repair_backslashes(s: str) -> str:
    """Escape lone backslashes that are not part of a valid JSON escape sequence."""
    return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)


def _extract_json(raw: str) -> dict:
    """Extract JSON object from agent output, tolerating leading/trailing text."""
    # Strip accidental markdown code fence
    if "```" in raw:
        start = raw.find("```") + 3
        # skip optional language tag on same line
        if "\n" in raw[start:]:
            start = raw.index("\n", start) + 1
        end = raw.rfind("```")
        raw = raw[start:end].strip()

    # Try direct parse first (agent followed instructions exactly)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Repair lone backslashes (agent emitted verbatim source chars, e.g. chemical formulas)
    repaired = _repair_backslashes(raw)
    if repaired != raw:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # Fall back: find outermost { ... } in case there is preamble/postamble text
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        chunk = raw[start : end + 1]
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            pass
        # Last attempt: repair backslashes in the extracted chunk
        try:
            return json.loads(_repair_backslashes(chunk))
        except json.JSONDecodeError as exc:
            return {"error": f"JSON parse failed: {exc}", "raw": raw[:500]}

    return {"error": "No JSON object found in agent output", "raw": raw[:500]}


# ── parser helpers ────────────────────────────────────────────────────────

def _call_parser(case_path: str) -> dict:
    """
    Call transcript-parser agent via the claude CLI.
    Returns the parsed JSON dict or {"error": "..."}.
    """
    t0 = time.time()
    result = subprocess.run(
        [
            "claude",
            "-p", f"Parse this case interview file: {case_path}",
            "--agent", "transcript-parser",
            "--output-format", "text",
            "--dangerously-skip-permissions",
            "--no-session-persistence",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    latency_ms = int((time.time() - t0) * 1000)

    if result.returncode != 0:
        return {"error": f"agent failed: {result.stderr[:200]}"}

    raw = result.stdout.strip()
    parsed = _extract_json(raw)
    if "error" in parsed:
        return parsed

    parsed["_parser_meta"] = {
        "agent": "transcript-parser",
        "latency_ms": latency_ms,
        "file": case_path,
    }
    print(f"[parser] {latency_ms}ms", file=sys.stderr)
    return parsed


# ── evaluator helpers ──────────────────────────────────────────────────────

def _call_evaluator(parse_output_path: str, case_path: str) -> dict:
    """
    Call parser-evaluator agent via the claude CLI.
    Passes file paths so the agent uses its Read tool — avoids large CLI args.
    Returns the parsed JSON dict or {"error": "..."}.
    """
    user_msg = (
        f"Evaluate the parser output.\n\n"
        f"Parse output file: {parse_output_path}\n"
        f"Original case file: {case_path}"
    )
    result = subprocess.run(
        [
            "claude",
            "-p", user_msg,
            "--agent", "parser-evaluator",
            "--output-format", "text",
            "--dangerously-skip-permissions",
            "--no-session-persistence",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    if result.returncode != 0:
        return {"error": f"agent failed: {result.stderr[:200]}"}

    return _extract_json(result.stdout.strip())


# ── subprocess wrappers ────────────────────────────────────────────────────

def _run_detect_format(case_path: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "detect_format.py"), case_path],
        capture_output=True, text=True,
    )
    try:
        return json.loads(result.stdout)
    except Exception as exc:
        return {
            "error": f"detect_format subprocess failed: {exc}",
            "stdout": result.stdout[:300],
            "stderr": result.stderr[:300],
        }


def _run_preprocess(case_path: str, output_path: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "preprocess_input.py"), case_path, output_path],
        capture_output=True, text=True,
    )
    try:
        return json.loads(result.stdout)
    except Exception as exc:
        return {
            "error": f"preprocess subprocess failed: {exc}",
            "stdout": result.stdout[:300],
            "stderr": result.stderr[:300],
        }


# ── summary helpers ────────────────────────────────────────────────────────

def _compute_dimension_pass_rates(eval_outputs):
    """PASS = 1.0, FLAG/FAIL = 0.0 per check. Returns dict[str, float|None]."""
    dimensions = [
        "field_completeness",
        "information_loss",
        "boundary_accuracy",
        "speaker_attribution",
        "verbatim_constraint",
    ]
    counts = {d: {"pass": 0, "total": 0} for d in dimensions}

    for ev in eval_outputs:
        checks = ev.get("checks", {})
        for dim in dimensions:
            if dim in checks:
                counts[dim]["total"] += 1
                if checks[dim] == "PASS":
                    counts[dim]["pass"] += 1

    rates = {}
    for dim in dimensions:
        total = counts[dim]["total"]
        rates[dim] = round(counts[dim]["pass"] / total, 2) if total > 0 else None
    return rates


def _worst_dimension(rates):
    worst_dim = None
    worst_rate = 1.1
    for dim, rate in rates.items():
        if rate is not None and rate < worst_rate:
            worst_rate = rate
            worst_dim = dim
    return worst_dim


# ── guard ──────────────────────────────────────────────────────────────────

def _check_no_testing_set(manifest: list[dict]) -> None:
    testing_str = str(TESTING_DIR.resolve())
    for case in manifest:
        p = case["path"]
        abs_p = (
            str((REPO_ROOT / p).resolve())
            if not Path(p).is_absolute()
            else str(Path(p).resolve())
        )
        if abs_p.startswith(testing_str):
            print(
                f"[eval_loop] ERROR: manifest contains testing_set path: {p}",
                file=sys.stderr,
            )
            sys.exit(1)


# ── main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Eval loop: parse + evaluate a manifest of training cases"
    )
    parser.add_argument("--max-cases",       type=int,  default=3,
                        help="Cases to sample per run (default: 3). D-033.")
    parser.add_argument("--seed",            type=int,  default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--manifest",        type=str,  default=None,
                        help="Path to pre-built manifest JSON")
    parser.add_argument("--confirm-full-run", action="store_true",
                        help="Run the full training set, bypassing --max-cases. "
                             "Requires explicit orchestrator authorization. D-033.")
    args = parser.parse_args()

    # ── D-033 guard — no unbounded run without explicit opt-in ────────────
    # ── load manifest ──────────────────────────────────────────────────────
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if not args.confirm_full_run and len(manifest) > args.max_cases:
            print(
                f"[eval_loop] ERROR: manifest has {len(manifest)} cases but "
                f"--max-cases is {args.max_cases}. "
                f"Pass --confirm-full-run to proceed. (D-033)",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        import case_manifest as cm
        all_cases = cm.build_all_cases()
        n_to_sample = len(all_cases) if args.confirm_full_run else args.max_cases
        manifest = cm.stratified_sample(all_cases, n_to_sample, args.seed)

    _check_no_testing_set(manifest)

    # ── create run directory ───────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOGS_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # ── per-case pipeline ──────────────────────────────────────────────────
    eval_outputs = []     # non-error eval results (have a verdict)
    errored_cases = []    # case_ids that hit an unrecoverable error

    for case in manifest:
        case_id   = case["case_id"]
        raw_path  = case["path"]
        case_path = (
            str((REPO_ROOT / raw_path).resolve())
            if not Path(raw_path).is_absolute()
            else raw_path
        )

        case_dir = run_dir / case_id
        case_dir.mkdir(exist_ok=True)

        # (a) detect_format
        fmt_result = _run_detect_format(case_path)
        (case_dir / "format_detection.json").write_text(json.dumps(fmt_result, indent=2))

        # (b) preprocess
        preprocessed_path = str(case_dir / "preprocessed.txt")
        pre_result = _run_preprocess(case_path, preprocessed_path)
        if "error" in pre_result:
            # Write an empty stub so downstream artifacts aren't missing
            Path(preprocessed_path).write_text("", encoding="utf-8")

        # (c) parse via transcript-parser agent (claude CLI)
        parse_result = _call_parser(case_path)

        (case_dir / "parse_output.json").write_text(json.dumps(parse_result, indent=2))

        if "error" in parse_result:
            eval_result = {"error": "parse failed — eval skipped", "case_id": case_id}
            (case_dir / "eval_output.json").write_text(json.dumps(eval_result, indent=2))
            errored_cases.append(case_id)
            print(
                f"[eval_loop] {case_id} → ERROR ({str(parse_result['error'])[:60]})",
                file=sys.stderr,
            )
            continue

        # (d) parser-evaluator agent — pass file paths, agent uses Read tool
        parse_output_path = str(case_dir / "parse_output.json")
        eval_result = _call_evaluator(parse_output_path, case_path)
        (case_dir / "eval_output.json").write_text(json.dumps(eval_result, indent=2))

        if "error" in eval_result:
            errored_cases.append(case_id)
            print(
                f"[eval_loop] {case_id} → ERROR ({str(eval_result['error'])[:60]})",
                file=sys.stderr,
            )
        else:
            eval_outputs.append(eval_result)
            verdict = eval_result.get("verdict", "UNKNOWN")
            score   = eval_result.get("quality_score", 0.0)
            print(f"[eval_loop] {case_id} → {verdict} ({score:.2f})", file=sys.stderr)

    # ── summary ────────────────────────────────────────────────────────────
    pass_count = sum(1 for e in eval_outputs if e.get("verdict") == "PASS")
    flag_count = sum(1 for e in eval_outputs if e.get("verdict") == "FLAG")
    fail_count = sum(1 for e in eval_outputs if e.get("verdict") == "FAIL")

    failure_type_counts = {}
    for ev in eval_outputs:
        for failure in ev.get("failures", []):
            et = failure.get("error_type", "UNKNOWN")
            failure_type_counts[et] = failure_type_counts.get(et, 0) + 1

    dim_rates   = _compute_dimension_pass_rates(eval_outputs)
    worst_dim   = _worst_dimension(dim_rates)

    cases_attempted = len(manifest)
    cases_errored   = len(errored_cases)
    cases_completed = cases_attempted - cases_errored

    total_judged = len(eval_outputs)
    pass_rate    = round(pass_count / total_judged, 2) if total_judged > 0 else 0.0

    summary = {
        "run_ts":               ts,
        "cases_attempted":      cases_attempted,
        "cases_completed":      cases_completed,
        "cases_errored":        cases_errored,
        "pass_count":           pass_count,
        "flag_count":           flag_count,
        "fail_count":           fail_count,
        "pass_rate":            pass_rate,
        "failure_type_counts":  failure_type_counts,
        "dimension_pass_rates": dim_rates,
        "worst_dimension":      worst_dim,
        "errored_cases":        errored_cases,
    }

    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    # ── stdout print ───────────────────────────────────────────────────────
    fail_types_str = "  ".join(f"{k}×{v}" for k, v in failure_type_counts.items()) or "none"
    print(
        f"Run: {ts}  Cases: {cases_attempted}  "
        f"Pass: {pass_count}  Flag: {flag_count}  Fail: {fail_count}"
    )
    print(f"Failure types: {fail_types_str}")
    if worst_dim:
        worst_rate_pct = int((dim_rates.get(worst_dim) or 0.0) * 100)
        print(f"Worst dimension: {worst_dim} ({worst_rate_pct}% pass)")
    else:
        print("Worst dimension: N/A")


if __name__ == "__main__":
    main()
