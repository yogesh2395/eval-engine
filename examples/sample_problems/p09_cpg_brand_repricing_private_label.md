# CPG Brand Repricing Under Private-Label Encroachment — Price-Pack Architecture Redesign

## Industry & Value Chain
- **Industry:** CPG / FMCG (packaged food)
- **Company type:** Large CPG company with a flagship ambient grocery brand (~$2.8B global revenue from the brand, sold in 34 markets)
- **Value chain position:** Pricing / Brand strategy
- **Source reference:** Synthesized from PwC "A new roadmap for CPG pricing strategies and growth" (pwc.com/us/en/industries/consumer-markets/library/cpg-pricing-strategy.html) + Consumer Goods Technology "CPGs Pull Pricing and Promotion Levers Amid Private Label Expansion" (consumergoods.com/cpgs-pull-pricing-and-promotion-levers-amid-private-label-expansion) + SmashBrand CPG pricing strategy (smashbrand.com/articles/cpg-pricing-strategy/)

## Business Context
A large CPG company's flagship ambient grocery brand (soups and sauces) has lost 3.8 percentage points of U.S. market share over the past 18 months — approximately $190M in annualized retail sales — as retailer private-label alternatives have expanded shelf presence and narrowed the quality perception gap. The brand's average retail price premium over private label is currently 42%, down from 51% three years ago (CPG raised prices twice for input-cost recovery; private label did not match the full increase). Consumer panel data shows the brand's household penetration has declined most sharply in the 25-44 demographic, while the 55+ cohort has remained loyal. The brand's gross margin is 38%; the CFO has set a floor of 33% and will not approve any pricing or promotional action that structurally breaches it. The brand team is debating three strategic options: a targeted price reduction on the core SKU, a price-pack architecture redesign introducing a "value" pack at a lower price point, or a brand investment (quality renovation + marketing) play to re-widen the perception gap.

## Problem Statement
> The brand P&L owner and revenue growth management team must recommend a price-pack architecture strategy for the U.S. market within the next annual planning cycle (decision locked in 10 weeks, implementation beginning Q1 next fiscal year). The recommendation must specify: (a) which of the three strategic options — price reduction, new pack tier, or brand investment — to pursue, with supporting quantification; (b) the specific price points, pack sizes, and promotional depth by retail channel (grocery, mass, club, e-commerce); and (c) the expected impact on volume, revenue, and gross margin at 12 and 24 months under base, upside, and downside demand scenarios. The primary metric is brand market share (volume); secondary constraints are gross margin floor (33%) and absolute dollar gross profit versus prior year. The recommendation must account for the risk that a price reduction triggers a retailer private-label repricing response that neutralizes the volume gain.

## Key Constraints
- **Hard:** Gross margin must not fall below 33% on a trailing-12-month basis — the CFO will reject any plan that breaches this, regardless of strategic rationale
- **Hard:** The annual planning cycle locks pricing decisions in 10 weeks; the retail trade calendar means any price changes must be communicated to major retail buyers at least 12 weeks before shelf implementation, creating a de facto 10-week decision window
- **Soft:** The global brand team does not want to establish a lower price point in the U.S. that creates precedent for pricing requests from lower-price international markets
- **Soft:** The brand investment option requires marketing spend above the current brand budget; incremental spend above $30M requires divisional CMO approval and competes with other brand priorities

## Available Data / Known Gaps
- **Available:** Three years of Nielsen/IRI retail scanner data (volume, price, promoted/non-promoted, by channel); consumer panel data on household penetration, purchase frequency, and brand switching; private-label cost structure estimates from industry benchmarking; gross-margin model by SKU; retailer P&L sensitivity models (from key account management team); historical price elasticity studies (most recent: 2022)
- **Gaps:** Private-label repricing response function is unknown — there is no historical precedent for a major branded player voluntarily reducing price in this category, making competitor response modeling speculative; consumer quality perception gap is measured only once annually (the most recent survey is 11 months old and predates the second price increase); e-commerce channel price elasticity has not been independently modeled (e-commerce data is embedded in the overall Nielsen model)

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** counterfactual
- **Flags:** distributional: false, intractable: false, reflexive: true, gameable: true
- **Classification rationale:** Multiple valid strategies exist (price reduction, pack architecture, brand investment are each defensible under different demand and competitor-response assumptions). Verifiability is counterfactual because only the chosen strategy is executed — the counterfactual market share trajectory under the unchosen strategies is never observable. Reflexive because the moment a price reduction is filed with retailers (even confidentially), it leaks into the trade; private-label buyers observe and can reposition, altering the competitive landscape the analysis was based on. Gameable because market share (volume) — the primary metric — can be short-term inflated by deep promotions that destroy long-run brand equity, creating incentive to hit the metric at the cost of the underlying objective.
