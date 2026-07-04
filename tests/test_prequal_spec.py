"""
Structural/content tests for rubrics/prequal_spec.yaml.

This is a SPEC-ONLY YAML file — no scoring logic, no LLM prompt templates.
These tests validate the YAML document itself (parseability, schema shape,
field presence, value correctness, and logical invariants) against the locked
acceptance criteria. No changes to the implementation are made here.

Every test function name maps directly to a stated acceptance criterion.
Run with:
    python -m pytest tests/test_prequal_spec.py -v

Style reference: tests/test_rubric_spec.py (unittest) — this file uses pytest
conventions as required by the acceptance criteria.
"""

import os
import re

import pytest
import yaml

PREQUAL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rubrics",
    "prequal_spec.yaml",
)

# ── Expected shapes ─────────────────────────────────────────────────────────
EXPECTED_TOP_LEVEL_KEYS = {
    "description",
    "io_shape",
    "checks",
    "conditioning_map",
    "fixtures",
    "neutrality_note",
}

EXPECTED_IO_INPUT_KEYS = {"prompt", "initial_framing", "interviewer_nudges"}

EXPECTED_IO_OUTPUT_KEYS = {
    "gate",
    "block_reason",
    "block_cta",
    "conditional_flag",
    "cardinality",
    "verifiability",
    "flags",
    "conditioners",
    "rationale",
}

EXPECTED_GATE_VALUES = ["PASS", "BLOCK", "CONDITIONAL"]
EXPECTED_CARDINALITY_VALUES = ["contradictory", "unique", "multiple"]
EXPECTED_VERIFIABILITY_VALUES = ["direct", "indirect", "counterfactual"]
EXPECTED_FLAG_KEYS = {"distributional", "intractable", "reflexive", "gameable"}

EXPECTED_FLAG_IDS = ["distributional", "intractable", "reflexive", "gameable"]

VALID_GATE_SET = set(EXPECTED_GATE_VALUES)
VALID_CARDINALITY_SET = set(EXPECTED_CARDINALITY_VALUES)
VALID_VERIFIABILITY_SET = set(EXPECTED_VERIFIABILITY_VALUES)

# Forbidden domain-specific terms — only checked in structural spec fields,
# NOT in example/fixture/opex_example fields.
FORBIDDEN_TERMS = [
    "storage",
    "logistics",
    "s&m",
    "selling & marketing",
    "selling and marketing",
    "cost center",
    "cost driver",
    "opex",
    "freight",
    "procurement",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_spec():
    with open(PREQUAL_PATH, "r") as fh:
        return yaml.safe_load(fh)


def _get_check(spec, check_id):
    for check in spec.get("checks", []) or []:
        if check.get("id") == check_id:
            return check
    return None


def _get_axis(classifier, axis_id):
    for axis in classifier.get("axes", []) or []:
        if axis.get("id") == axis_id:
            return axis
    return None


def _get_value(values_list, value_id):
    for v in values_list or []:
        if isinstance(v, dict) and v.get("id") == value_id:
            return v
    return None


def _get_flag(flags_list, flag_id):
    for f in flags_list or []:
        if isinstance(f, dict) and f.get("id") == flag_id:
            return f
    return None


def _collect_downstream_texts(das):
    """Collect all string values from a downstream_anchor_shifts mapping."""
    if not isinstance(das, dict):
        return []
    return [v for v in das.values() if isinstance(v, str)]


def _collect_structural_spec_texts(spec):
    """
    Collect all text from structural spec fields ONLY.

    Scanned fields: definition, classification_rule, downstream_anchor_shifts,
    gate_rules (conditions + consequences), mece_proof, set_when.
    Explicitly NOT scanned: fixtures.examples[*] (prompt, rationale),
    io_shape descriptions, opex_example fields.
    """
    texts = []

    for check in spec.get("checks", []) or []:
        # gate_rules (conditions lists + consequences strings)
        for _rule_key, rule_content in (check.get("gate_rules") or {}).items():
            if isinstance(rule_content, dict):
                conds = rule_content.get("conditions", [])
                if isinstance(conds, list):
                    texts.extend(c for c in conds if isinstance(c, str))
                consq = rule_content.get("consequences", "")
                if isinstance(consq, str):
                    texts.append(consq)
            elif isinstance(rule_content, str):
                texts.append(rule_content)

        # axes → values → definition, classification_rule, downstream_anchor_shifts
        for axis in check.get("axes", []) or []:
            mece = axis.get("mece_proof", "")
            if isinstance(mece, str):
                texts.append(mece)

            for val in axis.get("values", []) or []:
                if not isinstance(val, dict):
                    continue
                for field in ("definition", "classification_rule"):
                    text = val.get(field, "")
                    if isinstance(text, str):
                        texts.append(text)
                texts.extend(_collect_downstream_texts(val.get("downstream_anchor_shifts")))

        # flags → definition, set_when, downstream_anchor_shifts
        for flag in check.get("flags", []) or []:
            if not isinstance(flag, dict):
                continue
            for field in ("definition", "set_when"):
                text = flag.get(field, "")
                if isinstance(text, str):
                    texts.append(text)
            texts.extend(_collect_downstream_texts(flag.get("downstream_anchor_shifts")))

    return texts


# ── Module-level spec load ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def spec():
    return _load_spec()


@pytest.fixture(scope="module")
def well_posedness_gate(spec):
    return _get_check(spec, "well_posedness_gate")


@pytest.fixture(scope="module")
def problem_type_classifier(spec):
    return _get_check(spec, "problem_type_classifier")


@pytest.fixture(scope="module")
def cardinality_axis(problem_type_classifier):
    if problem_type_classifier is None:
        return None
    return _get_axis(problem_type_classifier, "cardinality_classifier")


@pytest.fixture(scope="module")
def verifiability_axis(problem_type_classifier):
    if problem_type_classifier is None:
        return None
    return _get_axis(problem_type_classifier, "verifiability_classifier")


@pytest.fixture(scope="module")
def classifier_flags(problem_type_classifier):
    if problem_type_classifier is None:
        return []
    return problem_type_classifier.get("flags") or []


@pytest.fixture(scope="module")
def examples(spec):
    return (spec.get("fixtures") or {}).get("examples") or []


# ════════════════════════════════════════════════════════════════════════════
# Group 1 — Top-level structure
# ════════════════════════════════════════════════════════════════════════════

class TestTopLevelStructure:
    """AC Group 1: File parseability and top-level keys."""

    def test_yaml_parses_without_error(self):
        """File parses as valid YAML without error."""
        try:
            data = _load_spec()
        except yaml.YAMLError as exc:
            pytest.fail(f"prequal_spec.yaml failed to parse as YAML: {exc}")
        assert isinstance(data, dict), "Top-level YAML document must be a mapping (dict)"
        assert data, "Parsed YAML document is empty"

    def test_top_level_keys_present(self, spec):
        """Top-level keys present: description, io_shape, checks, conditioning_map, fixtures, neutrality_note."""
        missing = EXPECTED_TOP_LEVEL_KEYS - set(spec.keys())
        assert not missing, (
            f"Top-level key(s) missing from prequal_spec.yaml: {sorted(missing)}"
        )

    def test_no_unexpected_top_level_keys(self, spec):
        """Edge case: no unknown top-level keys that indicate spec drift."""
        extra = set(spec.keys()) - EXPECTED_TOP_LEVEL_KEYS
        assert not extra, (
            f"Unexpected top-level key(s) found (spec may have drifted): {sorted(extra)}"
        )


# ════════════════════════════════════════════════════════════════════════════
# Group 2 — io_shape
# ════════════════════════════════════════════════════════════════════════════

class TestIOShape:
    """AC Group 2: io_shape input/output shapes."""

    @pytest.fixture(autouse=True)
    def _require_io_shape(self, spec):
        assert "io_shape" in spec, "io_shape key missing — Group 2 tests cannot run"
        self.io = spec["io_shape"]

    def test_io_shape_input_has_exactly_prompt_initial_framing_and_interviewer_nudges(self):
        """io_shape.input has exactly keys prompt, initial_framing, and interviewer_nudges."""
        inp = self.io.get("input")
        assert isinstance(inp, dict), "io_shape.input must be a mapping"
        assert set(inp.keys()) == EXPECTED_IO_INPUT_KEYS, (
            f"io_shape.input must have exactly {EXPECTED_IO_INPUT_KEYS}, "
            f"got {set(inp.keys())}"
        )

    def test_io_shape_output_has_exactly_required_keys(self):
        """io_shape.output has exactly the 9 required keys."""
        out = self.io.get("output")
        assert isinstance(out, dict), "io_shape.output must be a mapping"
        assert set(out.keys()) == EXPECTED_IO_OUTPUT_KEYS, (
            f"io_shape.output keys mismatch.\n"
            f"  Missing: {EXPECTED_IO_OUTPUT_KEYS - set(out.keys())}\n"
            f"  Extra:   {set(out.keys()) - EXPECTED_IO_OUTPUT_KEYS}"
        )

    def test_io_shape_output_gate_has_exactly_pass_block_conditional_values(self):
        """io_shape.output.gate has values list containing exactly [PASS, BLOCK, CONDITIONAL]."""
        gate = self.io["output"].get("gate", {})
        assert isinstance(gate, dict), "io_shape.output.gate must be a mapping"
        values = gate.get("values")
        assert isinstance(values, list), "io_shape.output.gate.values must be a list"
        assert sorted(values) == sorted(EXPECTED_GATE_VALUES), (
            f"io_shape.output.gate.values must be exactly {EXPECTED_GATE_VALUES}, got {values}"
        )
        assert len(values) == len(EXPECTED_GATE_VALUES), (
            f"io_shape.output.gate.values has duplicates or wrong count: {values}"
        )

    def test_io_shape_output_cardinality_has_exactly_contradictory_unique_multiple_values(self):
        """io_shape.output.cardinality has values list containing exactly [contradictory, unique, multiple]."""
        card = self.io["output"].get("cardinality", {})
        assert isinstance(card, dict), "io_shape.output.cardinality must be a mapping"
        values = card.get("values")
        assert isinstance(values, list), "io_shape.output.cardinality.values must be a list"
        assert sorted(values) == sorted(EXPECTED_CARDINALITY_VALUES), (
            f"io_shape.output.cardinality.values must be exactly {EXPECTED_CARDINALITY_VALUES}, "
            f"got {values}"
        )
        assert len(values) == 3, f"Cardinality values must have exactly 3 entries, got {len(values)}"

    def test_io_shape_output_verifiability_has_exactly_direct_indirect_counterfactual_values(self):
        """io_shape.output.verifiability has values list containing exactly [direct, indirect, counterfactual]."""
        verif = self.io["output"].get("verifiability", {})
        assert isinstance(verif, dict), "io_shape.output.verifiability must be a mapping"
        values = verif.get("values")
        assert isinstance(values, list), "io_shape.output.verifiability.values must be a list"
        assert sorted(values) == sorted(EXPECTED_VERIFIABILITY_VALUES), (
            f"io_shape.output.verifiability.values must be exactly {EXPECTED_VERIFIABILITY_VALUES}, "
            f"got {values}"
        )
        assert len(values) == 3, f"Verifiability values must have exactly 3 entries, got {len(values)}"

    def test_io_shape_output_flags_has_exactly_four_properties(self):
        """io_shape.output.flags has exactly 4 properties: distributional, intractable, reflexive, gameable."""
        flags = self.io["output"].get("flags", {})
        assert isinstance(flags, dict), "io_shape.output.flags must be a mapping"
        properties = flags.get("properties")
        assert isinstance(properties, dict), (
            "io_shape.output.flags.properties must be a mapping"
        )
        assert set(properties.keys()) == EXPECTED_FLAG_KEYS, (
            f"io_shape.output.flags.properties must be exactly {EXPECTED_FLAG_KEYS}, "
            f"got {set(properties.keys())}"
        )
        assert len(properties) == 4, (
            f"Expected exactly 4 flag properties, got {len(properties)}"
        )


# ════════════════════════════════════════════════════════════════════════════
# Group 3 — Well-posedness gate check
# ════════════════════════════════════════════════════════════════════════════

class TestWellPosednessGate:
    """AC Group 3: well_posedness_gate check structure."""

    def test_checks_has_well_posedness_gate_entry(self, spec):
        """checks is a list with at least one entry having id == 'well_posedness_gate'."""
        checks = spec.get("checks")
        assert isinstance(checks, list), "checks must be a list"
        ids = [c.get("id") for c in checks if isinstance(c, dict)]
        assert "well_posedness_gate" in ids, (
            f"No entry with id='well_posedness_gate' found in checks. Found ids: {ids}"
        )

    def test_well_posedness_gate_output_values_are_exactly_pass_block_conditional(
        self, well_posedness_gate
    ):
        """well_posedness_gate has output_values list containing exactly [PASS, BLOCK, CONDITIONAL]."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        ov = well_posedness_gate.get("output_values")
        assert isinstance(ov, list), "well_posedness_gate.output_values must be a list"
        assert sorted(ov) == sorted(EXPECTED_GATE_VALUES), (
            f"well_posedness_gate.output_values must be exactly {EXPECTED_GATE_VALUES}, got {ov}"
        )
        assert len(ov) == 3, f"Expected exactly 3 output_values, got {len(ov)}"

    def test_well_posedness_gate_sub_checks_has_at_least_three_entries_with_required_ids(
        self, well_posedness_gate
    ):
        """well_posedness_gate has sub_checks with at least 3 entries (falsifiability, question_alignment, constraint_type_declaration)."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        sub_checks = well_posedness_gate.get("sub_checks")
        assert isinstance(sub_checks, list), "well_posedness_gate.sub_checks must be a list"
        assert len(sub_checks) >= 3, (
            f"well_posedness_gate.sub_checks must have at least 3 entries, got {len(sub_checks)}"
        )
        sub_ids = {sc.get("id") for sc in sub_checks if isinstance(sc, dict)}
        for required_id in ("falsifiability", "question_alignment", "constraint_type_declaration"):
            assert required_id in sub_ids, (
                f"Required sub_check id '{required_id}' not found in well_posedness_gate.sub_checks. "
                f"Found: {sub_ids}"
            )

    def test_well_posedness_gate_gate_rules_has_pass_block_conditional_keys(
        self, well_posedness_gate
    ):
        """well_posedness_gate has gate_rules with keys PASS, BLOCK, CONDITIONAL."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        gate_rules = well_posedness_gate.get("gate_rules")
        assert isinstance(gate_rules, dict), "well_posedness_gate.gate_rules must be a mapping"
        for key in ("PASS", "BLOCK", "CONDITIONAL"):
            assert key in gate_rules, (
                f"well_posedness_gate.gate_rules missing key '{key}'. Found keys: {list(gate_rules.keys())}"
            )

    def test_well_posedness_gate_gate_rules_block_has_conditions_and_consequences(
        self, well_posedness_gate
    ):
        """well_posedness_gate.gate_rules.BLOCK has both conditions and consequences fields."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        gate_rules = well_posedness_gate.get("gate_rules", {})
        block_rule = gate_rules.get("BLOCK")
        assert isinstance(block_rule, dict), (
            "well_posedness_gate.gate_rules.BLOCK must be a mapping"
        )
        assert "conditions" in block_rule, (
            "well_posedness_gate.gate_rules.BLOCK missing 'conditions' field"
        )
        assert "consequences" in block_rule, (
            "well_posedness_gate.gate_rules.BLOCK missing 'consequences' field"
        )
        # Edge case: both fields must be non-empty
        assert block_rule["conditions"], "well_posedness_gate.gate_rules.BLOCK.conditions is empty"
        assert block_rule["consequences"], "well_posedness_gate.gate_rules.BLOCK.consequences is empty"

    def test_well_posedness_gate_has_block_cta_requirements(self, well_posedness_gate):
        """well_posedness_gate has a block_cta_requirements field (constitutional — must not be missing)."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        bca = well_posedness_gate.get("block_cta_requirements")
        assert bca is not None, (
            "well_posedness_gate.block_cta_requirements is missing — this is a constitutional field"
        )
        assert isinstance(bca, str) and bca.strip(), (
            "well_posedness_gate.block_cta_requirements must be a non-empty string"
        )

    def test_well_posedness_gate_documents_interviewer_directed_pruning_non_penalty_rule(
        self, well_posedness_gate
    ):
        """well_posedness_gate has a sub_check documenting the interviewer-directed-pruning non-penalty rule."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        sub_checks = well_posedness_gate.get("sub_checks") or []
        sub_ids = {sc.get("id") for sc in sub_checks if isinstance(sc, dict)}
        assert "interviewer_directed_pruning" in sub_ids, (
            "well_posedness_gate.sub_checks must include an "
            "'interviewer_directed_pruning' sub_check id. Found: "
            f"{sub_ids}"
        )
        sub_check = next(
            sc for sc in sub_checks
            if isinstance(sc, dict) and sc.get("id") == "interviewer_directed_pruning"
        )
        description = sub_check.get("description", "")
        assert re.search(r"interviewer", description, re.IGNORECASE), (
            "interviewer_directed_pruning sub_check must reference 'interviewer' "
            f"in its description; got: {description!r}"
        )
        assert re.search(r"CONDITIONAL", description), (
            "interviewer_directed_pruning sub_check must reference the "
            f"CONDITIONAL non-penalty rule; got: {description!r}"
        )

    def test_well_posedness_gate_has_data_declaration_sub_check_or_data_sufficiency_note(
        self, well_posedness_gate
    ):
        """well_posedness_gate has a data_declaration sub-check OR a data_sufficiency_note/equivalent."""
        assert well_posedness_gate is not None, "well_posedness_gate check not found"
        sub_checks = well_posedness_gate.get("sub_checks") or []
        sub_ids = {sc.get("id") for sc in sub_checks if isinstance(sc, dict)}

        has_data_declaration_sub_check = "data_declaration" in sub_ids
        has_data_sufficiency_note = (
            well_posedness_gate.get("data_sufficiency_note") is not None
            or well_posedness_gate.get("data_declaration_note") is not None
        )

        assert has_data_declaration_sub_check or has_data_sufficiency_note, (
            "well_posedness_gate must document the no-external-ground-truth constraint "
            "via a 'data_declaration' sub-check or a data_sufficiency_note/equivalent field. "
            f"sub_check ids found: {sub_ids}"
        )


# ════════════════════════════════════════════════════════════════════════════
# Group 4 — Problem type classifier: cardinality axis
# ════════════════════════════════════════════════════════════════════════════

class TestCardinalityAxis:
    """AC Group 4: cardinality axis of the problem_type_classifier."""

    def test_checks_has_problem_type_classifier_entry(self, spec):
        """checks has an entry for problem_type_classifier."""
        checks = spec.get("checks") or []
        ids = [c.get("id") for c in checks if isinstance(c, dict)]
        assert "problem_type_classifier" in ids, (
            f"No entry with id='problem_type_classifier' found in checks. Found ids: {ids}"
        )

    def test_cardinality_axis_has_exactly_three_values(self, cardinality_axis):
        """Exactly 3 cardinality values are defined: contradictory, unique, multiple."""
        assert cardinality_axis is not None, "cardinality_classifier axis not found"
        values = cardinality_axis.get("values")
        assert isinstance(values, list), "cardinality_classifier.values must be a list"
        val_ids = [v.get("id") for v in values if isinstance(v, dict)]
        assert sorted(val_ids) == sorted(EXPECTED_CARDINALITY_VALUES), (
            f"Cardinality axis must define exactly {EXPECTED_CARDINALITY_VALUES}, got {val_ids}"
        )
        assert len(val_ids) == 3, f"Cardinality axis must have exactly 3 values, got {len(val_ids)}"

    @pytest.mark.parametrize("value_id", EXPECTED_CARDINALITY_VALUES)
    def test_each_cardinality_value_has_definition_classification_rule_downstream_anchor_shifts(
        self, cardinality_axis, value_id
    ):
        """Each cardinality value has definition, classification_rule, and downstream_anchor_shifts."""
        assert cardinality_axis is not None, "cardinality_classifier axis not found"
        val = _get_value(cardinality_axis.get("values"), value_id)
        assert val is not None, f"Cardinality value '{value_id}' not found"
        for field in ("definition", "classification_rule", "downstream_anchor_shifts"):
            assert field in val, (
                f"Cardinality value '{value_id}' missing required field '{field}'"
            )
            assert val[field], f"Cardinality value '{value_id}'.{field} is empty"

    def test_cardinality_axis_has_mece_proof(self, cardinality_axis):
        """A mece_proof field is present for the cardinality axis."""
        assert cardinality_axis is not None, "cardinality_classifier axis not found"
        mece = cardinality_axis.get("mece_proof")
        assert mece is not None, "cardinality_classifier.mece_proof field is missing"
        assert isinstance(mece, str) and mece.strip(), (
            "cardinality_classifier.mece_proof must be a non-empty string"
        )

    def test_unique_cardinality_downstream_anchor_shifts_references_calibration(
        self, cardinality_axis
    ):
        """unique value's downstream_anchor_shifts references calibration (solution-verification stub)."""
        assert cardinality_axis is not None, "cardinality_classifier axis not found"
        unique_val = _get_value(cardinality_axis.get("values"), "unique")
        assert unique_val is not None, "Cardinality value 'unique' not found"
        das = unique_val.get("downstream_anchor_shifts")
        assert isinstance(das, dict), "'unique' downstream_anchor_shifts must be a mapping"
        assert "calibration" in das, (
            f"'unique' downstream_anchor_shifts must reference 'calibration'. "
            f"Keys found: {list(das.keys())}"
        )

    def test_contradictory_cardinality_downstream_anchor_shifts_references_tradeoff_awareness(
        self, cardinality_axis
    ):
        """contradictory value's downstream_anchor_shifts references tradeoff_awareness."""
        assert cardinality_axis is not None, "cardinality_classifier axis not found"
        contra_val = _get_value(cardinality_axis.get("values"), "contradictory")
        assert contra_val is not None, "Cardinality value 'contradictory' not found"
        das = contra_val.get("downstream_anchor_shifts")
        assert isinstance(das, dict), "'contradictory' downstream_anchor_shifts must be a mapping"
        assert "tradeoff_awareness" in das, (
            f"'contradictory' downstream_anchor_shifts must reference 'tradeoff_awareness'. "
            f"Keys found: {list(das.keys())}"
        )


# ════════════════════════════════════════════════════════════════════════════
# Group 5 — Problem type classifier: verifiability axis
# ════════════════════════════════════════════════════════════════════════════

class TestVerifiabilityAxis:
    """AC Group 5: verifiability axis of the problem_type_classifier."""

    def test_verifiability_axis_has_exactly_three_values(self, verifiability_axis):
        """Exactly 3 verifiability values defined: direct, indirect, counterfactual."""
        assert verifiability_axis is not None, "verifiability_classifier axis not found"
        values = verifiability_axis.get("values")
        assert isinstance(values, list), "verifiability_classifier.values must be a list"
        val_ids = [v.get("id") for v in values if isinstance(v, dict)]
        assert sorted(val_ids) == sorted(EXPECTED_VERIFIABILITY_VALUES), (
            f"Verifiability axis must define exactly {EXPECTED_VERIFIABILITY_VALUES}, got {val_ids}"
        )
        assert len(val_ids) == 3, (
            f"Verifiability axis must have exactly 3 values, got {len(val_ids)}"
        )

    @pytest.mark.parametrize("value_id", EXPECTED_VERIFIABILITY_VALUES)
    def test_each_verifiability_value_has_definition_classification_rule_downstream_anchor_shifts(
        self, verifiability_axis, value_id
    ):
        """Each verifiability value has definition, classification_rule, and downstream_anchor_shifts."""
        assert verifiability_axis is not None, "verifiability_classifier axis not found"
        val = _get_value(verifiability_axis.get("values"), value_id)
        assert val is not None, f"Verifiability value '{value_id}' not found"
        for field in ("definition", "classification_rule", "downstream_anchor_shifts"):
            assert field in val, (
                f"Verifiability value '{value_id}' missing required field '{field}'"
            )
            assert val[field], f"Verifiability value '{value_id}'.{field} is empty"

    def test_verifiability_axis_has_mece_proof(self, verifiability_axis):
        """A mece_proof field is present for the verifiability axis."""
        assert verifiability_axis is not None, "verifiability_classifier axis not found"
        mece = verifiability_axis.get("mece_proof")
        assert mece is not None, "verifiability_classifier.mece_proof field is missing"
        assert isinstance(mece, str) and mece.strip(), (
            "verifiability_classifier.mece_proof must be a non-empty string"
        )

    def test_counterfactual_verifiability_downstream_anchor_shifts_references_feasibility_and_calibration(
        self, verifiability_axis
    ):
        """counterfactual value's downstream_anchor_shifts references both feasibility and calibration."""
        assert verifiability_axis is not None, "verifiability_classifier axis not found"
        cf_val = _get_value(verifiability_axis.get("values"), "counterfactual")
        assert cf_val is not None, "Verifiability value 'counterfactual' not found"
        das = cf_val.get("downstream_anchor_shifts")
        assert isinstance(das, dict), "'counterfactual' downstream_anchor_shifts must be a mapping"
        for required_key in ("feasibility", "calibration"):
            assert required_key in das, (
                f"'counterfactual' downstream_anchor_shifts must reference '{required_key}'. "
                f"Keys found: {list(das.keys())}"
            )


# ════════════════════════════════════════════════════════════════════════════
# Group 6 — Flags
# ════════════════════════════════════════════════════════════════════════════

class TestFlags:
    """AC Group 6: flags defined in problem_type_classifier."""

    def test_exactly_four_flags_defined(self, classifier_flags):
        """Exactly 4 flags defined: distributional, intractable, reflexive, gameable."""
        assert isinstance(classifier_flags, list), "problem_type_classifier.flags must be a list"
        flag_ids = [f.get("id") for f in classifier_flags if isinstance(f, dict)]
        assert sorted(flag_ids) == sorted(EXPECTED_FLAG_IDS), (
            f"Must define exactly {EXPECTED_FLAG_IDS}, got {flag_ids}"
        )
        assert len(flag_ids) == 4, f"Expected exactly 4 flags, got {len(flag_ids)}"

    @pytest.mark.parametrize("flag_id", EXPECTED_FLAG_IDS)
    def test_each_flag_has_definition_set_when_downstream_anchor_shifts(
        self, classifier_flags, flag_id
    ):
        """Each flag has definition, set_when, and downstream_anchor_shifts."""
        flag = _get_flag(classifier_flags, flag_id)
        assert flag is not None, f"Flag '{flag_id}' not found in classifier flags"
        for field in ("definition", "set_when", "downstream_anchor_shifts"):
            assert field in flag, (
                f"Flag '{flag_id}' missing required field '{field}'"
            )
            assert flag[field], f"Flag '{flag_id}'.{field} is empty"

    def test_gameable_flag_downstream_anchor_shifts_references_tradeoff_awareness(
        self, classifier_flags
    ):
        """gameable flag's downstream_anchor_shifts references tradeoff_awareness."""
        flag = _get_flag(classifier_flags, "gameable")
        assert flag is not None, "Flag 'gameable' not found"
        das = flag.get("downstream_anchor_shifts")
        assert isinstance(das, dict), "'gameable' downstream_anchor_shifts must be a mapping"
        assert "tradeoff_awareness" in das, (
            f"'gameable' downstream_anchor_shifts must reference 'tradeoff_awareness'. "
            f"Keys found: {list(das.keys())}"
        )

    def test_reflexive_flag_downstream_anchor_shifts_references_tradeoff_awareness_or_feasibility(
        self, classifier_flags
    ):
        """reflexive flag's downstream_anchor_shifts references tradeoff_awareness or feasibility."""
        flag = _get_flag(classifier_flags, "reflexive")
        assert flag is not None, "Flag 'reflexive' not found"
        das = flag.get("downstream_anchor_shifts")
        assert isinstance(das, dict), "'reflexive' downstream_anchor_shifts must be a mapping"
        assert "tradeoff_awareness" in das or "feasibility" in das, (
            f"'reflexive' downstream_anchor_shifts must reference 'tradeoff_awareness' or "
            f"'feasibility'. Keys found: {list(das.keys())}"
        )


# ════════════════════════════════════════════════════════════════════════════
# Group 7 — Conditioning map
# ════════════════════════════════════════════════════════════════════════════

class TestConditioningMap:
    """AC Group 7: conditioning_map structure and required rules."""

    @pytest.fixture(autouse=True)
    def _require_conditioning_map(self, spec):
        assert "conditioning_map" in spec, "conditioning_map key missing — Group 7 tests cannot run"
        self.cm = spec["conditioning_map"]

    def test_conditioning_map_rules_has_at_least_five_entries(self):
        """conditioning_map has a rules list with at least 5 entries."""
        rules = self.cm.get("rules")
        assert isinstance(rules, list), "conditioning_map.rules must be a list"
        assert len(rules) >= 5, (
            f"conditioning_map.rules must have at least 5 entries, got {len(rules)}"
        )

    def test_conditioning_map_has_rule_with_contradictory_condition(self):
        """At least one rule has condition containing 'contradictory'."""
        rules = self.cm.get("rules") or []
        matching = [r for r in rules if "contradictory" in str(r.get("condition", ""))]
        assert matching, (
            "No conditioning_map rule has 'contradictory' in its condition. "
            f"Conditions found: {[r.get('condition') for r in rules]}"
        )

    def test_conditioning_map_has_rule_with_unique_and_direct_condition(self):
        """At least one rule has condition containing both 'unique' and 'direct' (solution-verification stub rule)."""
        rules = self.cm.get("rules") or []
        matching = [
            r for r in rules
            if "unique" in str(r.get("condition", "")) and "direct" in str(r.get("condition", ""))
        ]
        assert matching, (
            "No conditioning_map rule has both 'unique' and 'direct' in its condition. "
            f"Conditions found: {[r.get('condition') for r in rules]}"
        )

    def test_conditioning_map_has_rule_with_counterfactual_condition(self):
        """At least one rule has condition containing 'counterfactual'."""
        rules = self.cm.get("rules") or []
        matching = [r for r in rules if "counterfactual" in str(r.get("condition", ""))]
        assert matching, (
            "No conditioning_map rule has 'counterfactual' in its condition. "
            f"Conditions found: {[r.get('condition') for r in rules]}"
        )

    def test_every_conditioning_map_rule_has_condition_and_modifies(self):
        """Every rule has both condition and modifies fields."""
        rules = self.cm.get("rules") or []
        assert rules, "conditioning_map.rules is empty"
        for i, rule in enumerate(rules):
            assert isinstance(rule, dict), f"Rule at index {i} is not a mapping"
            assert "condition" in rule, (
                f"Rule at index {i} missing 'condition' field: {rule}"
            )
            assert "modifies" in rule, (
                f"Rule at index {i} missing 'modifies' field: {rule}"
            )
            assert rule["condition"], f"Rule at index {i} 'condition' is empty"
            assert rule["modifies"], f"Rule at index {i} 'modifies' is empty"


# ════════════════════════════════════════════════════════════════════════════
# Group 8 — Fixtures
# ════════════════════════════════════════════════════════════════════════════

class TestFixtures:
    """AC Group 8: fixtures.examples structure and content."""

    def test_fixtures_examples_has_at_least_three_entries(self, examples):
        """fixtures has an examples list with at least 3 entries."""
        assert isinstance(examples, list), "fixtures.examples must be a list"
        assert len(examples) >= 3, (
            f"fixtures.examples must have at least 3 entries, got {len(examples)}"
        )

    def test_every_fixture_has_required_fields(self, examples):
        """Every fixture has id, source, prompt, expected, rationale."""
        assert examples, "fixtures.examples is empty — cannot check required fields"
        for fixture in examples:
            assert isinstance(fixture, dict), f"Fixture entry is not a mapping: {fixture}"
            fid = fixture.get("id", "<unknown>")
            for field in ("id", "source", "prompt", "expected", "rationale"):
                assert field in fixture, (
                    f"Fixture '{fid}' missing required field '{field}'"
                )
                assert fixture[field] is not None, (
                    f"Fixture '{fid}'.{field} is None"
                )

    def test_every_fixture_expected_has_exactly_required_keys(self, examples):
        """Every fixture's expected dict has exactly these keys: gate, cardinality, verifiability, flags."""
        required = {"gate", "cardinality", "verifiability", "flags"}
        for fixture in examples:
            fid = fixture.get("id", "<unknown>")
            expected = fixture.get("expected")
            assert isinstance(expected, dict), f"Fixture '{fid}'.expected must be a mapping"
            assert set(expected.keys()) == required, (
                f"Fixture '{fid}'.expected keys mismatch.\n"
                f"  Missing: {required - set(expected.keys())}\n"
                f"  Extra:   {set(expected.keys()) - required}"
            )

    def test_every_fixture_expected_flags_has_exactly_four_keys(self, examples):
        """Every fixture's expected.flags has exactly 4 keys: distributional, intractable, reflexive, gameable."""
        required_flag_keys = {"distributional", "intractable", "reflexive", "gameable"}
        for fixture in examples:
            fid = fixture.get("id", "<unknown>")
            flags = (fixture.get("expected") or {}).get("flags")
            assert isinstance(flags, dict), f"Fixture '{fid}'.expected.flags must be a mapping"
            assert set(flags.keys()) == required_flag_keys, (
                f"Fixture '{fid}'.expected.flags must have exactly {required_flag_keys}, "
                f"got {set(flags.keys())}"
            )
            assert len(flags) == 4, (
                f"Fixture '{fid}'.expected.flags must have exactly 4 keys, got {len(flags)}"
            )

    def test_at_least_one_primary_operator_fixture_has_neutrality_flag(self, examples):
        """At least one fixture has source == 'primary_operator' and has a neutrality_flag field."""
        primary_with_flag = [
            f for f in examples
            if f.get("source") == "primary_operator" and "neutrality_flag" in f
        ]
        primary_all = [f for f in examples if f.get("source") == "primary_operator"]
        assert primary_all, (
            "No fixture with source='primary_operator' found — neutrality discipline requires at least one"
        )
        assert primary_with_flag, (
            f"Fixture(s) with source='primary_operator' exist but none have a 'neutrality_flag' field. "
            f"Found primary_operator fixtures: {[f.get('id') for f in primary_all]}"
        )

    def test_at_least_two_independent_source_fixtures(self, examples):
        """At least two fixtures have source == 'independent'."""
        independent = [f for f in examples if f.get("source") == "independent"]
        assert len(independent) >= 2, (
            f"At least 2 fixtures must have source='independent' (neutrality discipline). "
            f"Found {len(independent)}: {[f.get('id') for f in independent]}"
        )

    def test_all_fixture_gate_values_are_valid(self, examples):
        """All fixture gate values are in [PASS, BLOCK, CONDITIONAL]."""
        for fixture in examples:
            fid = fixture.get("id", "<unknown>")
            gate = (fixture.get("expected") or {}).get("gate")
            assert gate in VALID_GATE_SET, (
                f"Fixture '{fid}'.expected.gate value '{gate}' is not in {VALID_GATE_SET}"
            )

    def test_all_fixture_cardinality_values_are_valid(self, examples):
        """All fixture cardinality values are in [contradictory, unique, multiple]."""
        for fixture in examples:
            fid = fixture.get("id", "<unknown>")
            card = (fixture.get("expected") or {}).get("cardinality")
            assert card in VALID_CARDINALITY_SET, (
                f"Fixture '{fid}'.expected.cardinality value '{card}' is not in {VALID_CARDINALITY_SET}"
            )

    def test_all_fixture_verifiability_values_are_valid(self, examples):
        """All fixture verifiability values are in [direct, indirect, counterfactual]."""
        for fixture in examples:
            fid = fixture.get("id", "<unknown>")
            verif = (fixture.get("expected") or {}).get("verifiability")
            assert verif in VALID_VERIFIABILITY_SET, (
                f"Fixture '{fid}'.expected.verifiability value '{verif}' is not in {VALID_VERIFIABILITY_SET}"
            )


# ════════════════════════════════════════════════════════════════════════════
# Group 9 — Neutrality and domain-independence
# ════════════════════════════════════════════════════════════════════════════

class TestNeutralityAndDomainIndependence:
    """AC Group 9: neutrality note and domain-independence of structural fields."""

    def test_neutrality_note_is_present_and_non_empty(self, spec):
        """neutrality_note is present and non-empty."""
        note = spec.get("neutrality_note")
        assert note is not None, "neutrality_note key is missing from prequal_spec.yaml"
        assert isinstance(note, str), "neutrality_note must be a string"
        assert re.sub(r"\s+", " ", note).strip(), (
            "neutrality_note is present but contains only whitespace"
        )

    def test_neutrality_note_contains_word_independent(self, spec):
        """neutrality_note contains the word 'independent' (referring to independent validation)."""
        note = spec.get("neutrality_note", "")
        assert "independent" in note.lower(), (
            f"neutrality_note must contain the word 'independent' (referring to independent "
            f"validation). Current value:\n{note!r}"
        )

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_opex_terms_in_structural_spec_fields(self, spec, term):
        """No OPEX-specific terms appear in definition, classification_rule, downstream_anchor_shifts, gate_rules, or mece_proof fields."""
        structural_texts = _collect_structural_spec_texts(spec)
        violations = []
        for text in structural_texts:
            if term in text.lower():
                # Truncate for readability in failure output
                snippet = text[:120].replace("\n", " ")
                violations.append(f"  ...{snippet!r}...")
        assert not violations, (
            f"Forbidden OPEX term '{term}' found in structural spec field(s):\n"
            + "\n".join(violations)
            + "\nMove domain-specific language to opex_example: or fixture fields only."
        )
