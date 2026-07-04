"""
scripts/aggregate_score.py — deterministic scoring aggregators.

Pure, deterministic module: no I/O side effects at import time. Operates on
a `criterion_scores` dict whose values are ints 1-5 or the string "N/A", and
(for the conditioner_adaptive aggregator) a `conditioned_by` dict shaped like
the pre-qualifier's output (see rubrics/prequal_spec.yaml):

    {
      "cardinality": "contradictory" | "unique" | "multiple",
      "verifiability": "direct" | "indirect" | "counterfactual",
      "flags": {"distributional": bool, "intractable": bool,
                "reflexive": bool, "gameable": bool},
    }

This module implements four aggregation mechanics discussed in the Unit A
plan (equal_weighted baseline; conditioner_adaptive, critical_floor, and a
stubbed scaled_percentile), plus a two-part score_breakdown (process vs.
recommendation dimension groups). It does not fetch data, write files, or
call any model — it is pure arithmetic over the scores it is given.

Run standalone for manual verification:
    python3 scripts/aggregate_score.py <path-to-scorer_output.json>
"""

import json
import sys

# ---------------------------------------------------------------------------
# Canonical dimension order + groups
# ---------------------------------------------------------------------------

DIMENSIONS = [
    "decomposition",
    "root_cause",
    "materiality",
    "evidentiary_grounding",
    "tradeoff_awareness",
    "feasibility",
    "journey_coherence",
    "calibration",
]

PROCESS_DIMS = [
    "decomposition",
    "root_cause",
    "materiality",
    "journey_coherence",
]

RECOMMENDATION_DIMS = [
    "tradeoff_awareness",
    "feasibility",
    "evidentiary_grounding",
    "calibration",
]

SAFETY_CRITICAL = [
    "root_cause",
    "evidentiary_grounding",
    "calibration",
]

# ---------------------------------------------------------------------------
# conditioner_adaptive weight map — mirrors prequal_spec.yaml's
# conditioning_map / downstream_anchor_shifts EXACTLY. Each entry maps an
# ACTIVE condition to the list of dimensions that receive +1.0 weight.
# ---------------------------------------------------------------------------

WEIGHT_MAP = {
    ("cardinality", "contradictory"): ["tradeoff_awareness"],
    ("cardinality", "unique"): ["calibration", "root_cause"],
    ("cardinality", "multiple"): ["decomposition", "root_cause"],
    ("verifiability", "direct"): ["calibration", "feasibility"],
    ("verifiability", "indirect"): ["feasibility", "calibration"],
    ("verifiability", "counterfactual"): ["feasibility", "calibration"],
    ("flag", "distributional"): ["evidentiary_grounding", "calibration"],
    ("flag", "intractable"): ["feasibility", "root_cause"],
    ("flag", "reflexive"): ["tradeoff_awareness", "feasibility"],
    ("flag", "gameable"): ["tradeoff_awareness", "feasibility"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _non_na(scores):
    """Return a dict of only the non-'N/A' entries, values cast to int."""
    out = {}
    for dim, value in scores.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip().upper() == "N/A":
            continue
        out[dim] = int(value)
    return out


def raw_mean(scores):
    """Mean of non-N/A values, rounded to 3 dp. None if nothing to average."""
    present = _non_na(scores)
    if not present:
        return None
    return round(sum(present.values()) / len(present), 3)


def group_mean(scores, dims):
    """Mean over the non-N/A members of `dims`, 3 dp. None if all N/A."""
    present = _non_na(scores)
    values = [present[d] for d in dims if d in present]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def binary_cap_ceiling(scores):
    """
    Current safety-critical behavior, kept as-is: if any of SAFETY_CRITICAL
    is present (non-N/A) and scores <=2, cap overall at 3.0. Returns 3.0 or
    None (no cap triggered).
    """
    present = _non_na(scores)
    for dim in SAFETY_CRITICAL:
        if dim in present and present[dim] <= 2:
            return 3.0
    return None


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------

def equal_weighted(scores):
    """Arithmetic mean of non-N/A dims, with the binary safety cap applied."""
    base = raw_mean(scores)
    if base is None:
        return None
    ceil = binary_cap_ceiling(scores)
    return min(base, ceil) if ceil is not None else base


def conditioner_adaptive(scores, conditioned_by):
    """
    Weighted mean: every non-N/A dim starts at weight 1.0; for each ACTIVE
    condition in conditioned_by, +1.0 is added to each dim it names per
    WEIGHT_MAP (mirroring prequal_spec's downstream_anchor_shifts). Any
    named dim that is N/A is skipped. The same binary_cap_ceiling is then
    applied to the resulting weighted mean.
    """
    present = _non_na(scores)
    if not present:
        return None

    weights = {dim: 1.0 for dim in present}

    conditioned_by = conditioned_by or {}
    cardinality = conditioned_by.get("cardinality")
    verifiability = conditioned_by.get("verifiability")
    flags = conditioned_by.get("flags") or {}

    active_conditions = []
    if cardinality is not None:
        active_conditions.append(("cardinality", cardinality))
    if verifiability is not None:
        active_conditions.append(("verifiability", verifiability))
    for flag_name, flag_value in flags.items():
        if flag_value:
            active_conditions.append(("flag", flag_name))

    for condition in active_conditions:
        named_dims = WEIGHT_MAP.get(condition)
        if not named_dims:
            continue
        for dim in named_dims:
            if dim in weights:
                weights[dim] += 1.0

    weighted_sum = sum(weights[dim] * present[dim] for dim in present)
    total_weight = sum(weights.values())
    weighted_mean = weighted_sum / total_weight

    ceil = binary_cap_ceiling(scores)
    result = min(weighted_mean, ceil) if ceil is not None else weighted_mean
    return round(result, 3)


def critical_floor(scores):
    """
    Graduated (mastery/sectional-minimum) alternative to the hard binary
    cap. ceiling = min(5.0, 1.5 + 0.75 * critical_min); result is the raw
    mean capped at that ceiling.
    """
    base = raw_mean(scores)
    if base is None:
        return None

    present = _non_na(scores)
    present_critical = [present[d] for d in SAFETY_CRITICAL if d in present]
    if not present_critical:
        return base

    critical_min = min(present_critical)
    ceiling = min(5.0, 1.5 + 0.75 * critical_min)
    return round(min(base, ceiling), 3)


def scaled_percentile(scores, repository=None):
    """
    Forward-looking; NOT computed in v1. Once the repository (D-005)
    accretes enough scored cases, this will map the raw score to a
    percentile band vs. the population (GMAT 200-800 style). Needs the
    D-005 repository population to be meaningful — stubbed until then.
    Never raises; always returns None in v1.
    """
    return None


# ---------------------------------------------------------------------------
# Composite outputs
# ---------------------------------------------------------------------------

def score_breakdown(scores):
    return {
        "process_score": group_mean(scores, PROCESS_DIMS),
        "recommendation_score": group_mean(scores, RECOMMENDATION_DIMS),
    }


def aggregate_all(scores, conditioned_by):
    return {
        "equal_weighted": equal_weighted(scores),
        "conditioner_adaptive": conditioner_adaptive(scores, conditioned_by),
        "critical_floor": critical_floor(scores),
        "scaled_percentile": scaled_percentile(scores),
    }


# ---------------------------------------------------------------------------
# Manual verification entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/aggregate_score.py <scorer_output.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        data = json.load(f)

    criterion_scores = data["criterion_scores"]
    conditioned_by = data.get("conditioned_by", {})

    result = {
        "aggregate_all": aggregate_all(criterion_scores, conditioned_by),
        "score_breakdown": score_breakdown(criterion_scores),
    }
    print(json.dumps(result, indent=2))
