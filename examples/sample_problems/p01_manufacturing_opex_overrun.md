# Manufacturing Plant OPEX Overrun — Overhead Cost Variance Investigation

## Industry & Value Chain
- **Industry:** Discrete Manufacturing (automotive components)
- **Company type:** Mid-size Tier-1 auto parts supplier (~$1.2B revenue, 4 plants)
- **Value chain position:** Operations / COGS management
- **Source reference:** Synthesized from McKinsey "Indirect manufacturing costs: An overlooked source for clear savings" (mckinsey.com/capabilities/operations/our-insights/indirect-manufacturing-costs-an-overlooked-source-for-clear-savings) + Wiss & Company manufacturing variance analysis framework (wiss.com/manufacturing-variance-analysis-cost-overruns/)

## Business Context
A Tier-1 automotive components supplier with four North American stamping and assembly plants has seen plant-level EBITDA margins compress from 11.4% to 7.9% over the past three fiscal years, despite flat-to-modest revenue growth and a stable direct-materials contract with its OEM customer. The CFO's standard cost model shows favorable purchase-price variance on direct materials but widening unfavorable variance on overhead absorption. Leadership suspects the root cause lies in indirect operations (maintenance, tooling, plant utilities, temporary labor), which represent roughly 10% of total cost but account for a disproportionate share of the variance. An internal lean initiative launched 18 months ago was tracking well on direct-labor efficiency but was never instrumented to capture indirect cost drift.

## Problem Statement
> Plant 3 (Lansing, MI) has reported overhead cost-per-unit 23% above the standard set in the FY-24 budget, producing a $4.7M unfavorable overhead variance year-to-date through Q3. The standard was set using FY-22 actuals as a baseline. The plant manager attributes the overrun to energy prices and post-pandemic maintenance catch-up; the CFO's office suspects structural inefficiencies that will persist into FY-25 if unaddressed. Your mandate is to decompose the $4.7M variance into its root-cause buckets, distinguish transient from structural drivers, quantify the savings opportunity addressable within the next budget cycle (FY-25 planning, 90-day horizon), and recommend which levers should be pulled in what sequence. The plant cannot reduce direct-labor headcount and must maintain 98.5% OEM on-time-delivery.

## Key Constraints
- **Hard:** Direct-labor headcount is contractually frozen through June FY-25 (union agreement)
- **Hard:** OEM on-time-delivery must remain ≥ 98.5% — any recommendation that risks line stoppage is disqualifying
- **Soft:** Capital expenditure for new equipment must be submitted through the annual CapEx cycle (deadline: 10 weeks out); operational changes preferred within the current cycle
- **Soft:** Plant manager buy-in required — solutions that bypass plant management will not be implemented

## Available Data / Known Gaps
- **Available:** Three years of monthly P&L by cost center; standard cost roll-up for FY-22, FY-23, FY-24; maintenance work order log (SAP PM module, 24 months); utility bills by meter point; temp-agency invoices; OEM delivery scorecards; plant layout and shift schedule
- **Gaps:** No time-stamped indirect-labor activity data (timesheets aggregated to weekly buckets only); energy sub-metering exists only at building level, not machine level; benchmark data from the other three plants uses a different cost allocation methodology, making direct comparison unreliable

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** indirect
- **Flags:** distributional: false, intractable: false, reflexive: false, gameable: true
- **Classification rationale:** Multiple valid root-cause decompositions exist (maintenance vs. energy vs. indirect labor vs. absorption base); verifiability is indirect because savings from structural fixes won't fully materialize until Q2 FY-25 and will be confounded by volume changes. Gameable because the primary metric (overhead cost-per-unit) is sensitive to denominator manipulation — a plant manager can improve the ratio by reclassifying indirect costs or inflating volume projections.
