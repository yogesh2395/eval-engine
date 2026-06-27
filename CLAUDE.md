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

## Architecture principles
- Core evals are built with full rigor — no simplification that diminishes diagnostic utility.
- Modular periphery (tool injectors, MCP connectors, API harnesses) is built as a detachable/upgradeable harness. Stub the slot; attach the tool later.
- Knowledge graph structure uses flat tuples for classification output now; promote to property graph only when anchor-rules develop transitive structure a lookup table cannot express.
- All four property flags (distributional, intractable, reflexive, gameable) are in scope for v1 — flags are not decorative; each must change at least one scoring anchor or be deleted.

## Rubric architecture: constitution → generator → repository
- `rubric_spec.yaml` is the **constitution**: invariant, domain-independent dimensions with abstract anchors. No industry, problem-type, or company-specific language in anchor text.
- A **generator** instantiates concrete anchors for a given (industry, problem-type, approach). "Names ≥2 distinct cost drivers" is decomposition instantiated for a cost problem; "segments the market by X" is decomposition instantiated for market-entry. Flexibility lives in the generator.
- Every instantiated rubric produced by the generator gets stored in the **repository**. The semantic asset accretes as a byproduct of usage — no cold-start required, comparability and longitudinal lock-in accrete over time.
- Domain-specific examples (e.g., the OPEX cost-overrun scenario) are **generator test fixtures** only — never baked into the constitution's anchor text. One example per criterion is permitted as an `opex_example:` documentation field, clearly labeled as a placeholder instantiation.

## Neutrality discipline
- Any calibration/validation data used to tune rubrics or scorers must be tagged with its source operator/engagement.
- If validation cases come from a single operator's own client work, flag it explicitly as a neutrality risk — calibration must not silently absorb one operator's worldview as ground truth.
- Before a rubric is "validated," include at least one case sourced independently of the primary operator.

## Confidence discipline
- Distinguish verified facts (test passed/failed, output observed) from inferred claims (why something failed, which approach is better) explicitly in every agent output.
- Never state an inference with the confidence of a verified fact.
