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

**From the first two runs (1 completed case each — evaluator was broken for the other 6):**

| Dimension | Pass rate |
|---|---|
| field_completeness | 1.0 (100%) |
| boundary_accuracy | 1.0 (100%) |
| speaker_attribution | 1.0 (100%) |
| information_loss | 0.0 (0%) |
| verbatim_constraint | 0.0–1.0 (mixed) |

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

## Open Infrastructure Threads

### 1. Evaluate all 57 training cases (not just 7)
Current batch size is 7 per run (~2.5hr wall clock at 2.5min/case). To cover
all 57 cases, need either: (a) increase batch size with parallelism, or (b) run
multiple seeds until convergence. No API cost — only Pro auth.

### 2. Parser-fixer loop closure
Deferred (Units 5+6 in the plan). Once aggregate_failures.py runs on a
multi-case completed run, the fixer can generate a prompt patch. After patching,
re-run the same seed to measure delta. This is the RL loop.

### 3. Worktree cleanup
Two stale worktrees remain from this session:
- `.claude/worktrees/agent-a4feadb7ef73b89db` — eval_loop.py fix (merged to main)
- `.claude/worktrees/agent-a2aaff5c30a948f4b` — earlier work (check if needed)
These can be removed: `git worktree remove .claude/worktrees/<name> --force`

---

## Session Commit Log (this session's work)

| Commit | Change |
|---|---|
| `08e51e9` | Fix eval_loop: claude CLI agents, no API credits required |
| `345aed3` | Fix evaluator: file paths instead of inline JSON (D-032) |

These build on top of commits `dc3de81`, `0806ac1`, `3c4cb41` from earlier in
the session (eval pipeline scaffold, haiku agent switch, .claudeignore).

Branch is 5 commits ahead of `origin/main` — push before closing if desired.

---

## What to Tell the Next Session

1. The eval pipeline works end-to-end. Parser (transcript-parser, haiku) and
   evaluator (parser-evaluator) both run via `claude -p --agent` (Pro auth, no credits).

2. Parser passes field_completeness, boundary_accuracy, speaker_attribution.
   Parser fails information_loss and verbatim_constraint — specific fixes identified.

3. The next unit of work is the **parser-fixer loop**:
   - Run `aggregate_failures.py` on completed run dirs
   - Feed failure_summary.json to parser-fixer agent
   - Apply patch to transcript-parser.md
   - Re-run same seeds to measure delta

4. The `decisions_tracker.md` is authoritative for architecture state. D-031 and
   D-032 were added this session and reflect the active canonical paths.
