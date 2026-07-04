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

Re-run baseline (run 20260629_170243): information_loss = 0.5 (1/2 cases). c35 errored.

### 3. Parser-fixer loop — iteration 2 complete (2026-06-30) — **STOP-RULE MET**

Failure source: `logs/failures/failure_summary_20260629_170243.json` (c69 INFO_LOSS focus).
3 patches applied to `.claude/agents/transcript-parser.md`:
- `confirmed_case_facts` include: add stated client objective/strategic goal (covers "maximize economic worth" miss)
- `confirmed_case_facts` exclude clarification: short datum (e.g., "5 years") is NOT a bare confirmation
- Speaker attribution tiebreaker: 1–4 word response after candidate question → attribute to interviewer

Re-run (run 20260630_003738) — same manifest (c03, c35, c69):

| Dimension | Baseline (0629_170243) | Iteration 2 (0630_003738) | Delta |
|---|---|---|---|
| information_loss | 0.50 (1/2) | **1.00** (3/3) | +50pp |
| speaker_attribution | 0.50 (1/2) | **1.00** (3/3) | +50pp |
| boundary_accuracy | 1.00 (2/2) | 0.67 (2/3) | -33pp (c35 FLAG) |
| field_completeness | 1.00 | 1.00 | 0 |
| verbatim_constraint | 1.00 | 1.00 | 0 |

Stop-rule check: information_loss = 1.0 ≥ 0.8 ✓ | hard errors (FAIL) = 0 ✓ → **LOOP CLOSED**

Remaining open signals (not blocking, queue for future iteration if loop re-opens):
- c35 BOUNDARY_ERROR: interviewer question leaks into `final_recommendation` when no explicit closing signal found
- c69 INFO_LOSS (FLAG, 6.7%): reordered/duplicated block at top of source file; unique exchange not in `full_transcript`
- c35 INFO_LOSS (FLAG, 6.7%): trailing "Financial Feasibility Recommendations" block (PDF artifact) not captured
Failure summary: `logs/failures/failure_summary_20260630_003738.json`

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

## Session: Priority 2-4 + Process Enforcement (2026-06-30)

### What we built
Priority 2-4 from TODO.md: pre-merge gate, security-sweep agent, agents directory split.
Three post-commit corrections surfaced by orchestrator review.

### Agent tier classification — final canonical definition
Established by error-and-correction during this session. The correct criterion:

| Tier | Criterion | Agents |
|---|---|---|
| `specialist/` | Domain-specific to *this* eval engine — encodes rubric, gate, or extraction pipeline | pre-qualifier, post-scorer, transcript-parser, parser-evaluator, parser-fixer |
| `generalist/` | General-purpose — reusable in any software project | researcher, validator, committer, process-monitor |
| `dev/` | Dev-workflow tools — gate, scaffold, implement; not on production eval path | coder, test-writer, security-sweep |

**Error made:** pre-qualifier and post-scorer initially placed in `generalist/`. Caught by orchestrator — they encode this engine's 8-dimension rubric and well-posedness gate, which have no meaning outside this project.

### Validator loop bypass — root cause and fix

**Root cause:** The loop in CLAUDE.md was aspirational text with no mechanical enforcement. A background session acting as both implementer and orchestrator can call `git commit` directly, skipping committer agent, validator, and all conventions.

**Fix (D-037):**
- `scripts/hooks/pre-commit`: fires on every `git commit`; blocks if logic files (.py, .sh, agent .md) are staged without `logs/validator_pass.flag`; self-skips for docs-only changes; consumes flag after success (one PASS = one commit)
- `scripts/install_hooks.sh`: installs hook per checkout (git doesn't track hooks)
- `committer.md`: requires orchestrator to paste validator PASS verdict before writing flag; explicitly bans `--no-verify`
- `CLAUDE.md` Hard rules: background sessions named as non-exempt

**Validator PASS on the fix:** All 8 criteria verified end-to-end by validator agent. Hook was confirmed to block logic commits, self-skip docs commits, and consume the flag on success.

**Remaining gap:** Hook is opt-in per checkout — `install_hooks.sh` must be run manually after clone. This is documented in D-037 Implications. No workaround available without a CI pre-receive hook (requires paid GitHub plan).

### Process gaps identified this session

Three gaps surfaced by orchestrator, all sharing the same root cause — **no mandatory end-of-session checklist:**

1. **Validator not invoked** on Priority 2-4 work (first commit). Fixed: D-037 hook.
2. **learnings.md not updated** post-commit. Fixed: added step 7 to CLAUDE.md loop.
3. **todo.md not updated** with corrections post-commit. Fixed: added step 7 to CLAUDE.md loop.

Root cause: the loop ends at "commit." No hook, no checklist fires afterwards. Convention without enforcement decays under time pressure and in background sessions.

### D-030 security thread — CLOSED
The D-030 violation (`.env` file, now deleted) spawned the security-sweep agent and pre-merge gate. Both are now built and live. The open thread from the earlier session is closed.

### Session commit log (2026-06-30)

| Change | D-entry | Files |
|---|---|---|
| Pre-merge gate script | D-034 | `scripts/pre_merge_gate.sh` |
| Security-sweep agent | D-035 | `.claude/agents/dev/security-sweep.md` |
| Agents directory split (3 tiers) | D-036 | `.claude/agents/generalist/`, `specialist/`, `dev/` |
| Reclassify security-sweep → dev | D-036 update | rename |
| Reclassify pre-qualifier, post-scorer → specialist | D-036 update | rename |
| Validator loop enforcement | D-037 | `scripts/hooks/pre-commit`, `scripts/install_hooks.sh`, `committer.md`, `CLAUDE.md` |

Tests: 227/227 passing throughout.

---

## What to Tell the Next Session

1. **Parser RL loop is CLOSED.** information_loss = 1.0, 0 hard errors across 3 cases
   (run 20260630_003738). Iteration 2 patches live in `.claude/agents/transcript-parser.md`.

2. **Two loops — do not conflate:**
   - Main eval loop: `detect_format → [A] transcript-parser → pre-qualifier → post-scorer`
   - Dev/parser loop: `eval_loop.py → transcript-parser → parser-evaluator → aggregate_failures → parser-fixer`
   Current `eval_loop.py` is the **dev loop only**.

3. **Next priority: Priority 2 — Branching + merge gate** (see TODO.md).
   Enable branch protection, write pre-merge gate script, document in decisions_tracker.md.

4. **TODO.md is the task queue.** RL loop section now complete; Priorities 2–5 are live.

5. `decisions_tracker.md` is authoritative. D-033 fully implemented.

---

## Session: Eval Engine Improvements — Units A–E (2026-07-04)

Model discipline this session (user directive): Sonnet for mechanical agent work
(coder/test-writer/committer), Opus reserved for the validator gate and the Unit E
architecture audit. See memory feedback_model_cost_optimization.

### Unit A — Scorer mechanics (D-038) — validator PASS, 237/237

**What the c03 run exposed (verified from `logs/runs/20260629_170243/c03/scorer_output.json`):**
the flat rounded `overall_score = 3` hid a stark split. Splitting the 8 dimensions:
- process_score = mean(decomposition 5, root_cause 4, materiality 5, journey 4) = **4.5**
- recommendation_score = mean(tradeoff 1, feasibility 2, evidentiary 3, calibration 3) = **2.25**
The diagnosis was excellent; the recommendation was reflexive/gameable-blind. One integer erased it.

**Aggregation mechanics (deterministic, `scripts/aggregate_score.py`):**
| method | c03 | note |
|---|---|---|
| equal_weighted (headline) | 3.375 | raw mean, binary safety cap |
| conditioner_adaptive | 2.938 | +1 weight per active conditioner (map mirrors prequal_spec); reflexive+gameable up-weight tradeoff/feasibility → falls below baseline. Weights 47/16. |
| critical_floor | 3.375 | graduated ceiling min(5, 1.5+0.75·critical_min); c03 critical_min=3 → 3.75 ceiling, no bite |
| scaled_percentile | null | stub — needs D-005 repository population |

Verified fact: conditioner_adaptive is NEUTRAL — the weight map faithfully mirrors
prequal_spec `downstream_anchor_shifts`; c03's own weak recommendation dims pull it down, not a
rigged constant. Inference: this is the more honest headline for problem-type-conditioned scoring,
but we keep equal_weighted primary until alternates are compared across ≥10 cases.

**Per-dimension justification:** `dimension_justifications` now mandatory per non-N/A dimension
(observation + verbatim quote). This closes the leak that let root_cause=4 pass unjustified in c03
(the mechanical enforcement lands in Unit B / D-039).

**Validator (Opus) verdict:** PASS on all 8 acceptance criteria, each reproduced by re-running —
including the end-to-end seam check feeding the real c03 artifact through the new aggregator.

### Unit B — Mechanical leakage checker in process-monitor (D-039) — validator PASS, 244/244

**The leak, mechanically caught (verified):** Unit A made `dimension_justifications` mandatory;
Unit B enforces it. Running `check_justification_completeness.py` on the ORIGINAL c03
`scorer_output.json` (which predates the field) exits 1 and names all 8 dimensions as missing —
proving the checker catches the exact defect (root_cause=4 unjustified) that slipped past the gate.

**Semantics:** missing = (non-N/A scored dims) − (dims with non-empty justification). Empty string
counts as missing; N/A dims excluded. Quote detection is advisory-only (never flips the verdict).

**Integration honesty (validator-confirmed):** the checker is authoritative at the process-monitor
stage — the agent reports its verdict and cannot override a mechanical FAIL. Because process-monitor
is Read-only/no-Bash, the script runs as the stage wrapper and injects the verdict (falls back to
`status: "unavailable"`). Verified fact: the runnable wrapper is documented **intent**, not built —
it depends on the main-loop integration (still a RECOMMENDED TODO). This is a real gap for the Unit E
audit, not a claim of completed wiring.

### Unit C — Parser interviewer_nudges + speaker attribution (D-040) — validator PASS, 249/249

**Root cause of the c03 false CONDITIONAL (verified from parse_output.json + prequal_output.json):**
the parser mis-attributed the INTERVIEWER question "What do you think are the possible causes for
this?" into `initial_framing` (candidate field) and dropped the interviewer directive "So you can
move on from revenue." The pre-qualifier, blind to the directive, flagged the candidate for pruning
the revenue branch "before it was data-justified" — but it was the interviewer who directed the move.

**Fix:** (1) Step 0 speaker-attribution pass runs first; candidate-only fields exclude all interviewer
turns. (2) New `interviewer_nudges` field captures interviewer redirections + questions (distinct from
`confirmed_case_facts` data reveals). (3) Pre-qualifier consumes nudges: interviewer-directed pruning
is not a candidate defect.

**Neutrality discipline (validator-verified, the highest-risk point):** the exemption is scoped to
"do not raise CONDITIONAL *on that basis*" — it is NOT "nudge present ⇒ auto-PASS." Other CONDITIONAL
causes (undeclared "ignore reinsurance" constraint, missing decision horizon) are explicitly
unaffected. So c03 would correctly shed the FALSE component while the legitimate CONDITIONAL causes
(reinsurance/horizon) still stand — the gate is corrected, not weakened.

**Verified vs inferred:** Verified — schema/rule text present in all three files, seam coherent, 249
tests green. Inferred — the actual re-run gate outcome (CONDITIONAL-for-right-reason vs PASS) can only
be confirmed once the nudge hand-off is wired into a runnable pipeline (still a RECOMMENDED TODO); this
unit changes agent/spec contracts, not the runner.
