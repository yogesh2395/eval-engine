# Pharma R&D Portfolio Prioritization — Pipeline Triage Under Budget and Capacity Constraints

## Industry & Value Chain
- **Industry:** Pharmaceuticals / Biotech
- **Company type:** Mid-size specialty pharma company (~$3.1B revenue, 14 active pipeline assets across oncology and rare disease)
- **Value chain position:** R&D portfolio management
- **Source reference:** Synthesized from SDG case study on pharma portfolio prioritization (europe.sdg.com/case-study/cutting-edge-prioritization-model-enables-consistent-evaluation-of-early-stage-drugs-across-pharma-portfolio/) + PharmExec "Strategic Approach to Pharma R&D Portfolio Planning" (pharmexec.com/view/strategic-approach-pharma-rd-portfolio-planning) + PMC pipeline progress of top-30 pharma companies (pmc.ncbi.nlm.nih.gov/articles/PMC10540351/)

## Business Context
A mid-size specialty pharma company has 14 active pipeline assets: 3 in Phase 3, 5 in Phase 2, and 6 in Phase 1 or earlier. A recent commercial setback — the Phase 3 failure of its lead oncology asset (representing a $420M write-down) — has forced the CFO to cut the R&D budget by 22% for the next two fiscal years, from $680M to $530M annually. Simultaneously, the company's lead approved product faces generic entry in 28 months, which will erode ~40% of current revenue. The pipeline must now bear the full burden of replacing that revenue. The Head of R&D and Chief Business Officer disagree on the right prioritization logic: R&D leadership advocates for scientific merit and platform value; the CBO advocates for peak sales potential and probability-of-technical-success (PoTS) alone. The board needs a defensible prioritization framework and a recommended portfolio within 90 days, before the annual investor R&D day.

## Problem Statement
> The R&D portfolio committee must produce a prioritized pipeline recommendation for the next 24-month budget window: which assets receive full-funding (at clinical-plan-specified resource levels), which receive reduced or bridging funding (maintaining optionality while slowing development), and which are paused, out-licensed, or terminated. The recommendation must demonstrate that the selected portfolio fits within the $530M annual R&D budget, maintains at least one asset in each stage of development (to preserve organizational capability), and maximizes the risk-adjusted net present value (rNPV) of the portfolio subject to the budget and headcount constraints. The committee must also characterize the uncertainty in the rNPV outcome — including the probability that no pipeline asset reaches commercialization within 7 years — and identify which single decision (asset selection or resource allocation choice) has the highest option value if new clinical data emerges within 12 months.

## Key Constraints
- **Hard:** Total R&D spend must not exceed $530M in FY-current or FY-next; any asset requiring more than $180M in a single year must receive explicit CFO approval with contingency funding identified
- **Hard:** At least one Phase 3 asset must remain funded at full clinical-plan levels to maintain credibility with investors and the FDA (the company has regulatory commitments on two of the three Phase 3 programs)
- **Soft:** The Head of R&D will not support a portfolio that terminates all rare-disease assets — the company has a patient-advocacy relationship and potential orphan-drug designations at stake
- **Soft:** The CBO prefers assets with peak-sales potential > $500M over assets with PoTS > 70% but lower commercial ceiling, all else equal

## Available Data / Known Gaps
- **Available:** Asset-level clinical plans with stage-gate timelines and resource requirements (FTE and external spend); historical PoTS benchmarks by indication and phase from industry databases; commercial models for each asset (peak sales, time-to-peak, market share assumptions); existing rNPV model (built in Excel, uses point-estimate inputs); partnership/out-licensing term sheets received in the last 12 months for three assets
- **Gaps:** PoTS estimates for early-stage assets are particularly uncertain — Phase 1 data packages are thin and internal estimates have not been benchmarked against external precedent; commercial models for rare-disease assets use patient registry data that may understate addressable population (registries systematically undercount); two assets share a manufacturing platform, meaning resource savings from pausing one partially subsidize the other — this dependency is not modeled in the current budget tool

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** counterfactual
- **Flags:** distributional: true, intractable: true, reflexive: false, gameable: false
- **Classification rationale:** Multiple valid portfolio selections exist (rNPV maximization subject to constraints has many near-optimal solutions with different risk profiles). Verifiability is counterfactual because the value of the portfolio that was not chosen cannot be observed — Phase 3 outcomes for paused assets are never realized. Distributional because rNPV is explicitly a probability-weighted distribution over clinical and commercial scenarios, and the committee is asked for a probability characterization of failure to commercialize. Intractable because joint optimization of 14 assets with interdependent platform constraints, stage-gate branching probabilities, and multi-year budget flows produces a stochastic combinatorial problem that is NP-hard to solve exactly.
