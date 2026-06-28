# Retail Store Network Rationalization — Footprint Optimization Under Private-Label Pressure

## Industry & Value Chain
- **Company type:** Mid-market specialty apparel retailer (~320 stores, $2.4B revenue)
- **Value chain position:** Store network / Capital allocation
- **Source reference:** Synthesized from Umbrex "Store Closure and Rationalization Analysis" framework (umbrex.com/resources/industry-analyses/how-to-analyze-a-retail-company/store-closure-and-rationalization-analysis/) + PwC CPG pricing strategy research (pwc.com/us/en/industries/consumer-markets/library/cpg-pricing-strategy.html) + Consumer Goods Technology reporting on private-label expansion (consumergoods.com/cpgs-pull-pricing-and-promotion-levers-amid-private-label-expansion)

## Business Context
A specialty apparel chain operating 320 mall-anchored and strip-center stores across North America has seen same-store sales decline for six consecutive quarters, driven by a combination of traffic attrition (mall footfall down 18% since 2019) and online channel cannibalization. The retailer's lease portfolio is heterogeneous: roughly 40% of leases expire within 24 months, 35% have 3-5 years remaining with renewal options, and 25% are locked through 2030 or beyond. A private-equity sponsor acquired the company 18 months ago and is pressing for a network rationalization plan to be submitted to the board within the next budget cycle (90 days). The CFO has flagged that 74 stores are currently EBITDA-negative on a four-wall basis, but the real estate team argues that 22 of those stores drive material traffic to the e-commerce channel (online halo effect) and cannot be evaluated on four-wall P&L alone.

## Problem Statement
> The board has asked for a store portfolio recommendation covering the next 36-month planning window: which stores to close, which to retain, and whether any warrant capital investment for format conversion (e.g., smaller-footprint concepts). The primary metric is four-wall EBITDA contribution at the portfolio level, with a secondary constraint that corporate overhead — currently allocated across all 320 stores — must remain solvent if the store count falls below a threshold. Your mandate is to identify the 20-40 stores that represent the highest-priority closure candidates, estimate the net financial impact (including lease-exit costs, channel-shift revenue, and stranded overhead reabsorption), and propose a sequencing rule for executing closures within the 36-month window without triggering landlord co-tenancy clauses that could cascade to adjacent anchor leases.

## Key Constraints
- **Hard:** No store closure can trigger a co-tenancy clause in an adjacent anchor store's lease without explicit legal sign-off (exposure is up to $8M per triggered clause)
- **Hard:** The company's revolving credit facility contains a minimum-store-count covenant of 200 stores; falling below triggers a covenant violation
- **Soft:** The PE sponsor prefers to avoid closures in Q4 (holiday season) to protect revenue during the evaluation period
- **Soft:** Management wants to preserve stores in markets where the brand has highest NPS scores as potential format-test sites

## Available Data / Known Gaps
- **Available:** Store-level four-wall P&L (trailing 24 months); lease expiry schedule and exit penalty estimates from real estate counsel; customer zip-code purchase data enabling channel-overlap analysis; foot-traffic index by store (third-party); NPS by region; corporate overhead allocation methodology
- **Gaps:** Online halo-effect attribution model does not exist — only directional correlations available; landlord negotiation outcomes are uncertain (co-tenancy clause waivers may be negotiable for ~30% of stores); competitor store-proximity data is not mapped against the store list

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** indirect
- **Flags:** distributional: false, intractable: true, reflexive: false, gameable: false
- **Classification rationale:** Multiple valid portfolio selections exist (the optimal closure set is not unique because halo-effect estimates and negotiation outcomes are uncertain); verifiability is indirect because post-closure revenue shifts manifest over 12-18 months and are confounded by macro traffic trends. Intractable because the full combinatorial store-selection problem (with co-tenancy cascades and covenant floor) is NP-hard — exhaustive optimization is infeasible across 320 stores with interdependent constraints.
