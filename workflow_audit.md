# Workflow Audit — Compounding-Loop Self-Inspection

> Mandatory Unit-E deliverable (CLAUDE.md loop step 8). Audits the loop/architecture as it
> actually ran, names gaps, records in-session self-fixes, and ranks recommendations. Written
> from first-hand observation of this session's five-unit execution. Confidence discipline
> (D-024): **[verified]** = observed/ran it; **[inferred]** = judgment from artifacts.

---

## Method

Audited the loop as executed across Units A–E (2026-07-04): each unit ran
implement (Sonnet coder) → validator (Opus, except Sonnet for the docs-only Unit D) →
knowledge-base update → committer (Sonnet) → push. Four logic-file commits (509f057, 43c5260,
0e08781, 42a3c9a) each passed the pre-commit validator-flag gate.

---

## What the loop did well [verified this session]

1. **The validator gate held four times, mechanically.** Every logic-file commit produced the
   pre-commit hook line `validator sign-off confirmed — proceeding with commit` and consumed the
   flag; no `--no-verify`, no bypass. D-037 enforcement works in a background session.
2. **The Opus validator re-ran rather than rubber-stamped.** It independently reproduced the c03
   aggregation numbers (3.375 / 2.938 / 4.5 / 2.25), the leakage-checker exit codes (1 on the real
   c03 output naming all 8 dims), and cross-checked the WEIGHT_MAP against prequal_spec — catching
   substance, not vibes.
3. **Deterministic mechanical checks are the compounding asset.** `aggregate_score.py` and
   `check_justification_completeness.py` convert judgment gates into reproducible ones. Each such
   script permanently shrinks what the validator must adjudicate by hand — this is the core
   compounding mechanism working as intended.
4. **Model-cost discipline held.** Sonnet did all coder/committer/docs-validator work; Opus was
   spent only on the four scoring-logic validator passes and this audit. Concentrated the scarce
   resource where a false PASS is worst (D-026).
5. **Records discipline was continuous** (D-038…D-042 + TODO + learnings per unit), not deferred to
   session end.

---

## Gaps observed, ranked by impact on compounding

### G1 — Un-runnable design debt: the main pipeline is still not integrated [verified] — HIGHEST
Units B and C added agent/spec **contracts** whose runtime effect cannot be exercised end-to-end,
because `eval_loop.py` remains the dev/parser-quality loop, not the main
`detect_format → transcript-parser → pre-qualifier → post-scorer` path. Three units now carry an
explicit "needs main-loop wiring" caveat (B's stage-wrapper that injects the leakage verdict; C's
parser→pre-qualifier nudge hand-off; A's scorer runs only via the agent, not a wired stage). Every
unit that adds a contract without a runner widens the gap between *designed* and *runnable*. This is
the single biggest brake on compounding.

### G2 — Runtime behavior verified by spec+tests+math, NOT by execution [verified gap; D-024]
The plan's "live checks" (re-run post-scorer / transcript-parser / process-monitor on c03 via the
claude CLI, ~2.5 min each) were **not run** this session. **[verified]** the aggregation math, the
checker semantics, and the spec/rule text (scripts + 249 tests + validator re-runs).
**[inferred, not observed]** that the *agents* now actually emit `dimension_justifications`, exclude
interviewer turns, and produce `interviewer_nudges` at runtime — that is implied by the updated
prompts but was not executed. Honest confidence boundary: unit A–C behavioral claims are
spec-verified, not run-verified.

### G3 — No PR / merge path from the loop [verified]
`gh` is absent from this environment, so the branch is pushed but no draft PR exists; the loop had
no fallback beyond surfacing the GitHub create-PR URL. Combined with D-034 (branch protection needs
a paid plan), there is no automated merge-to-main path — a human must open and merge the PR.

### G4 — Per-checkout hook install was worktree-broken [verified] — FIXED this session (see below)

### G5 — Cold-subagent context re-derivation [verified cost, accepted]
Each coder/validator/committer spawned cold and re-read the same files — a real token cost. But
re-using a warm context for validation would compromise the fresh-eyes neutrality the gate depends
on (D-026). Treat as the deliberate price of validator neutrality, mitigated by precise prompts, not
a defect to "fix" by context reuse.

### G6 — Stub agents are `model: opus` and unwired [inferred low risk]
If harsh-grader / generous-grader / persona-comparer were ever invoked by accident they would spend
Opus. Mitigated by the double STUB banner and zero pipeline references (validator-confirmed), but a
latent footgun until wiring criteria are defined.

---

## Self-fixes applied in-session

- **G4 fixed [verified]:** `scripts/install_hooks.sh` now resolves the shared hooks dir via
  `git rev-parse --git-common-dir`, so it installs correctly from a worktree (where `.git` is a
  file). Ran it from this worktree: exit 0, installed to the shared `.git/hooks/pre-commit`.
- **Loop formalized:** CLAUDE.md loop gains step 7 (pre-push knowledge-base update incl. CLAUDE.md
  itself) and step 8 (pre-push workflow self-audit) — this file is that step's output.
- **Frontmatter staleness fixed (Unit C):** transcript-parser description no longer claims "five
  clean artifacts" after `interviewer_nudges` was added.

---

## Ranked recommendations (feed the RECOMMENDED / HOLD queues)

1. **Integrate the main eval loop** (`detect_format → transcript-parser → pre-qualifier →
   post-scorer`, renaming the current loop to `parser_eval_loop.py`). Unblocks G1 and enables
   run-verification of Units A–C. Highest leverage — do first.
2. **Build the runnable process-monitor stage wrapper** that invokes
   `check_justification_completeness.py` and injects `design_execution_leakage`. Turns D-039 from
   documented intent into executed behavior.
3. **Wire the parser→pre-qualifier nudge hand-off**, then re-run c03 to confirm the CONDITIONAL
   corrects to "right-reason only" (reinsurance/horizon), closing the G2 gap for D-040.
4. **Add a golden-output regression harness**: snapshot expected agent outputs for c03 (and 1–2
   more cases) so agent-behavior changes become execution-verified, not just spec/test-verified.
   Directly retires G2 as a class.
5. **PR fallback**: have the committer emit the create-PR URL prominently and document the
   `gh`-install / manual-merge path (G3). Cheap.
6. **Accrete the repository (D-005)** enough to activate `scaled_percentile` aggregation and to make
   `conditioner_adaptive` vs `equal_weighted` comparison empirical across ≥10 cases (ties to D-041's
   threshold and the dimension-sufficiency meta-check).

---

## Compounding scorecard

| Signal | Direction | Evidence |
|---|---|---|
| Mechanical gates replacing judgment gates | **+** | 2 new deterministic checkers this session |
| Records/decision accretion | **+** | D-038…D-042, continuous |
| Design→runnable gap | **–** | G1: 3 units await main-loop wiring |
| Execution-verified behavior | **–** | G2: agent runtime unrun this session |
| Enforcement robustness | **+** | hook held 4×; install now worktree-safe |

Net: the loop compounds on the *verification-asset* axis (deterministic checks, records) but is
accruing *un-runnable design debt* (G1/G2). The top recommendation — integrate the main loop — is
the lever that converts the accumulated contracts into runnable, self-verifying behavior.
