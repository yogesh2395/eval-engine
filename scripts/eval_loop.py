#!/usr/bin/env python3
"""
eval_loop.py — runs the full parse→eval pipeline on a manifest of training cases.

CLI:
    python3 scripts/eval_loop.py [--n N] [--seed SEED]
    python3 scripts/eval_loop.py --manifest path/to/manifest.json

For each case:
  a. detect_format.py  (subprocess) → logs/runs/<ts>/<case_id>/format_detection.json
  b. preprocess_input.py (subprocess) → logs/runs/<ts>/<case_id>/preprocessed.txt
  c. parse_transcript.parse() (direct import) → logs/runs/<ts>/<case_id>/parse_output.json
  d. parser-evaluator (Anthropic API, sonnet) → logs/runs/<ts>/<case_id>/eval_output.json

Writes logs/runs/<ts>/summary.json and prints a one-line summary to stdout.
Never reads from examples/testing_set/.

Requires ANTHROPIC_API_KEY in the shell environment.
"""

import sys
import os
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
AGENT_FILE         = REPO_ROOT / ".claude" / "agents" / "parser-evaluator.md"
PARSER_AGENT_FILE  = REPO_ROOT / ".claude" / "agents" / "transcript-parser.md"
PARSER_MODEL       = "claude-haiku-4-5-20251001"
LOGS_DIR    = REPO_ROOT / "logs" / "runs"

# ── extend sys.path (same pattern as parse_transcript.py) ─────────────────
_pip_deps = str(REPO_ROOT / ".pip_deps")
if _pip_deps not in sys.path:
    sys.path.insert(0, _pip_deps)


# ── evaluator helpers ──────────────────────────────────────────────────────

def _load_evaluator_prompt() -> str:
    """Read parser-evaluator.md; strip YAML frontmatter (between first two ---)."""
    with open(AGENT_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break

    return "\n".join(lines).strip()


def _call_evaluator(parse_output: dict, case_path: str, api_key: str) -> dict:
    """
    Call parser-evaluator via Anthropic API (claude-sonnet-4-6).
    Returns the parsed JSON dict or {"error": "..."}.
    """
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not found in .pip_deps"}

    system_prompt = _load_evaluator_prompt()
    client = anthropic.Anthropic(api_key=api_key)

    user_msg = (
        "Evaluate this parser output.\n\n"
        f"Original case file path: {case_path}\n\n"
        f"Parser output:\n{json.dumps(parse_output, indent=2)}"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as exc:
        return {"error": f"API call failed: {exc}"}

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"error": f"JSON parse failed: {exc}", "raw": raw[:500]}


# ── parser helpers ────────────────────────────────────────────────────────

def _load_parser_prompt() -> str:
    """Read transcript-parser.md; strip YAML frontmatter (between first two ---)."""
    with open(PARSER_AGENT_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break

    return "\n".join(lines).strip()


def _call_parser(case_path: str, api_key: str) -> dict:
    """
    Call transcript-parser agent via Anthropic API (haiku).
    Reads case file, uses transcript-parser.md as system prompt.
    Returns the parsed JSON dict or {"error": "..."}.
    """
    try:
        with open(case_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as exc:
        return {"error": f"File read failed: {exc}", "path": case_path}

    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not found in .pip_deps"}

    t0 = time.time()
    system_prompt = _load_parser_prompt()
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=PARSER_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"Parse this case interview file.\n\nFile: {case_path}\n\n{content}",
            }],
        )
    except Exception as exc:
        return {"error": f"API call failed: {exc}"}

    latency_ms = int((time.time() - t0) * 1000)
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"error": f"JSON parse failed: {exc}", "raw": raw[:500], "latency_ms": latency_ms}

    result["_parser_meta"] = {
        "latency_ms": latency_ms,
        "model": PARSER_MODEL,
        "agent_file": str(PARSER_AGENT_FILE),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "file": case_path,
    }
    print(
        f"[parser] {latency_ms}ms | in={response.usage.input_tokens} out={response.usage.output_tokens}",
        file=sys.stderr,
    )
    return result


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
    parser.add_argument("--n",        type=int,  default=15,   help="Cases to sample (default: 15)")
    parser.add_argument("--seed",     type=int,  default=42,   help="Random seed (default: 42)")
    parser.add_argument("--manifest", type=str,  default=None, help="Path to pre-built manifest JSON")
    args = parser.parse_args()

    # ── API key check ──────────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(
            "[eval_loop] ERROR: ANTHROPIC_API_KEY not set. "
            "Export it before running (never write to disk).",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── load manifest ──────────────────────────────────────────────────────
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        import case_manifest as cm
        all_cases = cm.build_all_cases()
        manifest = cm.stratified_sample(all_cases, args.n, args.seed)

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

        # (c) parse via transcript-parser.md agent (haiku)
        parse_result = _call_parser(case_path, api_key)

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

        # (d) parser-evaluator
        eval_result = _call_evaluator(parse_result, case_path, api_key)
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
