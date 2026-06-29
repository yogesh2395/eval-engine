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

## NEXT SESSION — Parser RL loop iteration 2

- [ ] Run `aggregate_failures.py` on `logs/runs/20260629_170243/`  ← already done, file exists
- [ ] Feed `failure_summary_20260629_170243.json` to parser-fixer
      Focus: c69 INFO_LOSS (objective clarification miss: "maximize economic worth")
- [ ] Apply fixer patch to `transcript-parser.md`
- [ ] Re-run with SAME manifest (`--manifest logs/runs/20260629_170243/manifest.json`)
      for apples-to-apples delta vs. this run's baseline
- [ ] Compute delta: need ≥10% improvement (low baseline) to close iteration 2
- [ ] Stop-rule: information_loss ≥ 0.8 with 0 hard errors → loop done

---

## AFTER RL LOOP REACHES STOP-RULE

### Priority 2 — Branching + merge gate
- [ ] Enable branch protection on `main` (no direct push, require PR)
- [ ] Write pre-merge gate script: runs `pytest tests/` + security sweep + flags open D-entries
- [ ] Document gate in `decisions_tracker.md`

### Priority 3 — D-030 security-sweep agent
- [ ] Design `security-sweep` agent (`.claude/agents/security-sweep.md`):
      Scans staged diff for `.env`, plaintext API keys, `ANTHROPIC_API_KEY=`, hardcoded tokens
      Returns PASS/BLOCK with specific finding + file:line. Never writes.
- [ ] Add new D-entry to `decisions_tracker.md` (D-034 or next available)
- [ ] Wire into pre-merge gate (Priority 2)

### Priority 4 — Split agents directory
- [ ] Create `agents/generalist/` and `agents/specialist/` under `.claude/agents/`
- [ ] Generalist: pre-qualifier, post-scorer, process-monitor, researcher, validator, committer
- [ ] Specialist: transcript-parser, parser-evaluator, parser-fixer, security-sweep
- [ ] Dev scaffolding: coder, test-writer → `agents/dev/`
- [ ] Update all agent references

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
