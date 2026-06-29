# learnings.md

> Session-transfer file. Records empirical findings from real pipeline runs,
> root causes diagnosed, and open threads. Architecture decisions live in
> decisions_tracker.md. Code history is in git log. This file captures what
> the data showed and what that means for the next session.

---

## Parser Eval: First Real Runs (2026-06-28)

### What we ran
Two batches of 7 cases each from the training set (57 cases), using stratified
random sampling. Seeds 42 and 99.

- Run A: `logs/runs/20260628_173621/` (seed=42)
- Run B: `logs/runs/20260628_173622/` (seed=99)
- Both used `claude -p --agent transcript-parser` via Pro OAuth (no credits)

A second pair of runs (seeds 42+99) was started at end of session with the
evaluator fix applied. Those run dirs are `20260628_220906` and `20260628_220908`
but may not have completed — check for `summary.json` before reading.

### What the data showed

**Reruns with fixed evaluator — 11 cases evaluated, 3 errored at parser:**

| Dimension | Run A seed=42 (6/7) | Run B seed=99 (5/7) | Signal |
|---|---|---|---|
| field_completeness | 100% | 100% | Solid |
| speaker_attribution | 100% | 80% | Mostly solid |
| verbatim_constraint | 100% | 100% | Solid |
| boundary_accuracy | 50% | 80% | Needs attention |
| **information_loss** | **0%** | **20%** | **Primary failure** |

**Failure counts across both runs (combined):**

| Error type | Count | Priority |
|---|---|---|
| INFO_LOSS | 17 | Fix first |
| BOUNDARY_ERROR | 4 | Fix second |
| SPEAKER_MISMATCH | 1 | Monitor |
| FIELD_MISSING | 1 | Monitor |

**Failure summaries on disk:**
- `logs/failures/failure_summary_20260628_220906.json` (seed=42)
- `logs/failures/failure_summary_20260628_220908.json` (seed=99)

**Consistent failure: `information_loss`**
- The parser strips interviewer data-reveal answers (quantitative targets revealed
  mid-interview: market size figures, product specs, cost percentages).
- `boundary_accuracy` is correct — the interviewer answer is correctly excluded
  from `initial_framing`. But it's also absent from `full_transcript`, meaning
  it's lost entirely.
- The evaluator's specific hint: "Add a `confirmed_case_facts` field to capture
  interviewer data-reveal answers verbatim, since current boundary rule strips
  these from initial_framing but leaves them recoverable only from full_transcript."

**Secondary failure: `verbatim_constraint`**
- Parser paraphrases in `final_recommendation` (pronoun substitution: "them" → "large dealers").
- Rule: copy original wording, append `[clarification]` only if disambiguation required,
  never substitute the original token.

**What was working well:**
- The parser reliably identifies all required fields (field_completeness = 100%).
- Boundary cuts between initial_framing and reasoning_trace are accurate.
- Speaker attribution (interviewer vs candidate) is correct.

### Root cause of evaluator silent failure (fixed)

`_call_evaluator` was embedding the full parse JSON as a `-p` argument to the
claude CLI. `full_transcript` alone can be 20K+ chars. macOS `ARG_MAX` is ~1MB
total but the claude CLI itself imposes a lower limit; the subprocess returned
exit code 1 with empty stderr.

**Fix applied (commit 345aed3):** `_call_evaluator` now receives two file paths
(`parse_output_path`, `case_path`) and passes them to the agent. The agent reads
both via its Read tool. This matches D-032 in decisions_tracker.md.

---

## Parser Fixer: Not Yet Run

The fixer agent (`parser-fixer.md`) exists but has not been invoked against real
failure data yet. The failure_summary needed for it is produced by
`aggregate_failures.py`, which requires a completed run with multiple evaluated
cases.

**Next session:** Once the rerun summaries land (20260628_220906/908), run
`python3 scripts/aggregate_failures.py logs/runs/<ts>/` and feed the
`logs/failures/failure_summary_<ts>.json` to the parser-fixer agent. The two
confirmed failure types to address are:

1. **INFO_LOSS** — add `confirmed_case_facts` field for mid-interview data reveals
2. **VERBATIM_VIOLATION** — tighten `final_recommendation` extraction rule

---

## Security / D-030 Violation (2026-06-28)

A `.env` file holding the Anthropic API key was created during early pipeline
development. This violates D-030 (Keychain-only credential storage) and is also
moot (D-031: the CLI OAuth path requires no API key). Status:
- `.env` has been deleted from disk
- `.env` is in `.gitignore` — it cannot be committed accidentally
- The security-sweep agent (Priority 2) must flag any future `.env` or plaintext
  secret at the pre-merge gate when built
- D-030 violation is closed; gate enforcement is deferred until the agent exists

---

## Open Infrastructure Threads

### 1. Evaluate all 57 training cases (not just 7)
Current batch size is 7 per run (~2.5hr wall clock at 2.5min/case). To cover
all 57 cases, need either: (a) increase batch size with parallelism, or (b) run
multiple seeds until convergence. No API cost — only Pro auth.

### 2. Parser-fixer loop — iteration 1 complete (2026-06-29)

Parser-fixer ran for the first time on combined failure summaries (seed=42 + seed=99).
4 patches applied to `.claude/agents/transcript-parser.md`:
- Schema: add `confirmed_case_facts: ["string"]` (INFO_LOSS)
- Rule: `full_transcript` ban on omitting spoken turns; `confirmed_case_facts` extraction rule (INFO_LOSS)
- Rule: `problem_statement` explicit stop-phrase signals (BOUNDARY_ERROR)
- Constraint: ban pronoun substitution (VERBATIM_VIOLATION)

Parser-evaluator updated: checks `confirmed_case_facts` in information_loss spot-check and
field_completeness. Tests: 225/225 pass.

Re-run with seed=42, `--max-cases 3` pending. Baseline information_loss pass rate = 0.0.

### 3. Worktree cleanup — CLOSED (2026-06-29)
All 4 stale worktrees removed (agent-a4feadb7ef73b89db, agent-a2aaff5c30a948f4b,
agent-aa3129cc37a2c313e, agent-acc062a6dd3897dac). Main is clean.

---

## First End-to-End Main Pipeline Run (2026-06-29)

Case: **c03 — Auto Insurance (BFSI, Moderate)**
Run dir: `logs/runs/20260629_170243/c03/`

| Stage | File | Outcome |
|---|---|---|
| transcript-parser | `parse_output.json` | PASS — 12 confirmed_case_facts |
| pre-qualifier | `prequal_output.json` | CONDITIONAL |
| post-scorer | `scorer_output.json` | overall_score = 3/5 |

Pre-qualifier CONDITIONAL: framing narrows "profitability declining" → "costs rising"
before revenue branch is data-justified. "Ignore reinsurance" constraint never surfaced.
No decision horizon. Flags: reflexive=true, gameable=true.

| Dimension | Score | Note |
|---|---|---|
| decomposition | 5 | Clean MECE tree |
| root_cause | 4 | Mechanistic: young/risky portfolio mix shift |
| materiality | 5 | Proportional pruning |
| evidentiary_grounding | 3 | Bare assertion on demographic causation |
| tradeoff_awareness | **1** | Both interventions as free wins; reflexive+gameable fully missed |
| feasibility | **2** | No preconditions in regulated market |
| journey_coherence | 4 | Consistent with framing |
| calibration | 3 | Broadly commensurate |

Unrounded mean = 3.375 → overall_score = 3. No safety-critical cap triggered.
Key signal: tradeoff_awareness=1 — structurally captured by rubric, easy to miss in manual review.

---

## Parser RL Loop — Ongoing Methodology

Periodically when the next run of aggregate_failures.py completes or is triggered,
pass onto the fixer to make further improvements. After fix-rerun to measure delta
with same seed. Close loop only with significant improvement. Significant improvement
depends on the baseline and delta. For low baseline, delta should be min 10%.
As baseline rate improves trim delta to 5% improvement gradually. This is the RL loop.

---

## Session Commit Log (2026-06-29)

| Change | Files |
|---|---|
| D-033: `--max-cases 3` default, `--confirm-full-run` guard | `scripts/eval_loop.py` |
| Parser RL loop iteration 1: 4 patches + evaluator update | `.claude/agents/transcript-parser.md`, `.claude/agents/parser-evaluator.md` |
| `_extract_json` lone-backslash repair (c35 class unblocked) | `scripts/eval_loop.py` |
| `confirmed_case_facts` added to test schema | `tests/test_parser_agents.py` |
| 2 new `_extract_json` tests | `tests/test_eval_loop.py` |
| committer.md: progress bar + session-close principle | `.claude/agents/committer.md` |
| TODO.md created | `TODO.md` |

Tests: 227/227 passing.

---

## What to Tell the Next Session

1. **Main pipeline is end-to-end verified.** transcript-parser → pre-qualifier →
   post-scorer ran on c03. Persistent outputs in `logs/runs/20260629_170243/c03/`.

2. **Two loops — do not conflate:**
   - Main eval loop: `detect_format → [A] transcript-parser → pre-qualifier → post-scorer`
   - Dev/parser loop: `eval_loop.py → transcript-parser → parser-evaluator → aggregate_failures → parser-fixer`
   Current `eval_loop.py` is the **dev loop only**.

3. **Parser RL loop iteration 2:** feed `logs/failures/failure_summary_20260629_170243.json`
   to parser-fixer (focus: c69 INFO_LOSS). Re-run `--manifest logs/runs/20260629_170243/manifest.json`
   for apples-to-apples delta. Stop-rule: information_loss >= 0.8 with 0 hard errors.

4. **TODO.md is the task queue.** Priorities 2-5 start after RL loop reaches stop-rule.

5. `decisions_tracker.md` is authoritative. D-033 now fully implemented.
