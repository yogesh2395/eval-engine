"""
Static / structural tests for the three parser agents in .claude/agents/.

All tests read agent definition files and check their content — no live API
calls are made.  Each test maps directly to a stated acceptance criterion.

Run with:
    python3 -m pytest tests/test_parser_agents.py -v
"""

import os
import re

import pytest
import yaml

# ---------------------------------------------------------------------------
# Absolute paths
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(REPO_ROOT, ".claude", "agents")

TRANSCRIPT_PARSER_PATH = os.path.join(AGENTS_DIR, "transcript-parser.md")
PARSER_EVALUATOR_PATH = os.path.join(AGENTS_DIR, "parser-evaluator.md")
PARSER_FIXER_PATH = os.path.join(AGENTS_DIR, "parser-fixer.md")


# ---------------------------------------------------------------------------
# File-reading / parsing helpers
# ---------------------------------------------------------------------------

def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_agent(path):
    """Return (frontmatter: dict, body: str) for an agent markdown file."""
    content = _read(path)
    if not content.startswith("---"):
        return {}, content
    # Locate the closing --- that terminates the frontmatter block
    close = content.index("---", 3)
    fm = yaml.safe_load(content[3:close].strip()) or {}
    body = content[close + 3:].strip()
    return fm, body


def _first_json_block(body):
    """Return the text inside the first ```json ... ``` code block."""
    m = re.search(r"```json\s*(.*?)```", body, re.DOTALL)
    return m.group(1) if m else ""


def _field_section(body, field_name):
    """
    Extract the paragraph that starts with **field_name** up to the next
    **bold_header** or ## section header.  Blank lines between field sections
    are handled by allowing one or more newlines in the lookahead.
    """
    pattern = re.compile(
        r"\*\*" + re.escape(field_name) + r"\*\*.*?(?=\n+\*\*\w|\n##\s|\Z)",
        re.DOTALL,
    )
    m = pattern.search(body)
    return m.group(0) if m else ""


def _named_section(body, header):
    """
    Extract text under a ## header up to the next ## header or end of string.
    `header` is the text after "## ", e.g. 'Constraints'.
    """
    pattern = re.compile(
        r"##\s+" + re.escape(header) + r"\s*\n(.*?)(?=\n##\s|\Z)",
        re.DOTALL,
    )
    m = pattern.search(body)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Group 1: transcript-parser schema
# ---------------------------------------------------------------------------

class TestTranscriptParserSchema:
    """Acceptance criteria for .claude/agents/transcript-parser.md."""

    @pytest.fixture(scope="class")
    def agent(self):
        fm, body = _parse_agent(TRANSCRIPT_PARSER_PATH)
        return {"fm": fm, "body": body, "schema": _first_json_block(body)}

    # AC: agent file exists
    def test_file_exists(self):
        assert os.path.isfile(TRANSCRIPT_PARSER_PATH), (
            f"transcript-parser agent file not found at {TRANSCRIPT_PARSER_PATH}"
        )

    # AC: model is haiku (fast extraction model, not sonnet or opus)
    def test_model_is_haiku(self, agent):
        model = agent["fm"].get("model", "")
        assert model == "haiku", (
            f"transcript-parser model must be 'haiku'; got {model!r}"
        )

    # AC: model is NOT sonnet or opus
    def test_model_is_not_sonnet_or_opus(self, agent):
        model = agent["fm"].get("model", "")
        assert model not in ("sonnet", "opus"), (
            f"transcript-parser must use the fast extraction model (haiku), not {model!r}"
        )

    # AC: output schema contains all 14 required fields
    @pytest.mark.parametrize("field", [
        "case_title",
        "case_category",
        "difficulty",
        "sector",
        "input_format",
        "problem_statement",
        "initial_framing",
        "reasoning_trace",
        "final_recommendation",
        "full_transcript",
        "approach_framework_present",
        "approach_framework_text",
        "turn_count",
        "extraction_notes",
    ])
    def test_output_schema_contains_required_field(self, agent, field):
        schema = agent["schema"]
        assert schema, "transcript-parser has no JSON schema block"
        assert f'"{field}"' in schema, (
            f"transcript-parser JSON output schema is missing required field: {field!r}"
        )

    # AC: reasoning_trace present in schema (called out separately — not subsumed
    #     by initial_framing + final_recommendation)
    def test_reasoning_trace_is_distinct_schema_field(self, agent):
        schema = agent["schema"]
        assert '"reasoning_trace"' in schema, (
            "reasoning_trace must be a distinct top-level field in the output schema, "
            "not replaced by initial_framing + final_recommendation"
        )

    # AC: input_format is hardcoded to "transcript" in the schema
    def test_input_format_hardcoded_to_transcript(self, agent):
        schema = agent["schema"]
        assert '"input_format": "transcript"' in schema, (
            'input_format must be hardcoded to the string "transcript" in the output schema; '
            f"found schema block:\n{schema}"
        )

    # AC: description mentions reasoning_trace
    def test_description_mentions_reasoning_trace(self, agent):
        description = agent["fm"].get("description", "")
        assert "reasoning_trace" in description, (
            f"transcript-parser description must mention reasoning_trace; "
            f"got: {description!r}"
        )

    # AC: Constraints section prohibits paraphrase ("verbatim")
    def test_constraints_section_prohibits_paraphrase(self, agent):
        constraints = _named_section(agent["body"], "Constraints")
        assert constraints, (
            "transcript-parser has no '## Constraints' section"
        )
        assert "verbatim" in constraints.lower(), (
            "Constraints section must prohibit paraphrase using the word 'verbatim'; "
            f"section text:\n{constraints}"
        )

    # AC: field coverage check is present in the prompt
    def test_field_coverage_check_section_present(self, agent):
        assert "Field coverage check" in agent["body"], (
            "transcript-parser must contain a 'Field coverage check' section in its prompt"
        )

    # AC: field coverage check verifies all 4 specific fields are non-empty before output
    @pytest.mark.parametrize("field", [
        "problem_statement",
        "initial_framing",
        "reasoning_trace",
        "final_recommendation",
    ])
    def test_field_coverage_check_verifies_field(self, agent, field):
        section = _named_section(agent["body"], "Field coverage check before outputting")
        assert section, (
            "Could not extract '## Field coverage check before outputting' section"
        )
        assert field in section, (
            f"Field coverage check must verify '{field}' is non-empty before output; "
            f"section text:\n{section}"
        )

    # AC: boundary rules for reasoning_trace specify a start boundary
    def test_reasoning_trace_has_start_boundary(self, agent):
        rt = _field_section(agent["body"], "reasoning_trace")
        assert rt, (
            "Could not locate **reasoning_trace** field section in body"
        )
        assert "Boundary start" in rt, (
            "reasoning_trace extraction rules must specify a 'Boundary start'; "
            f"section text:\n{rt}"
        )

    # AC: boundary rules for reasoning_trace specify an end boundary
    def test_reasoning_trace_has_end_boundary(self, agent):
        rt = _field_section(agent["body"], "reasoning_trace")
        assert rt, (
            "Could not locate **reasoning_trace** field section in body"
        )
        assert "Boundary end" in rt, (
            "reasoning_trace extraction rules must specify a 'Boundary end'; "
            f"section text:\n{rt}"
        )

    # AC: reasoning_trace explicitly excludes interviewer turns
    def test_reasoning_trace_explicitly_excludes_interviewer_turns(self, agent):
        rt = _field_section(agent["body"], "reasoning_trace")
        assert rt, (
            "Could not locate **reasoning_trace** field section in body"
        )
        has_exclude_interviewer = bool(
            re.search(
                r"Exclude.*interviewer|interviewer.*[Ee]xclude",
                rt,
                re.DOTALL,
            )
        )
        assert has_exclude_interviewer, (
            "reasoning_trace rules must explicitly EXCLUDE interviewer turns; "
            "both 'Exclude' and 'interviewer' must appear in the reasoning_trace section. "
            f"Section text:\n{rt}"
        )

    # AC: reasoning_trace explicitly excludes approach_framework_text
    def test_reasoning_trace_explicitly_excludes_approach_framework_text(self, agent):
        rt = _field_section(agent["body"], "reasoning_trace")
        assert rt, (
            "Could not locate **reasoning_trace** field section in body"
        )
        assert "approach_framework_text" in rt, (
            "reasoning_trace rules must explicitly reference approach_framework_text "
            "to clarify it is excluded"
        )
        has_exclusion = bool(
            re.search(
                r"(?:Do NOT|Exclude|not include|exclude).*approach_framework_text",
                rt,
                re.IGNORECASE | re.DOTALL,
            )
        )
        assert has_exclusion, (
            "reasoning_trace rules must explicitly exclude approach_framework_text "
            "(e.g. 'Do NOT include approach_framework_text content here'); "
            f"section text:\n{rt}"
        )


# ---------------------------------------------------------------------------
# Group 2: parser-evaluator schema
# ---------------------------------------------------------------------------

class TestParserEvaluatorSchema:
    """Acceptance criteria for .claude/agents/parser-evaluator.md."""

    @pytest.fixture(scope="class")
    def agent(self):
        fm, body = _parse_agent(PARSER_EVALUATOR_PATH)
        return {"fm": fm, "body": body, "schema": _first_json_block(body)}

    # AC: agent file exists
    def test_file_exists(self):
        assert os.path.isfile(PARSER_EVALUATOR_PATH), (
            f"parser-evaluator agent file not found at {PARSER_EVALUATOR_PATH}"
        )

    # AC: model is sonnet (reasoning required for quality assessment)
    def test_model_is_sonnet(self, agent):
        model = agent["fm"].get("model", "")
        assert model == "sonnet", (
            f"parser-evaluator model must be 'sonnet' (reasoning required); got {model!r}"
        )

    # AC: output schema contains all 6 required top-level fields
    @pytest.mark.parametrize("field", [
        "verdict",
        "quality_score",
        "information_loss_pct",
        "checks",
        "failures",
        "improvement_hints",
    ])
    def test_output_schema_contains_required_field(self, agent, field):
        schema = agent["schema"]
        assert schema, "parser-evaluator has no JSON schema block"
        assert f'"{field}"' in schema, (
            f"parser-evaluator JSON output schema is missing required field: {field!r}"
        )

    # AC: checks object contains all 5 required sub-checks
    @pytest.mark.parametrize("sub_check", [
        "field_completeness",
        "information_loss",
        "boundary_accuracy",
        "speaker_attribution",
        "verbatim_constraint",
    ])
    def test_checks_contains_required_sub_check(self, agent, sub_check):
        schema = agent["schema"]
        assert f'"{sub_check}"' in schema, (
            f"parser-evaluator 'checks' object must contain sub-check: {sub_check!r}"
        )

    # AC: failures array items contain all 4 required fields
    @pytest.mark.parametrize("field", ["error_type", "field", "detail", "example"])
    def test_failures_items_contain_required_field(self, agent, field):
        schema = agent["schema"]
        assert f'"{field}"' in schema, (
            f"parser-evaluator failures array items must include field: {field!r}"
        )

    # AC: verdict must be one of PASS, FLAG, FAIL — all three must be documented
    @pytest.mark.parametrize("value", ["PASS", "FLAG", "FAIL"])
    def test_verdict_documents_valid_value(self, agent, value):
        assert value in agent["body"], (
            f"parser-evaluator must document '{value}' as a valid verdict value"
        )

    def test_verdict_schema_field_enumerates_all_three_values(self, agent):
        schema = agent["schema"]
        verdict_line = next(
            (line for line in schema.splitlines() if '"verdict"' in line), ""
        )
        assert verdict_line, "verdict field not found in the JSON schema block"
        for v in ("PASS", "FLAG", "FAIL"):
            assert v in verdict_line, (
                f"verdict schema annotation must enumerate '{v}'; "
                f"got line: {verdict_line!r}"
            )

    # AC: all 3 information-loss thresholds are documented
    def test_threshold_below_10_pct_is_acceptable(self, agent):
        assert re.search(r"<\s*10\s*%", agent["body"]), (
            "parser-evaluator must document the <10% information-loss threshold "
            "as acceptable"
        )

    def test_threshold_10_to_20_pct_is_flag(self, agent):
        # Accept both hyphen and en-dash
        assert re.search(r"10\s*[–\-]\s*20\s*%", agent["body"]), (
            "parser-evaluator must document the 10–20% information-loss threshold "
            "as FLAG"
        )

    def test_threshold_above_20_pct_is_fail(self, agent):
        assert re.search(r">\s*20\s*%", agent["body"]), (
            "parser-evaluator must document the >20% information-loss threshold "
            "as FAIL"
        )

    # AC: improvement_hints must be specific and actionable — the prompt must say
    #     "not generic advice" (or equivalent)
    def test_improvement_hints_constraint_not_generic(self, agent):
        assert "not generic" in agent["body"].lower(), (
            "parser-evaluator must constrain improvement_hints to be specific and "
            "actionable, explicitly rejecting generic advice (phrase 'not generic' "
            "must appear in the prompt)"
        )

    # AC: description states it does NOT score consultant quality
    def test_description_does_not_score_consultant_quality(self, agent):
        description = agent["fm"].get("description", "")
        has_negation = bool(
            re.search(
                r"do not score.*consultant|NOT score.*consultant",
                description,
                re.IGNORECASE,
            )
        )
        assert has_negation, (
            "parser-evaluator description must explicitly state it does NOT score "
            "the consultant's response quality; "
            f"got description: {description!r}"
        )


# ---------------------------------------------------------------------------
# Group 3: parser-fixer schema
# ---------------------------------------------------------------------------

class TestParserFixerSchema:
    """Acceptance criteria for .claude/agents/parser-fixer.md."""

    @pytest.fixture(scope="class")
    def agent(self):
        fm, body = _parse_agent(PARSER_FIXER_PATH)
        return {"fm": fm, "body": body, "schema": _first_json_block(body)}

    # AC: agent file exists
    def test_file_exists(self):
        assert os.path.isfile(PARSER_FIXER_PATH), (
            f"parser-fixer agent file not found at {PARSER_FIXER_PATH}"
        )

    # AC: model is sonnet
    def test_model_is_sonnet(self, agent):
        model = agent["fm"].get("model", "")
        assert model == "sonnet", (
            f"parser-fixer model must be 'sonnet'; got {model!r}"
        )

    # AC: output schema contains all 6 required top-level fields
    @pytest.mark.parametrize("field", [
        "patch_summary",
        "error_types_addressed",
        "patches",
        "regression_risk",
        "regression_note",
        "test_case",
    ])
    def test_output_schema_contains_required_field(self, agent, field):
        schema = agent["schema"]
        assert schema, "parser-fixer has no JSON schema block"
        assert f'"{field}"' in schema, (
            f"parser-fixer JSON output schema is missing required field: {field!r}"
        )

    # AC: each patch object contains all 5 required sub-fields
    @pytest.mark.parametrize("field", [
        "location",
        "section",
        "old_text",
        "new_text",
        "rationale",
    ])
    def test_patch_object_contains_required_field(self, agent, field):
        schema = agent["schema"]
        assert f'"{field}"' in schema, (
            f"parser-fixer patch object must include field: {field!r}"
        )

    # AC: old_text must be verbatim from the parser prompt (constraint present in agent)
    def test_old_text_verbatim_constraint_present(self, agent):
        body = agent["body"]
        has_constraint = bool(
            re.search(
                r"old_text.*verbatim|verbatim.*old_text",
                body,
                re.IGNORECASE | re.DOTALL,
            )
        )
        assert has_constraint, (
            "parser-fixer must contain a constraint that old_text must be verbatim "
            "from the current parser prompt"
        )

    # AC: regression_risk must be LOW, MEDIUM, or HIGH — all three values documented
    @pytest.mark.parametrize("value", ["LOW", "MEDIUM", "HIGH"])
    def test_regression_risk_documents_value(self, agent, value):
        schema = agent["schema"]
        assert value in schema, (
            f"parser-fixer regression_risk must enumerate '{value}' as a valid value "
            "in the schema"
        )

    def test_regression_risk_schema_field_enumerates_all_three_values(self, agent):
        schema = agent["schema"]
        risk_line = next(
            (line for line in schema.splitlines() if '"regression_risk"' in line), ""
        )
        assert risk_line, "regression_risk field not found in the JSON schema block"
        for v in ("LOW", "MEDIUM", "HIGH"):
            assert v in risk_line, (
                f"regression_risk schema annotation must enumerate '{v}'; "
                f"got line: {risk_line!r}"
            )

    # AC: description states it does NOT re-evaluate quality
    def test_description_does_not_reevaluate_quality(self, agent):
        description = agent["fm"].get("description", "")
        has_negation = bool(
            re.search(
                r"does\s+not\s+re.?evaluat|NOT\s+re.?evaluat",
                description,
                re.IGNORECASE,
            )
        )
        assert has_negation, (
            "parser-fixer description must state it does NOT re-evaluate quality; "
            f"got: {description!r}"
        )

    # AC: description states it is SEPARATE from evaluator (neutrality maintained)
    def test_description_states_separate_from_evaluator(self, agent):
        description = agent["fm"].get("description", "")
        assert re.search(r"[Ss]eparate from the evaluator", description), (
            "parser-fixer description must state 'Separate from the evaluator' "
            "to confirm neutrality is maintained; "
            f"got: {description!r}"
        )

    # AC: constraint present that patches must not change the output schema
    def test_patches_must_not_change_output_schema_constraint(self, agent):
        body = agent["body"]
        has_constraint = bool(
            re.search(
                r"[Dd]o not write patches that change the output schema",
                body,
            )
        )
        assert has_constraint, (
            "parser-fixer must contain the constraint: "
            "'Do not write patches that change the output schema'"
        )


# ---------------------------------------------------------------------------
# Group 4: pipeline coherence
# ---------------------------------------------------------------------------

class TestPipelineCoherence:
    """
    Acceptance criteria for the three-agent directed pipeline.

    All checks are static: they verify that the agent definitions encode
    the correct pipeline relationships.  No agents are invoked.
    """

    @pytest.fixture(scope="class")
    def parser_agent(self):
        fm, body = _parse_agent(TRANSCRIPT_PARSER_PATH)
        return {"fm": fm, "body": body, "schema": _first_json_block(body)}

    @pytest.fixture(scope="class")
    def evaluator_agent(self):
        fm, body = _parse_agent(PARSER_EVALUATOR_PATH)
        return {"fm": fm, "body": body, "schema": _first_json_block(body)}

    @pytest.fixture(scope="class")
    def fixer_agent(self):
        fm, body = _parse_agent(PARSER_FIXER_PATH)
        return {"fm": fm, "body": body, "schema": _first_json_block(body)}

    # AC: parser output has problem_statement and reasoning_trace (feed journey_coherence)
    def test_parser_output_contains_problem_statement_for_post_scorer(self, parser_agent):
        assert '"problem_statement"' in parser_agent["schema"], (
            "transcript-parser output schema must include problem_statement — "
            "this field feeds journey_coherence scoring in the post-scorer"
        )

    def test_parser_output_contains_reasoning_trace_for_post_scorer(self, parser_agent):
        assert '"reasoning_trace"' in parser_agent["schema"], (
            "transcript-parser output schema must include reasoning_trace — "
            "this field feeds journey_coherence scoring in the post-scorer"
        )

    # AC: evaluator receives two inputs, not one
    def test_evaluator_states_it_receives_two_inputs(self, evaluator_agent):
        body = evaluator_agent["body"]
        assert re.search(r"two inputs", body, re.IGNORECASE), (
            "parser-evaluator must explicitly state it receives two inputs"
        )

    def test_evaluator_first_input_is_parser_json_output(self, evaluator_agent):
        body = evaluator_agent["body"]
        has_first_input = bool(
            re.search(
                r"transcript.parser.*JSON|JSON.*transcript.parser|parser.*JSON\s+output",
                body,
                re.IGNORECASE,
            )
        )
        assert has_first_input, (
            "parser-evaluator first input must be the transcript-parser's JSON output"
        )

    def test_evaluator_second_input_is_raw_file_path(self, evaluator_agent):
        body = evaluator_agent["body"]
        has_second_input = bool(
            re.search(
                r"raw case file|original raw|file path",
                body,
                re.IGNORECASE,
            )
        )
        assert has_second_input, (
            "parser-evaluator second input must be the original raw case file path"
        )

    # AC: fixer receives two inputs (evaluator failure log + current parser prompt)
    def test_fixer_enumerates_two_numbered_inputs(self, fixer_agent):
        body = fixer_agent["body"]
        has_1 = bool(re.search(r"^\s*1\.", body, re.MULTILINE))
        has_2 = bool(re.search(r"^\s*2\.", body, re.MULTILINE))
        assert has_1 and has_2, (
            "parser-fixer must enumerate at least two numbered inputs "
            "(evaluator failure log and current parser prompt)"
        )

    def test_fixer_first_input_is_evaluator_failure_log(self, fixer_agent):
        body = fixer_agent["body"]
        has_failure_input = bool(
            re.search(
                r"parser.evaluator.*failure|failure.*log|failures.*array",
                body,
                re.IGNORECASE,
            )
        )
        assert has_failure_input, (
            "parser-fixer first input must be the parser-evaluator's failure log "
            "(failures array / improvement_hints)"
        )

    def test_fixer_second_input_is_current_parser_prompt(self, fixer_agent):
        body = fixer_agent["body"]
        has_prompt_input = bool(
            re.search(
                r"current parser.*prompt|parser.*system prompt|current.*prompt",
                body,
                re.IGNORECASE,
            )
        )
        assert has_prompt_input, (
            "parser-fixer second input must be the current parser system prompt"
        )

    # AC: directed loop — evaluator explicitly runs AFTER the parser
    def test_evaluator_description_runs_after_parser(self, evaluator_agent):
        description = evaluator_agent["fm"].get("description", "")
        assert re.search(
            r"[Rr]un after transcript.parser|after.*transcript.parser",
            description,
        ), (
            "parser-evaluator description must state it runs after transcript-parser "
            "(encodes the parser → evaluator directed edge); "
            f"got: {description!r}"
        )

    # AC: directed loop — fixer triggers from evaluator output (evaluator → fixer edge)
    def test_fixer_description_triggers_from_evaluator(self, fixer_agent):
        description = fixer_agent["fm"].get("description", "")
        assert re.search(
            r"[Tt]riggers when.*evaluator|evaluator.*returns\s+FAIL|evaluator.*FAIL",
            description,
        ), (
            "parser-fixer description must state it triggers when the evaluator "
            "returns FAIL or FLAG (encodes the evaluator → fixer directed edge); "
            f"got: {description!r}"
        )

    # AC: no cycles within a single evaluation run — fixer does NOT re-run the parser
    def test_fixer_does_not_run_the_parser_itself(self, fixer_agent):
        body = fixer_agent["body"]
        has_no_run_constraint = bool(
            re.search(
                r"[Yy]ou do NOT run the parser|do NOT run the parser",
                body,
            )
        )
        assert has_no_run_constraint, (
            "parser-fixer must state it does NOT run the parser itself — "
            "this prevents cycles within a single evaluation run; "
            "expected text like 'You do NOT run the parser' in the body"
        )

    # AC: fixer closes the loop via test_case handoff, not by directly re-evaluating
    def test_fixer_loop_closes_via_test_case_handoff(self, fixer_agent):
        schema = fixer_agent["schema"]
        assert '"test_case"' in schema, (
            "parser-fixer output must include a test_case field — this is the "
            "handoff that closes the directed loop back to the parser "
            "(fixer → parser edge via prompt patch + test_case)"
        )
