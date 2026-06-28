"""
tests/test_eval_loop.py — Static structural tests for the eval loop scripts.

Groups:
  1. TestCaseManifest     — scripts/case_manifest.py
  2. TestEvalLoop         — scripts/eval_loop.py
  3. TestAggregateFailures — scripts/aggregate_failures.py (via subprocess)

No live API calls. No hardcoded content from actual training case files.
All Group 3 fixtures are synthetic in-memory data written to temp directories.

Run with:
    pytest tests/test_eval_loop.py -v
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# ---------------------------------------------------------------------------
# Absolute paths
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# ---------------------------------------------------------------------------
# Module-import helper
# ---------------------------------------------------------------------------

def _import_script(name: str):
    """
    Load a scripts/<name>.py module in isolation using importlib.
    Executes module-level code (sys.path inserts) but does NOT call main().
    """
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Group 3 helpers (module-level, used by TestAggregateFailures)
# ---------------------------------------------------------------------------

def _make_case_dir(case_dir: Path, eval_data: dict, parse_data: dict = None):
    """Write eval_output.json (and optionally parse_output.json) into case_dir."""
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "eval_output.json").write_text(
        json.dumps(eval_data), encoding="utf-8"
    )
    if parse_data is not None:
        (case_dir / "parse_output.json").write_text(
            json.dumps(parse_data), encoding="utf-8"
        )


def _run_aggregate_script(run_dir: Path, cwd: Path) -> dict:
    """
    Invoke aggregate_failures.py via subprocess with run_dir as the argument.
    CWD is set to cwd so that logs/failures/ is created inside the temp tree.
    Returns the parsed JSON output document.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "aggregate_failures.py"), str(run_dir)],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    assert result.returncode == 0, (
        f"aggregate_failures.py exited with code {result.returncode}.\n"
        f"stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    )
    output_path = result.stdout.strip()
    with open(output_path) as fh:
        return json.load(fh)


# ===========================================================================
# Group 1: TestCaseManifest
# ===========================================================================

class TestCaseManifest:
    """Acceptance criteria for scripts/case_manifest.py."""

    @pytest.fixture(scope="class")
    def cm(self):
        return _import_script("case_manifest")

    @pytest.fixture(scope="class")
    def all_cases(self, cm):
        return cm.build_all_cases()

    # AC 1: File exists at scripts/case_manifest.py
    def test_file_exists(self):
        assert (SCRIPTS_DIR / "case_manifest.py").is_file(), (
            f"scripts/case_manifest.py not found at {SCRIPTS_DIR / 'case_manifest.py'}"
        )

    # AC 2: CATEGORY_MAP is defined and contains exactly keys A, B, C, D, E, F
    def test_category_map_has_exactly_six_keys(self, cm):
        assert hasattr(cm, "CATEGORY_MAP"), "CATEGORY_MAP not defined in case_manifest.py"
        assert set(cm.CATEGORY_MAP.keys()) == {"A", "B", "C", "D", "E", "F"}, (
            f"CATEGORY_MAP must have exactly keys A,B,C,D,E,F; "
            f"got {set(cm.CATEGORY_MAP.keys())}"
        )

    # AC 3: CATEGORY_MAP["D"] == "Growth Strategy"
    def test_category_map_D_is_growth_strategy(self, cm):
        assert cm.CATEGORY_MAP["D"] == "Growth Strategy", (
            f'CATEGORY_MAP["D"] must be "Growth Strategy"; '
            f"got {cm.CATEGORY_MAP['D']!r}"
        )

    # AC 4: CATEGORY_MAP["F"] == "Unconventional Cases"
    def test_category_map_F_is_unconventional_cases(self, cm):
        assert cm.CATEGORY_MAP["F"] == "Unconventional Cases", (
            f'CATEGORY_MAP["F"] must be "Unconventional Cases"; '
            f"got {cm.CATEGORY_MAP['F']!r}"
        )

    # AC 5: build_all_cases() returns list of dicts with keys: case_id, path, sector,
    #        difficulty, category
    @pytest.mark.parametrize("key", [
        "case_id", "path", "sector", "difficulty", "category"
    ])
    def test_build_all_cases_dict_has_required_key(self, all_cases, key):
        assert all_cases, "build_all_cases() returned an empty list"
        for case in all_cases:
            assert key in case, (
                f"case dict is missing required key {key!r}: {case}"
            )

    # AC 5 (extra): _full_path is stripped from output dicts
    def test_build_all_cases_strips_internal_full_path(self, all_cases):
        for case in all_cases:
            assert "_full_path" not in case, (
                f"_full_path must be stripped from build_all_cases() output; "
                f"found in case: {case}"
            )

    # AC 6: All paths returned by build_all_cases() start with examples/training_set/
    def test_all_paths_start_with_training_set(self, all_cases):
        for case in all_cases:
            assert case["path"].startswith("examples/training_set/"), (
                f"Path does not start with 'examples/training_set/': {case['path']!r}"
            )

    # AC 7: No paths returned by build_all_cases() contain testing_set
    def test_no_path_contains_testing_set(self, all_cases):
        for case in all_cases:
            assert "testing_set" not in case["path"], (
                f"Path must not contain 'testing_set': {case['path']!r}"
            )

    # AC 8: build_all_cases() returns exactly 57 cases
    def test_build_all_cases_returns_exactly_57(self, all_cases):
        assert len(all_cases) == 57, (
            f"build_all_cases() must return exactly 57 cases; got {len(all_cases)}"
        )

    # AC 9: stratified_sample(cases, n=6, seed=42) returns exactly 6 items
    def test_stratified_sample_n6_returns_6_items(self, cm, all_cases):
        result = cm.stratified_sample(all_cases, n=6, seed=42)
        assert len(result) == 6, (
            f"stratified_sample(n=6) must return 6 items; got {len(result)}"
        )

    # AC 10: stratified_sample(cases, n=6, seed=42) called twice returns identical results
    def test_stratified_sample_n6_is_reproducible(self, cm, all_cases):
        r1 = cm.stratified_sample(all_cases, n=6, seed=42)
        r2 = cm.stratified_sample(all_cases, n=6, seed=42)
        ids1 = sorted(c["case_id"] for c in r1)
        ids2 = sorted(c["case_id"] for c in r2)
        assert ids1 == ids2, (
            f"stratified_sample(n=6, seed=42) is not reproducible: "
            f"first call={ids1}, second call={ids2}"
        )

    # AC 11: stratified_sample(cases, n=6, seed=42) covers all 6 categories
    def test_stratified_sample_n6_covers_all_six_categories(self, cm, all_cases):
        result = cm.stratified_sample(all_cases, n=6, seed=42)
        actual_cats = {c["category"] for c in result}
        expected_cats = set(cm.CATEGORY_MAP.values())
        assert actual_cats == expected_cats, (
            f"stratified_sample(n=6) must cover all 6 categories; "
            f"got {actual_cats}, expected {expected_cats}"
        )

    # AC 12: stratified_sample(cases, n=15, seed=42) returns exactly 15 items
    def test_stratified_sample_n15_returns_15_items(self, cm, all_cases):
        result = cm.stratified_sample(all_cases, n=15, seed=42)
        assert len(result) == 15, (
            f"stratified_sample(n=15) must return 15 items; got {len(result)}"
        )

    # AC 13: _assert_no_testing_set raises ValueError for a testing_set path
    def test_assert_no_testing_set_raises_value_error(self, cm):
        bad_cases = [
            {"case_id": "c99", "path": "examples/testing_set/cases/c99_foo.md"}
        ]
        with pytest.raises(ValueError, match="testing_set"):
            cm._assert_no_testing_set(bad_cases)

    # AC 14: All case_id values match pattern c\d+ (e.g., c02, c11)
    def test_all_case_ids_match_pattern(self, all_cases):
        pattern = re.compile(r"^c\d+$")
        for case in all_cases:
            assert pattern.match(case["case_id"]), (
                f"case_id {case['case_id']!r} does not match required pattern c\\d+; "
                f"full case: {case}"
            )


# ===========================================================================
# Group 2: TestEvalLoop
# ===========================================================================

class TestEvalLoop:
    """Acceptance criteria for scripts/eval_loop.py."""

    @pytest.fixture(scope="class")
    def el(self):
        return _import_script("eval_loop")

    @pytest.fixture(scope="class")
    def source(self):
        return (SCRIPTS_DIR / "eval_loop.py").read_text(encoding="utf-8")

    # AC 1: File exists at scripts/eval_loop.py
    def test_file_exists(self):
        assert (SCRIPTS_DIR / "eval_loop.py").is_file(), (
            f"scripts/eval_loop.py not found at {SCRIPTS_DIR / 'eval_loop.py'}"
        )

    # AC 2: AGENT_FILE constant points to .claude/agents/parser-evaluator.md
    def test_agent_file_constant_points_to_parser_evaluator(self, el):
        assert hasattr(el, "AGENT_FILE"), "AGENT_FILE constant not found in eval_loop.py"
        path_str = str(el.AGENT_FILE)
        assert ".claude" in path_str, (
            f"AGENT_FILE must include '.claude' in path; got {path_str!r}"
        )
        assert "agents" in path_str, (
            f"AGENT_FILE must include 'agents' in path; got {path_str!r}"
        )
        assert "parser-evaluator.md" in path_str, (
            f"AGENT_FILE must reference 'parser-evaluator.md'; got {path_str!r}"
        )

    # AC 3: _load_evaluator_prompt() strips YAML frontmatter
    #        Tested with an in-memory fake file — no disk I/O.
    def test_load_evaluator_prompt_strips_frontmatter(self, el):
        fake_content = "---\nmodel: sonnet\ndescription: test agent\n---\nThis is the body."
        with patch("builtins.open", mock_open(read_data=fake_content)):
            result = el._load_evaluator_prompt()
        assert result == "This is the body.", (
            f"_load_evaluator_prompt must strip YAML frontmatter and return only body; "
            f"got: {result!r}"
        )
        assert "model: sonnet" not in result, (
            "Frontmatter key 'model: sonnet' must be absent from stripped result"
        )
        assert "description: test agent" not in result, (
            "Frontmatter key 'description: test agent' must be absent from stripped result"
        )

    # AC 4: _compute_dimension_pass_rates([]) → dict with all 5 keys, all None
    def test_compute_dimension_pass_rates_empty_returns_all_none(self, el):
        result = el._compute_dimension_pass_rates([])
        expected_keys = {
            "field_completeness",
            "information_loss",
            "boundary_accuracy",
            "speaker_attribution",
            "verbatim_constraint",
        }
        assert set(result.keys()) == expected_keys, (
            f"_compute_dimension_pass_rates([]) must return exactly keys "
            f"{expected_keys}; got {set(result.keys())}"
        )
        for dim, rate in result.items():
            assert rate is None, (
                f"Dimension {dim!r} must be None for empty input; got {rate!r}"
            )

    # AC 5: All 5 checks PASS → all rates == 1.0
    def test_compute_dimension_pass_rates_all_pass_returns_1_0(self, el):
        ev = {
            "checks": {
                "field_completeness":   "PASS",
                "information_loss":     "PASS",
                "boundary_accuracy":    "PASS",
                "speaker_attribution":  "PASS",
                "verbatim_constraint":  "PASS",
            }
        }
        result = el._compute_dimension_pass_rates([ev])
        for dim, rate in result.items():
            assert rate == 1.0, (
                f"Dimension {dim!r} must be 1.0 when its check is PASS; got {rate}"
            )

    # AC 6: One check FAIL → 0.0 for that dimension; all others remain 1.0
    @pytest.mark.parametrize("failing_dim", [
        "field_completeness",
        "information_loss",
        "boundary_accuracy",
        "speaker_attribution",
        "verbatim_constraint",
    ])
    def test_compute_dimension_pass_rates_one_fail_returns_0_0(self, el, failing_dim):
        checks = {
            "field_completeness":   "PASS",
            "information_loss":     "PASS",
            "boundary_accuracy":    "PASS",
            "speaker_attribution":  "PASS",
            "verbatim_constraint":  "PASS",
        }
        checks[failing_dim] = "FAIL"
        result = el._compute_dimension_pass_rates([{"checks": checks}])
        assert result[failing_dim] == 0.0, (
            f"Dimension {failing_dim!r} must be 0.0 when its check is FAIL; "
            f"got {result[failing_dim]}"
        )
        for other_dim, rate in result.items():
            if other_dim != failing_dim:
                assert rate == 1.0, (
                    f"Dimension {other_dim!r} must remain 1.0 when only {failing_dim!r} "
                    f"failed; got {rate}"
                )

    # AC 7: _worst_dimension({"a": 0.8, "b": 0.3, "c": 0.9}) returns "b"
    def test_worst_dimension_returns_key_with_lowest_rate(self, el):
        rates = {"a": 0.8, "b": 0.3, "c": 0.9}
        result = el._worst_dimension(rates)
        assert result == "b", (
            f"_worst_dimension must return 'b' (rate 0.3 is lowest); got {result!r}"
        )

    # AC 8: _worst_dimension({"a": None, "b": None}) returns None
    def test_worst_dimension_all_none_returns_none(self, el):
        rates = {"a": None, "b": None}
        result = el._worst_dimension(rates)
        assert result is None, (
            f"_worst_dimension must return None when all rates are None; got {result!r}"
        )

    # AC 9: Model in _call_evaluator is claude-sonnet-4-6 (verified from source text)
    def test_call_evaluator_uses_claude_sonnet_4_6_model(self, source):
        assert "claude-sonnet-4-6" in source, (
            "eval_loop.py must specify model 'claude-sonnet-4-6' in _call_evaluator; "
            "string not found in source"
        )


# ===========================================================================
# Group 3: TestAggregateFailures
# ===========================================================================

class TestAggregateFailures:
    """
    Acceptance criteria for scripts/aggregate_failures.py.

    All tests use synthetic in-memory fixtures written to temp directories;
    the script is invoked via subprocess (option b — tests the actual CLI path).
    """

    # ---- Fixtures -----------------------------------------------------------

    @pytest.fixture(scope="class")
    def main_run(self, tmp_path_factory):
        """
        2 valid cases + 1 errored case.

        c_pass:          verdict=PASS, all checks PASS, category=Profitability
        c_fail_boundary: verdict=FAIL, boundary_accuracy=FAIL, BOUNDARY_ERROR,
                         category=Market Entry; shares one hint with c_pass
        c_error:         top-level "error" key — must be counted as errored, not evaluated
        """
        base    = Path(tmp_path_factory.mktemp("agg_main"))
        run_dir = base / "run_dir"

        _make_case_dir(
            run_dir / "c_pass",
            eval_data={
                "verdict": "PASS",
                "checks": {
                    "field_completeness":  "PASS",
                    "information_loss":    "PASS",
                    "boundary_accuracy":   "PASS",
                    "speaker_attribution": "PASS",
                    "verbatim_constraint": "PASS",
                },
                "failures": [],
                "improvement_hints": ["Ensure verbatim quotes are preserved exactly"],
            },
            parse_data={"case_category": "Profitability"},
        )

        _make_case_dir(
            run_dir / "c_fail_boundary",
            eval_data={
                "verdict": "FAIL",
                "checks": {
                    "field_completeness":  "PASS",
                    "information_loss":    "PASS",
                    "boundary_accuracy":   "FAIL",
                    "speaker_attribution": "PASS",
                    "verbatim_constraint": "PASS",
                },
                "failures": [
                    {
                        "error_type": "BOUNDARY_ERROR",
                        "field": "reasoning_trace",
                        "detail": "Start boundary misidentified",
                        "example": "Candidate answer included interviewer question text",
                    }
                ],
                "improvement_hints": [
                    "Ensure verbatim quotes are preserved exactly",   # duplicate
                    "Clarify boundary detection for reasoning_trace start",
                ],
            },
            parse_data={"case_category": "Market Entry"},
        )

        _make_case_dir(
            run_dir / "c_error",
            eval_data={"error": "parse failed — eval skipped"},
        )

        return _run_aggregate_script(run_dir, base)

    @pytest.fixture(scope="class")
    def priority_run(self, tmp_path_factory):
        """
        3 valid cases for testing improvement_priority sort order.

        c0 + c1: BOUNDARY_ERROR (total count 2)
        c2:      FIELD_MISSING  (total count 1)
        Expected priority: ["BOUNDARY_ERROR", "FIELD_MISSING"]
        """
        base    = Path(tmp_path_factory.mktemp("agg_priority"))
        run_dir = base / "run_dir"

        for i, error_type in enumerate(
            ["BOUNDARY_ERROR", "BOUNDARY_ERROR", "FIELD_MISSING"]
        ):
            _make_case_dir(
                run_dir / f"c{i}",
                eval_data={
                    "verdict": "FAIL",
                    "checks": {
                        "field_completeness":  "FAIL",
                        "information_loss":    "PASS",
                        "boundary_accuracy":   "FAIL",
                        "speaker_attribution": "PASS",
                        "verbatim_constraint": "PASS",
                    },
                    "failures": [
                        {
                            "error_type": error_type,
                            "field":      "reasoning_trace",
                            "detail":     "synthetic failure",
                            "example":    "synthetic example text",
                        }
                    ],
                    "improvement_hints": [],
                },
                parse_data={"case_category": "Profitability"},
            )

        return _run_aggregate_script(run_dir, base)

    @pytest.fixture(scope="class")
    def all_error_run(self, tmp_path_factory):
        """2 cases, both errored — pass_rate must be None."""
        base    = Path(tmp_path_factory.mktemp("agg_all_err"))
        run_dir = base / "run_dir"

        _make_case_dir(run_dir / "c_err1", eval_data={"error": "timeout"})
        _make_case_dir(run_dir / "c_err2", eval_data={"error": "parse failed"})

        return _run_aggregate_script(run_dir, base)

    # ---- Tests --------------------------------------------------------------

    # AC 1: File exists at scripts/aggregate_failures.py
    def test_file_exists(self):
        assert (SCRIPTS_DIR / "aggregate_failures.py").is_file(), (
            f"scripts/aggregate_failures.py not found at "
            f"{SCRIPTS_DIR / 'aggregate_failures.py'}"
        )

    # AC 2: DIMENSIONS contains exactly the 5 expected strings in the right order
    def test_dimensions_list_exact(self):
        mod = _import_script("aggregate_failures")
        expected = [
            "field_completeness",
            "information_loss",
            "boundary_accuracy",
            "speaker_attribution",
            "verbatim_constraint",
        ]
        assert mod.DIMENSIONS == expected, (
            f"DIMENSIONS must be exactly {expected}; got {mod.DIMENSIONS}"
        )

    # AC 3: improvement_priority == ["BOUNDARY_ERROR"] for 1 PASS + 1 FAIL(BOUNDARY_ERROR)
    def test_improvement_priority_contains_boundary_error(self, main_run):
        assert main_run["improvement_priority"] == ["BOUNDARY_ERROR"], (
            f"improvement_priority must be ['BOUNDARY_ERROR'] for a single-type failure run; "
            f"got {main_run['improvement_priority']}"
        )

    # AC 4: errored cases go to cases_errored, not cases_evaluated
    def test_errored_case_is_counted_in_errored_not_evaluated(self, main_run):
        assert main_run["cases_errored"] == 1, (
            f"cases_errored must be 1 (one case with top-level 'error' key); "
            f"got {main_run['cases_errored']}"
        )
        assert main_run["cases_evaluated"] == 2, (
            f"cases_evaluated must be 2 (excludes the errored case); "
            f"got {main_run['cases_evaluated']}"
        )

    # AC 5: pass_rate is None when all cases are errored (0 valid cases)
    def test_pass_rate_is_none_when_all_cases_errored(self, all_error_run):
        assert all_error_run["pass_rate"] is None, (
            f"pass_rate must be None when all cases errored; "
            f"got {all_error_run['pass_rate']!r}"
        )

    # AC 6: boundary_accuracy dimension pass rate = 0.5 (1 PASS, 1 FAIL out of 2 valid)
    def test_boundary_accuracy_pass_rate_is_0_5(self, main_run):
        rate = main_run["dimension_pass_rates"]["boundary_accuracy"]
        assert rate == 0.5, (
            f"boundary_accuracy dimension pass rate must be 0.5 "
            f"(1 PASS + 1 FAIL = 2 cases); got {rate}"
        )

    # AC 7: worst_dimension is boundary_accuracy (lowest pass rate at 0.5 vs 1.0)
    def test_worst_dimension_is_boundary_accuracy(self, main_run):
        assert main_run["worst_dimension"] == "boundary_accuracy", (
            f"worst_dimension must be 'boundary_accuracy' (pass rate 0.5, "
            f"all others 1.0); got {main_run['worst_dimension']!r}"
        )

    # AC 8: improvement_priority is sorted descending by frequency
    def test_improvement_priority_sorted_descending_by_frequency(self, priority_run):
        priority = priority_run["improvement_priority"]
        assert priority == ["BOUNDARY_ERROR", "FIELD_MISSING"], (
            f"improvement_priority must be ['BOUNDARY_ERROR', 'FIELD_MISSING'] "
            f"(BOUNDARY_ERROR count=2 > FIELD_MISSING count=1); got {priority}"
        )

    # AC 9: improvement_hints deduplication — same hint in two cases appears once
    def test_improvement_hints_are_deduplicated(self, main_run):
        hints = main_run["improvement_hints"]
        # "Ensure verbatim quotes are preserved exactly" appears in both c_pass and
        # c_fail_boundary but must appear only once in the output.
        repeated_hint = "Ensure verbatim quotes are preserved exactly"
        count = hints.count(repeated_hint)
        assert count == 1, (
            f"Hint {repeated_hint!r} appears in two cases but must appear "
            f"only once after deduplication; found {count} times in {hints}"
        )
        # Total unique hints should be 2
        assert len(hints) == 2, (
            f"Expected exactly 2 unique hints after deduplication; got {len(hints)}: {hints}"
        )

    # AC 10: worst_category reflects the category with the lowest pass rate
    def test_worst_category_is_market_entry(self, main_run):
        # Market Entry: 1 case, verdict=FAIL → pass rate 0.0
        # Profitability: 1 case, verdict=PASS → pass rate 1.0
        assert main_run["worst_category"] == "Market Entry", (
            f"worst_category must be 'Market Entry' (0% pass rate vs "
            f"Profitability 100%); got {main_run['worst_category']!r}"
        )
