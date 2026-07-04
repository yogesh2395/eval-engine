"""
Structural/content tests for rubrics/rubric_spec.yaml.

This is a SPEC-ONLY file -- there is no scorer implementation to invoke.
These tests therefore validate the YAML document itself (parseability,
schema shape, and content thresholds) against the locked acceptance
criteria, rather than any runtime behavior.

Tool choice: plain Python (stdlib `unittest` + PyYAML) with assert-style
checks via unittest's assertion methods. No pytest is installed in this
environment and no test runner is yet configured in the repo, so this is
the lightest reasonable option that still gives clear pass/fail output
per criterion. PyYAML is already available in the environment.

Run with:
    python3 -m unittest tests/test_rubric_spec.py -v
or simply:
    python3 tests/test_rubric_spec.py

--------------------------------------------------------------------------
The rubric is now a domain-independent constitution. Level anchors are
abstract and structural -- no OPEX/cost-center/logistics/S&M/storage
language appears in the anchor text. Concrete domain instantiations are
produced by a separate generator layer. OPEX references are confined to
the top-level `example_scenario:` field (labeled as a placeholder) and
per-criterion `opex_example:` documentation fields.

Mechanical "no vague language" proxy (documented per instructions, used
for AC #1 and AC #5):

"Vagueness" is not directly machine-checkable, so each level anchor text
is required to pass ALL of the following mechanical proxies:

  1. Minimum length: at least 40 characters (after whitespace collapse).
     Anchors like "good diagnosis" or "shows some awareness" are short;
     genuine concrete anchors with structural thresholds run much longer
     in this spec (observed: shortest anchor is ~120 chars). 40 chars is
     a deliberately generous floor that would still reject one-line vague
     filler, while not being so tight it could reject a legitimately terse
     but concrete anchor.

  2. Quantifiable/falsifiable marker: must contain at least one of:
       - a digit (e.g. "2 of 3", "1 of 3"),
       - or "≥" (the ≥ symbol, used as a count marker in abstract anchors
         such as "≥1", "≥2", "≥3" throughout the constitution),
       - or one of the phrases: "at least", "all " (lowercase with trailing
         space -- matches "all identified", "all proposed", etc. while
         avoiding false matches on "overall"), "all 3", "each", "every",
         "no individual", "no root cause", "no tradeoffs".
     This proxies the "discrete, falsifiable threshold" requirement
     (AC #1, AC #5) -- i.e. the anchor states a checkable count/condition
     rather than just an adjective like "good" or "strong".
     This check applies ONLY to levels 3-5 of each criterion. Levels 1-2
     intentionally describe the vague/generic/absent diagnostic behavior
     that the higher levels are contrasted against (e.g. "no decomposition"
     or "gestures at risk in vague terms... without naming a specific
     tradeoff") -- by definition they describe the *absence* of a
     falsifiable count, so requiring one of them would be incoherent.

     CONDITIONAL-CRITERIA EXEMPTION: Criteria whose YAML entry has a
     `conditional` field present (currently: journey_coherence, calibration)
     are exempt from proxy #2. Their anchors describe arc coherence and
     confidence calibration posture, not falsifiable count thresholds.
     Requiring a digit or count marker in those anchors would be incoherent
     -- the same rationale as the level 1-2 exemption above.

These proxies are necessarily approximate (a human could still write a
technically-passing anchor that is qualitatively vague, or vice versa),
but they directly operationalize the criteria's own stated examples
(e.g. ">=2 of 3 named sub-components + >=1 causal why question") and
should let a validator quickly judge if the proxy is reasonable.
--------------------------------------------------------------------------
"""

import os
import re
import unittest

import yaml

RUBRIC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rubrics",
    "rubric_spec.yaml",
)

EXPECTED_CRITERION_KEYS = [
    "decomposition",
    "root_cause",
    "tradeoff_awareness",
    "materiality",
    "evidentiary_grounding",
    "feasibility",
    "journey_coherence",
    "calibration",
]
EXPECTED_LEVELS = [1, 2, 3, 4, 5]

FALSIFIABLE_MARKERS = [
    "at least",
    "all ",
    "all 3",
    "each",
    "every",
    "no individual",
    "no root cause",
    "no tradeoffs",
    "≥",
]

MIN_ANCHOR_LENGTH = 40


def _load_rubric():
    with open(RUBRIC_PATH, "r") as f:
        return yaml.safe_load(f)


def _collapse_ws(text):
    return re.sub(r"\s+", " ", text).strip()


def _has_digit(text):
    return bool(re.search(r"\d", text))


def _has_falsifiable_marker(text):
    lowered = text.lower()
    return _has_digit(text) or any(marker in lowered for marker in FALSIFIABLE_MARKERS)



class TestRubricSpecIsParseable(unittest.TestCase):
    """AC #7: The file is well-formed/parseable YAML."""

    def test_file_exists(self):
        self.assertTrue(
            os.path.isfile(RUBRIC_PATH), f"Expected rubric file at {RUBRIC_PATH}"
        )

    def test_yaml_parses_without_error(self):
        try:
            data = _load_rubric()
        except yaml.YAMLError as e:
            self.fail(f"rubric_spec.yaml failed to parse as YAML: {e}")
        self.assertIsInstance(data, dict, "Top-level YAML document must be a mapping")

    def test_yaml_parses_to_nonempty_document(self):
        data = _load_rubric()
        self.assertTrue(data, "Parsed YAML document is empty")


class TestCriteriaCountAndKeys(unittest.TestCase):
    """
    AC #1 (count/non-overlap part) and AC #2 (exact keys).
    """

    @classmethod
    def setUpClass(cls):
        cls.data = _load_rubric()
        cls.criteria = cls.data.get("criteria")

    def test_criteria_key_present(self):
        self.assertIsNotNone(self.criteria, "Top-level `criteria` key is missing")
        self.assertIsInstance(self.criteria, list, "`criteria` must be a list")

    def test_criterion_count(self):
        self.assertEqual(
            len(self.criteria),
            8,
            f"Expected exactly 8 criteria, found {len(self.criteria)}",
        )

    def test_criterion_keys_are_exact_expected_set(self):
        keys = [c.get("key") for c in self.criteria]
        self.assertEqual(
            keys,
            EXPECTED_CRITERION_KEYS,
            f"Expected criterion keys {EXPECTED_CRITERION_KEYS} in order, got {keys}",
        )

    def test_criterion_keys_are_unique_non_overlapping(self):
        keys = [c.get("key") for c in self.criteria]
        self.assertEqual(
            len(keys),
            len(set(keys)),
            f"Criterion keys are not unique (overlap detected): {keys}",
        )

    def test_criteria_have_distinct_descriptions(self):
        """Sanity check for 'non-overlapping': descriptions should not be
        duplicates of one another (a crude but mechanical proxy for
        criteria actually measuring different things)."""
        descriptions = [
            _collapse_ws(c.get("description", "")) for c in self.criteria
        ]
        self.assertEqual(
            len(descriptions),
            len(set(descriptions)),
            "Two or more criteria have identical descriptions",
        )


class TestCriterionLevelsCompleteness(unittest.TestCase):
    """AC #6: Every criterion has levels 1-5 present, each non-empty text."""

    @classmethod
    def setUpClass(cls):
        cls.data = _load_rubric()
        cls.criteria = cls.data.get("criteria", [])

    def test_every_criterion_has_levels_dict(self):
        for c in self.criteria:
            with self.subTest(criterion=c.get("key")):
                self.assertIn("levels", c, f"Criterion {c.get('key')} missing `levels`")
                self.assertIsInstance(
                    c["levels"], dict, f"Criterion {c.get('key')} `levels` must be a mapping"
                )

    def test_every_criterion_has_levels_1_through_5(self):
        for c in self.criteria:
            key = c.get("key")
            levels = c.get("levels", {})
            with self.subTest(criterion=key):
                present_levels = sorted(levels.keys())
                self.assertEqual(
                    present_levels,
                    EXPECTED_LEVELS,
                    f"Criterion {key} must have exactly levels 1-5, found {present_levels}",
                )

    def test_every_level_anchor_is_nonempty_text(self):
        for c in self.criteria:
            key = c.get("key")
            levels = c.get("levels", {})
            for level_num in EXPECTED_LEVELS:
                with self.subTest(criterion=key, level=level_num):
                    anchor = levels.get(level_num)
                    self.assertIsInstance(
                        anchor,
                        str,
                        f"Criterion {key} level {level_num} must be a string",
                    )
                    self.assertTrue(
                        _collapse_ws(anchor),
                        f"Criterion {key} level {level_num} anchor is empty/whitespace-only",
                    )


class TestAnchorsAreConcreteNotVague(unittest.TestCase):
    """
    AC #1 ("no vague... language -- anchors must contain concrete,
    checkable thresholds") and AC #5 (level-3 anchors specifically must
    spell out an explicit, falsifiable threshold).

    See module docstring for the documented mechanical proxy used here.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = _load_rubric()
        cls.criteria = cls.data.get("criteria", [])

    def test_all_level_anchors_meet_min_length(self):
        for c in self.criteria:
            key = c.get("key")
            for level_num, anchor in c.get("levels", {}).items():
                with self.subTest(criterion=key, level=level_num):
                    collapsed = _collapse_ws(anchor)
                    self.assertGreaterEqual(
                        len(collapsed),
                        MIN_ANCHOR_LENGTH,
                        f"Criterion {key} level {level_num} anchor is suspiciously "
                        f"short ({len(collapsed)} chars), may be vague: {collapsed!r}",
                    )

    def test_level_3_through_5_anchors_have_falsifiable_marker(self):
        """AC #5 requires an explicit, falsifiable threshold starting at
        level 3 ('meets standard') and above (4, 5).

        Levels 1 and 2 are deliberately exempt from this check: those
        anchors describe vague/generic/absent diagnostic behavior (e.g.
        "no decomposition", "gestures at risk in vague terms... without
        naming a specific tradeoff") -- they are describing the *absence*
        of a falsifiable count, so requiring one of them in the anchor text
        itself would be incoherent. Only levels 3-5 are required to spell
        out a concrete, checkable bar.

        CONDITIONAL-CRITERIA EXEMPTION: Criteria with a `conditional` field
        in their YAML entry (currently: journey_coherence, calibration) are
        also exempt. Their anchors describe diagnostic arc coherence and
        confidence calibration posture, not OPEX-specific falsifiable count
        thresholds -- requiring a digit or count marker in those anchors
        would be incoherent (same rationale as the levels 1-2 exemption).
        """
        for c in self.criteria:
            # Conditional criteria anchors describe arc coherence and confidence
            # calibration posture, not OPEX count thresholds -- exempted.
            if c.get("conditional") is not None:
                continue
            key = c.get("key")
            for level_num, anchor in c.get("levels", {}).items():
                if level_num in (1, 2):
                    continue
                with self.subTest(criterion=key, level=level_num):
                    self.assertTrue(
                        _has_falsifiable_marker(anchor),
                        f"Criterion {key} level {level_num} anchor lacks a "
                        f"quantifiable/falsifiable marker (digit or at least/all/each/"
                        f"every/no-X phrase), may be vague: {anchor!r}",
                    )

    def test_level_3_anchors_spell_out_explicit_falsifiable_threshold(self):
        """AC #5 specifically calls out level-3 ('meets standard') anchors.

        Proxy: level-3 text must (a) contain the literal phrase
        'Meets standard' (this spec's own convention for flagging the
        threshold line) and (b) contain a falsifiable count marker -- either
        a digit-based count (e.g. '2 of 3') or a spelled-out quantifier
        ('at least one', 'all 3', etc., via _has_falsifiable_marker) --
        establishing a concrete, checkable bar, not just prose like 'shows
        reasonable diagnostic ability'.

        CONDITIONAL-CRITERIA EXEMPTION: Criteria with a `conditional` field
        in their YAML entry (currently: journey_coherence, calibration) are
        exempt from the falsifiable-marker requirement (b). Their level-3
        anchors describe a confidence posture ('meets standard' for
        calibration) or arc coherence (journey_coherence), not a countable
        OPEX threshold. Requiring a digit or count marker would be
        incoherent. The 'Meets standard' label requirement (a) still applies.
        """
        for c in self.criteria:
            key = c.get("key")
            level_3_anchor = c.get("levels", {}).get(3, "")
            is_conditional = c.get("conditional") is not None
            with self.subTest(criterion=key):
                self.assertIn(
                    "Meets standard",
                    level_3_anchor,
                    f"Criterion {key} level 3 anchor does not explicitly flag "
                    f"itself as the 'meets standard' threshold: {level_3_anchor!r}",
                )
                if not is_conditional:
                    # Conditional criteria anchors describe confidence posture or
                    # arc coherence, not countable OPEX thresholds -- exempted.
                    self.assertTrue(
                        _has_falsifiable_marker(level_3_anchor),
                        f"Criterion {key} level 3 anchor lacks a numeric/countable "
                        f"threshold (e.g. '2 of 3', 'at least one'): {level_3_anchor!r}",
                    )


class TestJustificationRequirements(unittest.TestCase):
    """AC #3: justification_requirements documents (a) naming driving
    criteria, (b) 2-3 direct quotes, (c) 150-300 words."""

    @classmethod
    def setUpClass(cls):
        cls.data = _load_rubric()
        cls.reqs = cls.data.get("justification_requirements")

    def test_justification_requirements_key_present(self):
        self.assertIsNotNone(
            self.reqs, "Top-level `justification_requirements` key is missing"
        )
        self.assertIsInstance(
            self.reqs, list, "`justification_requirements` must be a list"
        )

    def _find_req(self, req_id):
        for r in self.reqs:
            if r.get("id") == req_id:
                return r
        return None

    def test_names_driving_criteria_requirement_present(self):
        req = self._find_req("names_driving_criteria")
        self.assertIsNotNone(
            req,
            "No justification_requirements entry documents naming the "
            "driving criterion/criteria (expected id 'names_driving_criteria')",
        )
        self.assertTrue(
            _collapse_ws(req.get("description", "")),
            "names_driving_criteria requirement has empty description",
        )

    def test_direct_quotes_requirement_present_with_2_to_3_count(self):
        req = self._find_req("direct_quotes")
        self.assertIsNotNone(
            req,
            "No justification_requirements entry documents direct quotes "
            "(expected id 'direct_quotes')",
        )
        self.assertEqual(
            req.get("quote_count_min"),
            2,
            f"direct_quotes quote_count_min should be 2, got {req.get('quote_count_min')}",
        )
        self.assertEqual(
            req.get("quote_count_max"),
            3,
            f"direct_quotes quote_count_max should be 3, got {req.get('quote_count_max')}",
        )

    def test_length_requirement_present_with_150_to_300_words(self):
        req = self._find_req("length")
        self.assertIsNotNone(
            req,
            "No justification_requirements entry documents word-count length "
            "(expected id 'length')",
        )
        self.assertEqual(
            req.get("word_count_min"),
            150,
            f"length word_count_min should be 150, got {req.get('word_count_min')}",
        )
        self.assertEqual(
            req.get("word_count_max"),
            300,
            f"length word_count_max should be 300, got {req.get('word_count_max')}",
        )

    def test_exactly_three_justification_requirements_no_more_no_less(self):
        ids = [r.get("id") for r in self.reqs]
        self.assertEqual(
            sorted(ids),
            sorted(["names_driving_criteria", "direct_quotes", "length"]),
            f"Expected exactly the 3 documented requirement ids, got {ids}",
        )


class TestIOShape(unittest.TestCase):
    """AC #4: input {prompt: string, response: string} -> output
    {overall_score: integer 1-5, justification: string,
     criterion_scores: {decomposition, root_cause, tradeoff_awareness,
     materiality, evidentiary_grounding, feasibility,
     journey_coherence, calibration}}."""

    @classmethod
    def setUpClass(cls):
        cls.data = _load_rubric()
        cls.io_shape = cls.data.get("io_shape")

    def test_io_shape_key_present(self):
        self.assertIsNotNone(self.io_shape, "Top-level `io_shape` key is missing")

    def test_input_has_prompt_and_response_as_strings(self):
        input_shape = self.io_shape.get("input")
        self.assertIsNotNone(input_shape, "io_shape.input is missing")

        self.assertIn("prompt", input_shape, "io_shape.input missing `prompt`")
        self.assertEqual(
            input_shape["prompt"].get("type"),
            "string",
            "io_shape.input.prompt.type must be 'string'",
        )

        self.assertIn("response", input_shape, "io_shape.input missing `response`")
        self.assertEqual(
            input_shape["response"].get("type"),
            "string",
            "io_shape.input.response.type must be 'string'",
        )

    def test_input_has_exactly_prompt_and_response_fields(self):
        input_shape = self.io_shape.get("input")
        self.assertEqual(
            sorted(input_shape.keys()),
            sorted(["prompt", "response"]),
            f"io_shape.input should have exactly prompt+response, got {list(input_shape.keys())}",
        )

    def test_output_has_overall_score_number_1_to_5(self):
        output_shape = self.io_shape.get("output")
        self.assertIsNotNone(output_shape, "io_shape.output is missing")

        overall_score = output_shape.get("overall_score")
        self.assertIsNotNone(overall_score, "io_shape.output missing `overall_score`")
        self.assertEqual(
            overall_score.get("type"),
            "number",
            "io_shape.output.overall_score.type must be 'number'",
        )
        self.assertEqual(
            overall_score.get("range"),
            [1, 5],
            f"io_shape.output.overall_score.range must be [1, 5], "
            f"got {overall_score.get('range')}",
        )

    def test_output_has_justification_string(self):
        output_shape = self.io_shape.get("output")
        justification = output_shape.get("justification")
        self.assertIsNotNone(justification, "io_shape.output missing `justification`")
        self.assertEqual(
            justification.get("type"),
            "string",
            "io_shape.output.justification.type must be 'string'",
        )

    def test_output_has_criterion_scores_with_exact_eight_properties(self):
        output_shape = self.io_shape.get("output")
        criterion_scores = output_shape.get("criterion_scores")
        self.assertIsNotNone(
            criterion_scores, "io_shape.output missing `criterion_scores`"
        )
        self.assertEqual(
            criterion_scores.get("type"),
            "object",
            "io_shape.output.criterion_scores.type must be 'object'",
        )

        properties = criterion_scores.get("properties", {})
        self.assertEqual(
            sorted(properties.keys()),
            sorted(EXPECTED_CRITERION_KEYS),
            f"io_shape.output.criterion_scores.properties must be exactly "
            f"{EXPECTED_CRITERION_KEYS}, got {list(properties.keys())}",
        )

        for key in EXPECTED_CRITERION_KEYS:
            with self.subTest(property=key):
                prop = properties[key]
                self.assertEqual(
                    prop.get("type"),
                    "integer",
                    f"io_shape.output.criterion_scores.properties.{key}.type must be 'integer'",
                )
                self.assertEqual(
                    prop.get("range"),
                    [1, 5],
                    f"io_shape.output.criterion_scores.properties.{key}.range must be [1, 5], "
                    f"got {prop.get('range')}",
                )

    def test_output_has_exactly_expected_top_level_fields(self):
        output_shape = self.io_shape.get("output")
        self.assertEqual(
            sorted(output_shape.keys()),
            sorted([
                "overall_score",
                "aggregation",
                "score_breakdown",
                "criterion_scores",
                "dimension_justifications",
                "justification",
            ]),
            f"io_shape.output should have exactly overall_score+aggregation+"
            f"score_breakdown+criterion_scores+dimension_justifications+"
            f"justification, got {list(output_shape.keys())}",
        )


class TestDomainIndependence(unittest.TestCase):
    """
    Enforces the constitution/generator split.

    Rubric anchors must be domain-independent: abstract, structural language
    only.  OPEX instantiations belong in `opex_example:` fields and generator
    output, never in the constitution's level anchors.

    This test scans ALL 8 criteria — including the conditional criteria
    journey_coherence and calibration — across ALL 5 levels, asserting that no
    level anchor contains any OPEX-specific forbidden term.  It also asserts
    that the top-level `example_scenario:` field is present and explicitly
    labeled as a placeholder, confirming it is not silently treated as
    canonical domain specification for the constitution's anchors.
    """

    FORBIDDEN_TERMS = [
        "storage",
        "logistics",
        "s&m",
        "selling & marketing",
        "selling and marketing",
        "cost center",
        "cost driver",
        "budget",
        "opex",
        "freight",
        "procurement",
        "inventory",
        "q3",
        "q4",
    ]

    @classmethod
    def setUpClass(cls):
        cls.data = _load_rubric()
        cls.criteria = cls.data.get("criteria", [])

    def test_no_opex_terms_in_any_level_anchor(self):
        """All 8 criteria x 5 levels: level anchor text must contain no
        OPEX-specific domain term.  A hit means a domain instantiation has
        leaked from the generator layer into the constitution layer.

        Additionally asserts that the top-level example_scenario: field is
        present AND contains the literal text '[Placeholder', confirming it is
        explicitly labeled as a generator test fixture and not silently treated
        as canonical domain specification.
        """
        # --- Part 1: no forbidden OPEX term in any level anchor ---
        for c in self.criteria:
            key = c.get("key")
            levels = c.get("levels", {})
            for level_num in EXPECTED_LEVELS:
                anchor = levels.get(level_num, "")
                if not isinstance(anchor, str):
                    continue
                anchor_lower = anchor.lower()
                for term in self.FORBIDDEN_TERMS:
                    with self.subTest(criterion=key, level=level_num, term=term):
                        self.assertNotIn(
                            term,
                            anchor_lower,
                            f"Criterion {key} level {level_num} anchor contains "
                            f"OPEX-specific term '{term}': {anchor!r} — move "
                            f"domain-specific language to the opex_example: field",
                        )

        # --- Part 2: example_scenario is present and labeled as a placeholder ---
        scenario = self.data.get("example_scenario")
        self.assertIsNotNone(
            scenario,
            "Top-level `example_scenario:` field is missing from rubric_spec.yaml",
        )
        self.assertIn(
            "[Placeholder",
            scenario,
            "Top-level `example_scenario:` field does not contain the literal "
            "text '[Placeholder' — it must be explicitly labeled as a generator "
            "test fixture, not silently treated as canonical domain specification",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
