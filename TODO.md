# TODO — eval-engine

> Authoritative task queue. Update on completion. Architecture decisions live in
> `decisions_tracker.md`. Run history and empirical findings live in `learnings.md`.

---

## NOW (current session)

- [x] D-033: `--max-cases 3` default + `--confirm-full-run` guard in `eval_loop.py`
- [x] Parser RL loop iteration 1: `confirmed_case_facts` field, stop-signal patches, pronoun ban
- [x] Fix `_extract_json` lone-backslash bug (c35 Petrochemical class)
- [x] Run full main pipeline for ≥1 case and print outputs at each stage:
      `transcript-parser → pre-qualifier → post-scorer → final JSON`
      c03 (Auto Insurance, BFSI): overall_score=3, gate=CONDITIONAL, 227/227 tests pass

---

## Parser RL loop iteration 2 — CLOSED ✓ (2026-06-30)

- [x] Run `aggregate_failures.py` on `logs/runs/20260629_170243/`
- [x] Feed `failure_summary_20260629_170243.json` to parser-fixer
      Focus: c69 INFO_LOSS (objective clarification miss: "maximize economic worth")
- [x] Apply fixer patch to `transcript-parser.md` (3 patches)
- [x] Re-run with SAME manifest → `logs/runs/20260630_003738/` — 3/3 completed, 0 errors
- [x] Delta: information_loss 0.50 → 1.00 (+50pp), speaker_attribution 0.50 → 1.00 (+50pp)
- [x] Stop-rule: information_loss = 1.0 ≥ 0.8 ✓ | hard FAIL = 0 ✓ → **LOOP CLOSED**

---

## AFTER RL LOOP REACHES STOP-RULE — ✓ DONE (2026-06-30)

### Priority 2 — Branching + merge gate  ✓ DONE (2026-06-30)
- [x] Enable branch protection on `main` — N/A: GitHub requires paid plan (Pro/Team) for
      branch protection on private repos. Gate script is the sole enforcement mechanism.
- [x] Write pre-merge gate script: `scripts/pre_merge_gate.sh`
      Runs pytest + security sweep + D-entry scan; exits 0 (PASS) or 1 (FAIL)
      Usage: `./scripts/pre_merge_gate.sh` or `--staged` for staged-only scan
- [x] Document gate in `decisions_tracker.md` as D-034

### Priority 3 — D-030 security-sweep agent  ✓ DONE (2026-06-30)
- [x] Design `security-sweep` agent (`.claude/agents/dev/security-sweep.md`):
      Scans staged diff for `.env`, plaintext API keys, `ANTHROPIC_API_KEY=`, hardcoded tokens
      Returns JSON PASS/BLOCK with finding at file:line. Never writes.
- [x] Add D-035 to `decisions_tracker.md`
- [x] Wire into pre-merge gate — pre_merge_gate.sh runs grep sweep; agent available ad-hoc

### Priority 4 — Split agents directory  ✓ DONE (2026-06-30)
- [x] Create `agents/generalist/`, `agents/specialist/`, `agents/dev/` under `.claude/agents/`
- [x] Generalist: researcher, validator, committer, process-monitor (general-purpose)
- [x] Specialist: transcript-parser, parser-evaluator, parser-fixer, pre-qualifier, post-scorer
      (all domain-specific to this engine — pre-qualifier/post-scorer reclassified post-review)
- [x] Dev: coder, test-writer, security-sweep (dev-workflow tools, not production eval path)
- [x] Agent references unchanged — `--agent <name>` matches frontmatter `name:` field, not path
- [x] Add D-036 to `decisions_tracker.md`

### Post-commit corrections (2026-06-30)
- [x] Reclassify security-sweep: specialist → dev (it's a dev-workflow gate, not pipeline-specific)
- [x] Reclassify pre-qualifier + post-scorer: generalist → specialist
      (user-identified: they encode this engine's rubric and gate — not general-purpose)
      Validator PASS: all 8 criteria met, 227/227 tests
- [x] Fix validator loop bypass (D-037):
      `scripts/hooks/pre-commit` — blocks logic-file commits without `logs/validator_pass.flag`
      `scripts/install_hooks.sh` — installs hook per-checkout
      `committer.md` — requires pasted PASS verdict before writing flag
      `CLAUDE.md` Hard rules — background sessions explicitly non-exempt
- [x] Fix learnings.md and todo.md not updated post-commit (process gap — no end-of-loop step)

---

## Eval Engine Improvements session (2026-07-04) — Units A–E

Source: user improvement brief (scorer output, monitor leakage check, parser nudges, persona
stubs, loop self-audit). Plan: `.claude/plans/lucky-hopping-waterfall.md`.

- [x] **Unit A — Scorer mechanics** (D-038): decimal `overall_score`; `score_breakdown`
      {process 4.5 / recommendation 2.25 on c03}; `aggregation` {equal_weighted 3.375,
      conditioner_adaptive 2.938, critical_floor 3.375, scaled_percentile stub}; mandatory
      `dimension_justifications`. Validator PASS (8/8), 237/237 tests.
- [x] **Unit B — Mechanical leakage checker in process-monitor** (D-039):
      `scripts/check_justification_completeness.py`; process-monitor `design_execution_leakage`
      section; validator justification-completeness FAIL criterion. Validator PASS (7/7); checker
      exits 1 on real c03 (all 8 dims missing), 244/244 tests. Note: runnable stage-wrapper is
      documented intent — needs main-loop wiring.
- [x] **Unit C — Parser interviewer_nudges + speaker attribution** (D-040):
      transcript-parser Step 0 attribution + `interviewer_nudges` field; pre-qualifier
      non-penalty rule for interviewer-directed pruning (scoped, other CONDITIONAL causes
      preserved). Validator PASS (7/7, incl. neutrality gate), 249/249 tests. Nudge hand-off in
      a runnable pipeline still needs main-loop wiring.
- [ ] **Unit D — Persona/ideal/meta stubs** (D-041): harsh/generous graders, persona-comparer
      (STUB, not wired); ideal-solution + dimension-sufficiency D-entries + overfitting guardrail.
- [ ] **Unit E — Loop self-audit** (D-042): CLAUDE.md audit-before-push step; `workflow_audit.md`
      session deliverable (gaps + self-fixes + ranked recs).

---

## HOLD

### Priority 5 — Model seam
- Deferred until post-scorer validates. Do not conflate dev-tooling model lane with
  product routing. Log an explicit D-entry when ready to revisit.

---

## RECOMMENDED (post-scorer validates — D-001 keystone)

- [ ] Integrate pre-qualifier + post-scorer into main `eval_loop.py` as the primary path
      Current `eval_loop.py` is a **dev/parser-quality loop**, not the main eval engine
      New path: `detect_format → [if A] transcript-parser → pre-qualifier → post-scorer`
      Current path stays as `eval_loop_dev.py` or renamed to `parser_eval_loop.py`
- [ ] Define final output schema for a scored evaluation (overall_score + dimension_scores + justification)
- [ ] Run the main eval loop on the full training set once RL loop + scorer both validate
