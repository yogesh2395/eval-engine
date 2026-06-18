# eval-engine — project context

## What this is
The evaluation/scorer engine for a neutral third-party evaluation authority.
Keystone principle: build the scorer before any routing logic.

## Roles
- **You (human)**: orchestrator — decide what to work on, set acceptance criteria, approve commits
- **researcher**: proposes next eval dimension with evidence. Read-only.
- **coder**: implements one scoped change at a time.
- **test-writer**: writes tests covering acceptance criteria.
- **validator**: grades work PASS/FAIL. NO write access. Judges; never fixes.

## The loop (one unit at a time)
1. You name ONE change + acceptance criteria
2. researcher gathers evidence if needed
3. coder implements only that change
4. test-writer writes tests per criteria
5. validator runs tests, scores PASS/FAIL with reasons
6. FAIL → back to coder with findings. PASS → you review diff and commit.

## Hard rules
- No orchestration platform build. No model-router build.
- Validator gates everything. A false PASS is failure.
- 2-3 parallel streams max — your review bandwidth is the real ceiling.
