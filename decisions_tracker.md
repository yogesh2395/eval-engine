# decisions_tracker.md

> Update this file before each `/committer` push. Add new entries for decisions made
> in the session. Mark superseded entries with Status: Superseded by [D-NNN].
> Entries are numbered chronologically. Inference from code is marked [inferred].

---

## Product Decisions

### [D-001] Build scorer before routing logic
- **Category:** Product
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("Keystone principle: build the scorer before any routing logic.")
- **Decision:** The evaluation/scorer engine must be fully built and validated before any routing or orchestration logic is considered.
- **Rationale:** Routing logic without a calibrated scorer produces noise. The scorer is the only ground-truth asset; routing is downstream of it.
- **Implications:** Any PR touching orchestration or model-router is out of scope until the scorer ships. Validator must FAIL any work that conflates scorer with router.

---

### [D-002] v1 scope: pre + post eval phases only; during-phase is v2
- **Category:** Product
- **Status:** Locked
- **Implemented in:** CLAUDE.md (implied by phase structure), prequal_spec.yaml, rubric_spec.yaml
- **Decision:** Version 1 includes only the pre-qualifier gate and the post-scorer. The during-evaluation process-monitor is deferred to v2 for scoring purposes.
- **Rationale:** Sequencing risk reduction — the pre/post pipeline can be validated end-to-end without the complexity of real-time trace capture. Adding during-phase scoring in v1 would block delivery on a dependency that requires external trace artifacts.
- **Implications:** process-monitor agent exists as a diagnostic tool in v1 but its output does not feed into the headline score. Post-scorer must degrade gracefully when trace artifacts are absent (journey_coherence → N/A).

---

### [D-003] Process-monitor is OPEN loop in v1 — output goes to orchestrator only
- **Category:** Product
- **Status:** Locked
- **Implemented in:** CLAUDE.md (Architecture principles); process-monitor agent definition
- **Decision:** In v1, the process-monitor's output is diagnostic-only. It flows to the orchestrator and post-scorer; it never surfaces to the consultant.
- **Rationale:** Surfacing real-time diagnostic signals to the consultant mid-session creates a feedback loop that could alter the very behavior being evaluated (reflexive contamination). Closed loop is a v2+ decision requiring explicit neutrality controls.
- **Implications:** process-monitor output schema must include a `loop_mode: open` field. Any agent that routes monitor output to the consultant is a bug.

---

### [D-004] Target use case: neutral third-party evaluation authority
- **Category:** Product
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("What this is: The evaluation/scorer engine for a neutral third-party evaluation authority.")
- **Decision:** This system is built as a neutral third-party evaluator, not an operator-specific or self-assessment tool.
- **Rationale:** Operator-embedded tools absorb the operator's worldview as calibration data, undermining comparability. A neutral authority's credibility requires independence from any single operator's cases, language, or preferences.
- **Implications:** All rubric anchors must be domain-independent. Calibration data must be sourced independently. Operator-specific examples are fixtures only. Neutrality discipline (D-023) is a direct corollary.

---

## Architecture Decisions

### [D-005] Constitution/generator/repository architecture
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("Rubric architecture: constitution → generator → repository"); rubric_spec.yaml (the constitution itself)
- **Decision:** The rubric system has three layers: (1) rubric_spec.yaml is the invariant constitution with domain-independent anchors, (2) a generator instantiates concrete anchors for a given (industry, problem-type, approach), (3) a repository accumulates every instantiated rubric produced.
- **Rationale:** Separating invariants from instantiations allows the same scoring engine to cover any domain without re-architecting. The repository creates a semantic flywheel — comparability and longitudinal lock-in accrete as a byproduct of normal usage with no cold-start effort.
- **Implications:** The constitution file (rubric_spec.yaml) must be treated as append-only for dimensions and strictly abstracted for anchor text. The generator is the only place domain-specific language is permitted. The repository is the commercial moat.

---

### [D-006] Three evaluation phases: pre-qualifier / post-scorer / process-monitor
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (pre-qualifier); rubric_spec.yaml (post-scorer); process-monitor agent definition
- **Decision:** Evaluation is divided into three phases: (1) pre-qualifier gates and classifies before any scoring; (2) post-scorer scores quality across 8 dimensions; (3) process-monitor (during) is diagnostic-only in v1.
- **Rationale:** Phase separation enforces a clean dependency chain. The pre-qualifier's gate output conditions how post-scorer anchors are applied — without the gate, the post-scorer cannot know which conditional dimensions are active.
- **Implications:** Pre-qualifier must always run before post-scorer. If gate == BLOCK, post-scoring is short-circuited entirely. journey_coherence and calibration are conditional dimensions — N/A when their prerequisite artifacts are absent.

---

### [D-007] Flat tuples for knowledge graph output in v1
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("Knowledge graph structure uses flat tuples for classification output now; promote to property graph only when transitive structure emerges.")
- **Decision:** Classification output in v1 uses flat tuples (cardinality, verifiability, flags as booleans). Promotion to a property graph with nodes, edges, and transitive inference is deferred until anchor-rules develop structure that a lookup table cannot express.
- **Rationale:** Property graphs impose overhead (query language, traversal logic, schema versioning) that is not justified until the rules become transitive. Premature promotion adds complexity without diagnostic benefit.
- **Implications:** conditioning_map in prequal_spec.yaml is a flat lookup over (cardinality × verifiability × flags). Any proposal to add edge types or graph traversal requires evidence of a transitive rule first.

---

### [D-008] Aggregation rule: gate → safety-critical cap → weighted average
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** rubric_spec.yaml (io_shape and criteria structure); implied by D-009
- **Decision:** The overall_score aggregation applies three sequential rules: (1) if gate == BLOCK, no score is produced; (2) if any safety-critical dimension scores ≤2, the overall_score is capped at 3; (3) otherwise, a weighted average of criterion_scores is used.
- **Rationale:** A weighted average alone can paper over a catastrophic failure on a single critical dimension (e.g., an analyst who guesses everything right but has zero evidentiary grounding). The cap makes safety-critical failures structurally visible in the headline score.
- **Implications:** Scorers must apply the cap check before computing the weighted average. Any change to the safety-critical dimension list (D-009) automatically changes the cap's trigger condition.

---

### [D-009] Safety-critical cap: root_cause, evidentiary_grounding, calibration ≤2 → overall capped at 3
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** rubric_spec.yaml (scoring_rules or notes); CLAUDE.md (implied by architecture principles)
- **Decision:** If any of {root_cause, evidentiary_grounding, calibration} scores ≤2, the overall_score is capped at 3 regardless of other dimension scores.
- **Rationale:** These three dimensions represent the most diagnostically dangerous failure modes: misidentifying causes (root_cause), making claims without evidence (evidentiary_grounding), and being miscalibrated about uncertainty (calibration). A high overall score with any of these failing is misleading and dangerous.
- **Implications:** These three dimensions cannot be absent or N/A when a score is produced. Post-scorer must flag any score where the cap fires. Changing this set requires an architecture-level decision, not a coder-level change.

---

### [D-010] Problem-type taxonomy: Axis A {contradictory/unique/multiple} + Axis B {direct/indirect/counterfactual}
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (cardinality + verifiability enums)
- **Decision:** The problem-type taxonomy uses two independent axes: Axis A (cardinality) = {contradictory, unique, multiple} and Axis B (verifiability) = {direct, indirect, counterfactual}. This replaces an earlier taxonomy of {deterministic/stochastic × closed/open}.
- **Rationale:** The original axes were not MECE — "deterministic" and "stochastic" describe a property of the problem, not the structure of its solution set. The new axes partition by (a) whether feasible solutions exist and how many (Axis A) and (b) how strongly the outcome can be verified within the decision horizon (Axis B). These are orthogonal and exhaustive.
- **Implications:** All conditioning rules in the pre-qualifier reference (cardinality, verifiability) not the old axes. The old taxonomy is superseded and must not appear in any new code or spec.

---

### [D-011] 4 boolean flags in v1 scope; each must change a scoring anchor or be deleted
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (flags object: distributional, intractable, reflexive, gameable); CLAUDE.md ("flags are not decorative; each must change at least one scoring anchor or be deleted")
- **Decision:** Four boolean property flags — distributional, intractable, reflexive, gameable — are all in scope for v1. Each flag is only retained if it changes at least one post-scorer anchor in the conditioners list.
- **Rationale:** Decorative flags create false complexity: they appear to enrich classification without affecting scoring. If a flag has no downstream effect, it is noise that degrades trust in the classifier.
- **Implications:** When implementing conditioners for each flag, the test must verify that at least one rubric anchor shifts when the flag is set. Any flag that cannot produce a conditioner that changes an anchor must be dropped before v1 ships.

---

### [D-012] Solution-verification stub for unique+direct problems
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (implied by verifiability=direct conditioner); CLAUDE.md (modular periphery principle)
- **Decision:** For problems classified as unique+direct (one correct answer, verifiable outcome), a solution-verification tool slot is reserved. In v1, the slot is a stub — the scorer evaluates confidence-evidence alignment only. A future MCP/proof-runner can be attached without changing the scoring schema.
- **Rationale:** unique+direct problems are the only class where a formal verifier could replace the rubric's evidentiary proxies with a definitive check. Reserving the slot now avoids a schema-breaking change later. Stubbing is consistent with the modular periphery principle (D-005 implications).
- **Implications:** The conditioners list for unique+direct must include a note about the verification stub. Post-scorer documentation must state that v1 scores confidence-evidence alignment, not verified correctness.

---

## Design Decisions

### [D-013] 8 scoring dimensions: 6 invariant + 2 conditional
- **Category:** Design
- **Status:** Locked
- **Implemented in:** rubric_spec.yaml (criterion_scores: decomposition, root_cause, tradeoff_awareness, materiality, evidentiary_grounding, feasibility, journey_coherence, calibration)
- **Decision:** The post-scorer has 8 dimensions. Six are invariant (always scored): decomposition, root_cause, tradeoff_awareness, materiality, evidentiary_grounding, feasibility. Two are conditional: journey_coherence (N/A when process trace is absent) and calibration (N/A when problem_type classification is absent).
- **Rationale:** Conditional dimensions allow the rubric to score more when more information is available, without requiring that information to be present. N/A is an honest score; a forced score on absent data is a false PASS.
- **Implications:** Scorer implementation must handle N/A returns from conditional dimensions without treating them as 0s in the weighted average. Aggregation (D-008) must be defined for partial dimension sets.

---

### [D-014] OPEX scenario is a generator test fixture only — never baked into constitution anchor text
- **Category:** Design
- **Status:** Locked
- **Implemented in:** rubric_spec.yaml (example_scenario field labeled as placeholder; opex_example fields per criterion); CLAUDE.md ("Domain-specific examples are generator test fixtures only")
- **Decision:** The OPEX cost-overrun scenario exists only as a generator test fixture. All 40 level anchors (8 dimensions × 5 levels) use domain-independent language. One opex_example: documentation field per criterion is permitted, clearly labeled.
- **Rationale:** Baking a domain example into anchor text would make the rubric appear to require OPEX-specific knowledge, breaking neutrality and preventing generator reuse for other domains.
- **Implications:** Test fixtures for the generator use the OPEX case. Tests for the constitution (rubric_spec.yaml structure) must verify that anchor text contains no OPEX-specific or industry-specific terms. D-017 is a direct corollary.

---

### [D-015] Level-3 anchor is the "meets standard" floor
- **Category:** Design
- **Status:** Locked
- **Implemented in:** rubric_spec.yaml (level 3 anchors for each dimension include the phrase "Meets standard:")
- **Decision:** Across all 8 scoring dimensions, the level-3 anchor is defined as the minimum acceptable quality floor. It is labeled "Meets standard:" in the anchor text. Levels 1-2 describe failure modes; levels 4-5 describe above-standard performance.
- **Rationale:** A named floor makes the scoring scale normative rather than purely ordinal. Evaluators and scorers know that a 3 means "acceptable, not excellent." This prevents grade inflation at the middle of the scale.
- **Implications:** The post-scorer's justification (D-013) must explain when a response falls below the level-3 floor. Test proxies for falsifiability are scoped to levels 3-5 (D-016) because the floor is the diagnostic threshold.

---

### [D-016] Falsifiable-marker proxy tests scoped to levels 3-5 only
- **Category:** Design
- **Status:** Locked
- **Implemented in:** tests/test_rubric_spec.py; commit a3b1423 ("Scope rubric_spec test proxies to levels 3-5 only")
- **Decision:** Automated tests checking that level anchors contain falsifiable markers (specific quantities, named conditions, testable claims) apply only to levels 3, 4, and 5. Levels 1 and 2 are explicitly excluded.
- **Rationale:** Levels 1 and 2 legitimately describe vague or absent behavior — "no decomposition" and "names at most 1 sub-component" are correctly imprecise anchors for failure modes. Requiring falsifiable markers at those levels would force artificial specificity into failure descriptions.
- **Implications:** Any regression to applying falsifiability proxy tests to levels 1-2 is a test design bug, not a rubric bug. The test file must document this scope restriction explicitly.

---

### [D-017] Cost-center term proxy removed from rubric tests
- **Category:** Design
- **Status:** Locked
- **Implemented in:** tests/test_rubric_spec.py (proxy removed); related to commit a3b1423
- **Decision:** Automated tests must not check for OPEX-specific terms (e.g., "cost center," "storage," "logistics") in the rubric_spec.yaml anchor text.
- **Rationale:** Such a test would incorrectly validate OPEX-specificity as a feature of the constitution, when D-014 requires the constitution to be domain-independent. The proxy was testing the wrong thing.
- **Implications:** Any new test that checks for domain-specific terms in the constitution file is a defect. The generator's tests are the correct place to verify domain-specific instantiation.

---

### [D-018] Well-posedness gate uses PASS/BLOCK/CONDITIONAL (not binary)
- **Category:** Design
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (gate enum: [PASS, BLOCK, CONDITIONAL])
- **Decision:** The pre-qualifier gate is a ternary decision: PASS (proceed normally), BLOCK (refuse scoring), CONDITIONAL (proceed with caveats surfaced to post-scorer). Ambiguous cases default to CONDITIONAL, not PASS.
- **Rationale:** A binary gate forces borderline framings into either full approval or full refusal. CONDITIONAL preserves the ability to score while explicitly flagging the limitation, which is more useful diagnostically than either extreme. Defaulting ambiguous cases to CONDITIONAL rather than PASS enforces conservative scoring — a false PASS is the worst outcome (D-026).
- **Implications:** The post-scorer must consume the conditional_flag field and reflect it in the rationale. A CONDITIONAL gate with no downstream flag consumption is a schema violation.

---

### [D-019] block_cta must be specific — generic "please revise" is a defect
- **Category:** Design
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (block_cta description: "Concrete call-to-action: what specific change would make this submission scoreable. Not a generic 'please revise.'")
- **Decision:** When gate == BLOCK, the block_cta field must name the exact change that would make the submission scoreable. A generic instruction (e.g., "please revise your framing") fails the spec.
- **Rationale:** Generic CTAs are useless to the consultant and mask the diagnostic signal. A specific CTA (e.g., "State a falsifiable claim: replace 'improve operations' with a specific outcome you expect to change and by how much") is actionable and calibrates the consultant's next attempt.
- **Implications:** Validator must check block_cta specificity when reviewing pre-qualifier output. A BLOCK with a generic CTA is graded FAIL, not PASS.

---

### [D-020] Data sufficiency assessed only as "did framing declare data needs" — not objective sufficiency
- **Category:** Design
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (data_declaration sub-check description: "data sufficiency is NOT assessed as 'is data objectively sufficient' — only: 'did the framing declare its data needs and gaps?'")
- **Decision:** The pre-qualifier's data check evaluates only whether the consultant's framing declared what data it needs and flagged known gaps. It does not assess whether the data is objectively sufficient.
- **Rationale:** Assessing objective sufficiency requires external ground truth about what data actually exists — which the evaluator cannot access without breaking neutrality. The declarative check is admissible because it depends only on the framing artifact.
- **Implications:** Scorers must not penalize a consultant for having insufficient data if the framing honestly declared the gap. Penalizing data gaps that are honestly acknowledged is both inadmissible and discourages calibration (D-024).

---

### [D-021] Hard constraint vs soft preference declaration required in framing when material to cardinality
- **Category:** Design
- **Status:** Locked
- **Implemented in:** prequal_spec.yaml (constraint_type_declaration sub-check; CONDITIONAL gate rule for undeclared constraints)
- **Decision:** The framing must explicitly distinguish hard constraints (immovable, cardinality = 0 if violated) from soft preferences (aspirational, relaxable) when the distinction is material to classifying the solution-set cardinality. Failure to declare fires CONDITIONAL with a CTA to declare.
- **Rationale:** Without the constraint/preference distinction, the cardinality classification is ambiguous — the same framing could be contradictory (if the constraints are hard) or multiple (if they are soft preferences). Ambiguity in cardinality propagates error through all downstream conditioners.
- **Implications:** This is a MECE leak fix — prevents the classifier from silently assigning cardinality under ambiguous constraint types. The CTA must name which specific constraint type was undeclared.

---

## Ethos / Intent Decisions

### [D-022] Log ALL events including BLOCK cases — data is the RL flywheel
- **Category:** Ethos
- **Status:** Locked
- **Implemented in:** MEMORY.md ("Log everything — data flywheel — all events including BLOCK cases must be logged; data is the RL flywheel asset; never discard partial/failed evaluations")
- **Decision:** Every evaluation event — including BLOCKs, CONDITIONALs, and failed evaluations — must be logged to the repository. Nothing is discarded.
- **Rationale:** BLOCK cases are the most diagnostically valuable data points — they reveal systematic framing failures that a dataset of PASSing evaluations cannot surface. Discarding them sacrifices the RL signal needed to improve the pre-qualifier's classification accuracy.
- **Implications:** The logging schema must capture gate decision, block_reason, block_cta, and timestamp at minimum for BLOCK events. A log pipeline that drops BLOCK events is a defect. The repository (D-005) accretes BLOCK cases alongside scored evaluations.

---

### [D-023] Neutrality discipline — calibration data tagged; single-operator calibration flagged
- **Category:** Ethos
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("Neutrality discipline" section)
- **Decision:** All calibration/validation data must be tagged with its source operator/engagement. If validation cases come exclusively from one operator's client work, this must be explicitly flagged as a neutrality risk. At least one independently sourced case is required before classifier thresholds are treated as validated.
- **Rationale:** Single-operator calibration silently absorbs that operator's worldview as ground truth. This produces a scorer that is calibrated for that operator's consulting style, not for the general population of consultants — exactly the opposite of a neutral third-party authority (D-004).
- **Implications:** The repository schema must include a `source_operator` tag on every calibration case. "Validated" is a status that requires at least one independent case. A rubric validated entirely on operator A's cases must carry a neutrality risk flag until a diverse case is added.

---

### [D-024] Confidence discipline — distinguish verified facts from inferences in every agent output
- **Category:** Ethos
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("Confidence discipline" section)
- **Decision:** Every agent output (validator, post-scorer, pre-qualifier, researcher) must explicitly distinguish verified facts (test passed/failed, output observed) from inferred claims (why something failed, which approach is better). Inferences must never be stated with the confidence of verified facts.
- **Rationale:** Conflating inference with fact degrades trust in the evaluation system and produces feedback that cannot be acted on safely. A validator that states "this fails because the coder misunderstood X" is making an inference; the verified fact is only "test Y returned FAIL."
- **Implications:** Agent output schemas should include a `confidence` or `basis` field for each finding. Validator output must separate the PASS/FAIL verdict (verified) from the diagnostic explanation (inferred). False PASSes caused by confident-sounding inferences are the worst outcome (D-026).

---

### [D-025] Agent model names use bare role names — version independence
- **Category:** Ethos
- **Status:** Locked
- **Implemented in:** CLAUDE.md (Roles section uses bare names: researcher, coder, test-writer, validator)
- **Decision:** Agent model assignments use bare role names (sonnet, opus, haiku) rather than pinned version IDs (e.g., claude-opus-4-5-20251101). Version selection is delegated to the harness.
- **Rationale:** Pinning version IDs creates maintenance overhead on every model update and couples the eval engine's logic to Anthropic's release schedule. Bare role names allow the harness operator to update model versions without touching rubric or spec files.
- **Implications:** Any agent definition that hard-codes a version ID should be refactored to use the bare role name. The harness is responsible for resolving role name → current model ID.

---

### [D-026] Validator gates everything; false PASS is the worst outcome
- **Category:** Ethos
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("Validator gates everything. A false PASS is failure."); validator agent definition ("A false PASS is the worst outcome.")
- **Decision:** The validator is the constitutional gate for all work. A false PASS — approving work that does not meet acceptance criteria — is defined as the worst possible outcome, worse than a false FAIL (which wastes iteration time but does not ship broken work).
- **Rationale:** A false FAIL causes rework; a false PASS ships a defect into the rubric that silently corrupts all downstream scores. Given that the rubric is the system's core asset (D-005), a corrupt rubric is a systemic failure, not a local one.
- **Implications:** The validator has NO write access and must NEVER fix what it finds. Its only output is PASS/FAIL with reasons. The orchestrator (human) decides whether to send work back to the coder or accept it. Any agent that both grades and fixes is violating this constraint.

---

### [D-027] 2-3 parallel streams max — reviewer bandwidth is the real ceiling
- **Category:** Ethos
- **Status:** Locked
- **Implemented in:** CLAUDE.md ("2-3 parallel streams max — your review bandwidth is the real ceiling.")
- **Decision:** At most 2-3 units of work may be in flight simultaneously. The constraint is not compute or cost — it is the orchestrator's capacity to review diffs, verify acceptance criteria, and approve commits without losing context.
- **Rationale:** More parallel streams than a human reviewer can track in a session produce rubber-stamp approvals, which degrade the validator's gate (D-026). The loop (CLAUDE.md) is designed around one unit at a time per stream; parallelism is a concession to efficiency, not an override of review quality.
- **Implications:** The committer agent must not push more than one unit without explicit orchestrator approval of each diff. If the orchestrator is reviewing stream A, stream B must not be committed until A is resolved.

---

## Architecture Decisions (continued)

### [D-028] Two input formats supported: transcript (A) and structured response (B)
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** transcript-parser.md, detect_format.py, rubric_spec.yaml (input_format field), prequal_spec.yaml
- **Decision:** The eval engine accepts two input formats: Format A (conversational interview transcript with interleaved interviewer/candidate turns) and Format B (polished structured response). Format detection is deterministic (regex, <100ms). Format A routes through transcript-parser first; Format B goes directly to pre-qualifier.
- **Rationale:** IIMA casebook provides both formats. Excluding transcripts would discard the primary training corpus. Excluding structured responses would prevent evaluation of deliverable-format submissions.
- **Implications:** transcript-parser output must include `input_format: "transcript"` so downstream agents apply the correct scoring conditioners (e.g., journey_coherence is N/A without a reasoning trace).

---

### [D-029] Parser improvement loop: evaluator judges, fixer patches, never coupled
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** parser-evaluator.md, parser-fixer.md
- **Decision:** Parser quality improvement uses a two-agent loop. The evaluator (neutral judge) assesses extraction quality across 5 dimensions and issues PASS/FLAG/FAIL. The fixer (operator) reads only the failure log and generates prompt patches — never the evaluator's criteria. These are separate agents that never share context.
- **Rationale:** If the fixer knew the evaluator's criteria, it could game the evaluation rather than improve actual extraction quality. Separation maintains the neutrality principle (D-023) within the parser loop itself.
- **Implications:** Evaluator output (verdict + failure log) is the only interface between judge and fixer. The fixer must not read parser-evaluator.md. Validator checks this separation in any PR touching either agent.

---

### [D-030] Credential management: macOS Keychain only — never .env or plaintext files
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** scripts/setup_keychain.sh, scripts/run_parser.sh, scripts/parse_transcript.py
- **Decision:** The Anthropic API key for the direct-API parser path is stored in macOS Keychain under service=eval-engine, account=anthropic. Scripts read it via `security find-generic-password` at runtime. No .env file. No plaintext storage on disk.
- **Rationale:** .env files are readable by any process with filesystem access to the project directory. Keychain is encrypted at rest, requires OS authentication, and is not readable by third-party processes without explicit permission grant.
- **Implications:** The `parse_transcript.py` error message for missing key directs to Keychain, not .env. The .pip_deps/ and .env are both in .gitignore. Production deployment uses a secrets manager (AWS SM / Vault) as the equivalent.

---

### [D-031] Claude CLI subprocess is the canonical agent-call path — direct Anthropic API deprecated for eval pipeline
- **Category:** Architecture
- **Status:** Locked
- **Supersedes:** Earlier assumption that `parse_transcript.py` (direct `anthropic.Anthropic()` API) was the parser path
- **Implemented in:** scripts/eval_loop.py (`_call_parser`, `_call_evaluator` use `subprocess.run(["claude", "-p", ..., "--agent", ...])`); .claudeignore (scripts/parse_transcript.py and scripts/run_parser.sh excluded from Claude context)
- **Decision:** All agent invocations in the eval pipeline use `claude -p --agent <name> --output-format text --dangerously-skip-permissions --no-session-persistence` via subprocess. The direct `anthropic.Anthropic(api_key=...)` path (parse_transcript.py) is deprecated. No ANTHROPIC_API_KEY is needed or read.
- **Rationale:** `claude -p --agent` routes through Claude Pro OAuth (macOS Keychain token managed by the claude CLI). The direct API requires pay-as-you-go credits on a separate billing account. Since the eval engine runs on a Pro subscription, the CLI path costs nothing incremental and eliminates a credential class entirely.
- **Implications:** `parse_transcript.py` and `run_parser.sh` are in `.claudeignore` — they are not the active path. Do not reintroduce `anthropic.Anthropic()` calls in the eval pipeline. Latency is ~2.5min per document due to claude CLI startup overhead; this is acceptable for batch runs but not real-time use.

---

### [D-032] Evaluator receives file paths — agents read their own inputs via Read tool
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** scripts/eval_loop.py (`_call_evaluator(parse_output_path, case_path)`)
- **Decision:** The parser-evaluator agent is passed two file paths (parse_output_path, case_path) and uses its Read tool to load them. The eval_loop never embeds parse output as inline JSON in the claude CLI `-p` argument.
- **Rationale:** Embedding the full parse JSON (including `full_transcript`, which can be 20K+ chars) as a CLI argument causes a silent agent failure — the subprocess returns exit code 1 with empty stderr because macOS ARG_MAX is exceeded. File paths are stable, short, and let the agent control its own I/O.
- **Implications:** Any agent that receives large data must get it via file path, not inline `-p` injection. This is the correct pattern for all future agent integrations: write artifact to disk, pass path, agent reads it.

---

## DevOps / Tooling Decisions

### [D-034] Pre-merge gate: pytest + security sweep + open-D-entry check
- **Category:** DevOps
- **Status:** Locked
- **Implemented in:** scripts/pre_merge_gate.sh
- **Decision:** All merges to `main` must pass a three-check gate: (1) `pytest tests/` — zero test failures; (2) security sweep — no credentials, API keys, or `.env` files in changed files; (3) open D-entry scan — warn on any `# TODO: D-xxx` markers or non-Locked entries in `decisions_tracker.md` (non-blocking, logs warning).
- **Rationale:** The gate encodes the project's minimum bar mechanically so it cannot be skipped by oversight. The security sweep prevents D-030 credential-class bugs from reaching the repo. The D-entry warning surfaces unresolved architectural debt at merge time rather than at runtime.
- **Implications:** Run `./scripts/pre_merge_gate.sh` before every push to main. The script exits 0 (PASS) or 1 (FAIL). D-entry warnings are non-blocking. GitHub branch protection on private repos requires a paid plan (Pro/Team) — confirmed unavailable on this account. The gate script is the sole enforcement mechanism; this is acceptable for a single-contributor repo.

---

### [D-035] Security-sweep agent: read-only credential scanner for staged diffs
- **Category:** DevOps
- **Status:** Locked
- **Implemented in:** .claude/agents/dev/security-sweep.md
- **Decision:** A dedicated `security-sweep` Claude agent scans staged diffs or named files for credential leaks (raw API keys, hardcoded passwords/tokens, tracked `.env` files). It returns a structured JSON verdict (PASS or BLOCK) with specific finding at file:line. It has NO write access.
- **Rationale:** A grep-only sweep (used in pre_merge_gate.sh) is fast and deterministic for known patterns. The Claude agent layer adds semantic understanding for edge cases (e.g., distinguishing a real token from a test fixture), produces structured machine-readable output, and can be invoked ad-hoc during development. Both layers are complementary.
- **Implications:** The agent is wired into pre_merge_gate.sh as the backing scanner. Agent output schema uses `verdict: PASS|BLOCK` and a `findings` array with `file`, `line`, `pattern`, `snippet`, `severity`. A false PASS (missed credential) is the worst outcome — the agent is biased toward BLOCK on ambiguous cases.

---

### [D-036] Agents directory split: generalist / specialist / dev tiers
- **Category:** DevOps
- **Status:** Locked
- **Implemented in:** .claude/agents/generalist/, .claude/agents/specialist/, .claude/agents/dev/
- **Decision:** Agent files under `.claude/agents/` are organized into three subdirectories: `generalist/` (researcher, validator, committer, process-monitor), `specialist/` (transcript-parser, parser-evaluator, parser-fixer, pre-qualifier, post-scorer), `dev/` (coder, test-writer, security-sweep). Agent discovery remains by `name:` frontmatter field — the claude harness scans subdirectories recursively.
- **Rationale:** Tier semantics: generalist = general-purpose agents reusable outside this project; specialist = domain-specific to this eval engine's pipeline (scoring rubric, pre-qual gate, transcript extraction); dev = development-workflow tools not on the production eval path. pre-qualifier and post-scorer are specialist, not generalist — they encode this engine's rubric and gate logic and have no meaning outside it.
- **Supersedes:** Initial (incorrect) placement of pre-qualifier and post-scorer in generalist/.
- **Implications:** New agents must be placed in the correct tier before their first PR. The `--agent <name>` CLI invocation is unaffected — it matches on the `name:` field, not the file path. If the harness is updated to scope agent access by tier (e.g., restricting specialist agents to specific callers), the subdirectory structure makes that policy trivially enforceable.

---

### [D-037] Validator bypass fix: pre-commit hook + committer sentinel
- **Category:** DevOps
- **Status:** Locked
- **Implemented in:** scripts/hooks/pre-commit, scripts/install_hooks.sh, .claude/agents/generalist/committer.md, CLAUDE.md (Hard rules)
- **Decision:** The validator loop (CLAUDE.md) had no mechanical enforcement — any session could `git commit` directly, bypassing the validator entirely. Fixed by: (1) `scripts/hooks/pre-commit` blocks commits on logic files (.py, .sh, agent .md) unless `logs/validator_pass.flag` exists; (2) the committer agent now requires the orchestrator to paste the validator's PASS verdict before writing the flag; (3) the flag is consumed (deleted) on each commit so it cannot carry over; (4) CLAUDE.md Hard rules explicitly name background sessions as non-exempt.
- **Rationale:** Documentation does not stop a background session from committing directly. Only a mechanism in the commit path itself is reliable. The pre-commit hook fires unconditionally on every `git commit`, regardless of which agent or session invoked it. --no-verify is already banned (D-026 / CLAUDE.md), so the hook cannot be legitimately bypassed.
- **Implications:** Run `./scripts/install_hooks.sh` once after cloning or after pulling this change. The hook is not checked into `.git/hooks/` (git does not track hooks), so install_hooks.sh must be run manually. For logic-file commits: invoke validator → get PASS → committer writes flag → commit proceeds. For docs/config-only commits: hook self-skips, no sign-off needed.

---

### [D-038] Scorer output: decimal overall_score, two-part breakdown, plural aggregation mechanics, per-dimension justification
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** rubrics/rubric_spec.yaml, .claude/agents/specialist/post-scorer.md, scripts/aggregate_score.py, tests/test_rubric_spec.py, tests/test_eval_loop.py
- **Decision:** The post-scorer no longer rounds `overall_score` to an integer — it reports the exact mean to ≤3 decimal places (`type: number`). Output is enriched with (a) `score_breakdown` = {process_score, recommendation_score}, splitting the 8 dimensions into a diagnostic-journey group {decomposition, root_cause, materiality, journey_coherence} and a final-recommendation group {tradeoff_awareness, feasibility, evidentiary_grounding, calibration}; (b) `aggregation` = {equal_weighted (primary headline for now), conditioner_adaptive, critical_floor, scaled_percentile}; (c) `dimension_justifications` — a mandatory observation+verbatim-quote per non-N/A dimension. `overall_score` = equal_weighted pending comparison of alternates.
- **Rationale:** A single rounded integer erased the c03 signal — process dimensions meant 4.5 (excellent diagnosis) while recommendation dimensions meant 2.25 (reflexive/gameable-blind), yet the headline was a flat "3". Equal-weighted is a defensible baseline but is naive for problem-type-conditioned scoring; standardized/adaptive-testing practice (GMAT/GRE/SAT, IRT item discrimination) motivates the alternates. `conditioner_adaptive` up-weights the dimensions the pre-qualifier re-anchored (weight map mirrors prequal_spec `downstream_anchor_shifts` exactly) so the score reflects the dimensions that matter most for THIS problem type — c03 falls 3.375 → 2.938. `critical_floor` replaces the binary safety cliff with a graduated ceiling min(5, 1.5 + 0.75·critical_min).
- **Implications:** io_shape.output canonical set is now {overall_score, aggregation, score_breakdown, criterion_scores, dimension_justifications, justification}. Aggregation logic lives in the deterministic `scripts/aggregate_score.py` (single source of truth for the weight map). `scaled_percentile` is a stubbed slot — it needs the D-005 repository population before it can compute. The per-dimension justification requirement closes the design/execution leak that let root_cause=4 pass unjustified (enforced mechanically in D-039). Validator PASS on all 8 acceptance criteria; suite 237/237.

---

### [D-039] Mechanical justification-completeness checker — design/execution-leakage gate integrated into the process-monitor stage
- **Category:** DevOps / Architecture
- **Status:** Locked
- **Implemented in:** scripts/check_justification_completeness.py, .claude/agents/generalist/process-monitor.md, .claude/agents/generalist/validator.md, tests/test_eval_loop.py
- **Decision:** A deterministic checker (`check_justification_completeness.py`) verifies that every non-N/A dimension in a scorer output carries a non-empty `dimension_justifications` entry; missing = (non-N/A scored dims) − (dims with non-empty justification); empty-string counts as missing; N/A dims are excluded. HARD FAIL (exit 1) if any dimension is scored without justification, naming each. A quote-detection heuristic emits advisory warnings only (never changes the verdict). The check is declared an authoritative component of the **process-monitor stage** (new `design_execution_leakage` output section) and a required **validator** acceptance criterion.
- **Rationale:** In the c03 run, `root_cause=4` was emitted with no attached justification yet the gate passed — a "design vs execution leakage" (the rubric design requires evidence per dimension; the execution omitted it). Convention alone did not catch it. A deterministic mechanical check is the only reliable enforcement (same philosophy as D-034/D-037). Verified: running the checker on the real c03 scorer_output.json exits 1 and names all 8 dimensions as missing.
- **Implications:** Because the process-monitor agent is Read-only/no-Bash, the checker runs as the stage wrapper around the agent invocation and its verdict is injected; the agent reports it and cannot override a mechanical FAIL (falls back to `status: "unavailable"` when no verdict is supplied). The runnable stage-wrapper that injects the verdict is documented intent, not yet built — it depends on the main-loop integration (RECOMMENDED TODO). Suite 244/244; validator PASS on all 7 criteria incl. the honesty check that the integration is framed as design, not a false implementation claim.

---

### [D-040] Transcript parser: speaker-attribution pass + interviewer_nudges; pre-qualifier non-penalty for interviewer-directed pruning
- **Category:** Architecture
- **Status:** Locked
- **Implemented in:** .claude/agents/specialist/transcript-parser.md, .claude/agents/specialist/pre-qualifier.md, rubrics/prequal_spec.yaml, tests/test_parser_agents.py, tests/test_prequal_spec.py
- **Decision:** (1) The transcript parser runs a Step 0 speaker-attribution pass FIRST — the opening problem_statement is the interviewer, the first clarifying question is the candidate, and the candidate-only fields (initial_framing, reasoning_trace, final_recommendation) exclude every interviewer turn. (2) A new output field `interviewer_nudges` captures verbatim interviewer redirections ("So you can move on from revenue.") and questions to the candidate ("What do you think are the possible causes for this?"), distinct from confirmed_case_facts (data reveals). (3) The pre-qualifier accepts `interviewer_nudges` as an optional input; when a redirection nudge directed the candidate off a branch, that pruning is interviewer-directed and is NOT a candidate defect / not a CONDITIONAL cause — but only for that branch. Other CONDITIONAL causes (undeclared hard constraints, missing decision horizon) are evaluated independently and unaffected.
- **Rationale:** In the c03 run the parser mis-attributed the interviewer question "What do you think are the possible causes for this?" into initial_framing and dropped the interviewer directive "So you can move on from revenue." The pre-qualifier then issued a FALSE CONDITIONAL, penalizing the candidate for a branch prune the interviewer had explicitly directed. Correct speaker attribution + surfaced nudges + a scoped non-penalty rule removes the false-positive without weakening the gate.
- **Rationale (neutrality, validator-verified):** The exemption is scoped narrowly ("do not raise CONDITIONAL on that basis") and cannot be read as "nudge present ⇒ auto-PASS"; the gate's default-to-CONDITIONAL and false-PASS-is-worst constraints remain intact. prequal_spec adds an explicit clause that the sub-check does not suppress other CONDITIONAL causes.
- **Implications:** io_shape.input for the pre-qualifier now has three keys (prompt, initial_framing, interviewer_nudges[nullable]). Absence of nudges is treated as neutral ("no nudge information"), not as evidence. The parser→pre-qualifier nudge hand-off in a runnable pipeline still depends on the main-loop integration (RECOMMENDED TODO) — Unit C makes the agent/spec changes only. Validator PASS on all 7 criteria incl. the neutrality gate; suite 249/249.
