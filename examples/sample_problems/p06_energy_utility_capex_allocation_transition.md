# Energy Utility Capital Allocation — Renewable Transition Investment Sequencing

## Industry & Value Chain
- **Industry:** Energy / Regulated Electric Utility
- **Company type:** Vertically integrated investor-owned utility (~$14B rate base, serving 2.1M customers in a single state)
- **Value chain position:** Finance / Capital allocation
- **Source reference:** Synthesized from IEA "A capital allocation dilemma in energy transitions" (iea.org/commentaries/a-capital-allocation-dilemma-in-energy-transitions) + ScienceDirect redirecting capital in renewable energy transition (sciencedirect.com/science/article/pii/S2949790626000819) + ScienceDirect capital structure decisions in energy transition (sciencedirect.com/science/article/pii/S0957178724001450)

## Business Context
A regulated investor-owned utility has committed to the state public utility commission (PUC) to achieve 60% clean generation by 2035 and 100% by 2040, pursuant to a state-mandated integrated resource plan (IRP). The utility's current generation mix is 54% coal (three aging plants, average age 38 years), 22% natural gas, 14% nuclear, and 10% renewable. The IRP authorizes up to $9.4B in capital investment over the next 10 years. However, the utility's investment-grade credit rating (currently Baa1) constrains total debt issuance; each incremental $1B in rate-base investment increases annual revenue requirement by ~$90M and requires PUC rate case approval, which on average takes 18 months. The three coal plants have different retirement economics: Coal-1 is fully depreciated and retires cheaply; Coal-2 has a $340M stranded-cost regulatory asset that must be securitized; Coal-3 is jointly owned with a municipal cooperative that has veto rights over any closure before 2031. Renewable development is competing for the same EPC contractor workforce, creating a sequencing bottleneck.

## Problem Statement
> The CFO and Chief Strategy Officer have been asked to present the board and PUC with a 10-year capital sequencing plan that maximizes the probability of meeting the 2035 clean-generation milestone while maintaining a Baa1 or better credit rating, keeping customer rate increases below 3.5% annually in real terms, and avoiding stranded-cost exposure that exceeds the regulatory risk appetite. Your mandate is to evaluate at least four distinct capital sequencing scenarios — varying the timing of coal retirements, the mix of owned vs. contracted renewables, and the pace of transmission and storage investment — and to quantify, for each scenario, the distribution of outcomes on credit metrics, rate impact, and clean-generation percentage at 2030 and 2035. The analysis must be submitted as part of the next IRP update filing, due in 18 months.

## Key Constraints
- **Hard:** Coal-3 cannot be retired before 2031 without consent of the municipal co-owner (legal and contractual constraint; consent probability is low based on current negotiations)
- **Hard:** The Baa1 credit floor is a board-level covenant — scenarios that breach this threshold for more than two consecutive quarters are out of scope
- **Soft:** PUC has historically allowed 9-10% allowed ROE in rate cases; scenarios assuming >10% are unlikely to be approved and should be flagged as optimistic
- **Soft:** The utility prefers owned generation over long-term PPAs for rate-base growth, but PPA structures may be required for battery storage where the economics do not yet support ownership

## Available Data / Known Gaps
- **Available:** Existing IRP model with load forecasts, generation dispatch economics, and capital cost estimates; regulatory precedent from the last four rate cases; credit agency sensitivity models (shared by Moody's in prior engagement); EPC contractor capacity estimates (from procurement team); Coal-3 joint-ownership agreement (legal)
- **Gaps:** Long-run renewable energy cost curves are uncertain beyond 5 years (IRP uses deterministic point estimates, not distributions); the securitization timeline for Coal-2 stranded costs depends on pending state legislation and is binary (either passes this session or delays 2 years); capacity market price projections are highly uncertain and materially affect the economics of gas peakers vs. battery storage

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** counterfactual
- **Flags:** distributional: true, intractable: false, reflexive: true, gameable: false
- **Classification rationale:** Multiple valid sequencing plans exist (no single optimal sequence given parametric uncertainty). Verifiability is counterfactual because there is no observable baseline to compare against — any chosen sequence forecloses the alternatives, and outcomes 10 years out cannot be attributed to the plan vs. exogenous factors. Distributional because the deliverable explicitly requires probability distributions over credit, rate, and generation outcomes for each scenario. Reflexive because the utility's own capital sequencing signals — when filed publicly in the IRP — affect wholesale power market prices, competitor investment decisions, and EPC contractor bidding behavior, which in turn alter the scenario economics.
