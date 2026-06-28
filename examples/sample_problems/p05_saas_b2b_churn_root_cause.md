# B2B SaaS Customer Churn — Root Cause Decomposition and Intervention Prioritization

## Industry & Value Chain
- **Industry:** SaaS / Enterprise Technology
- **Company type:** B2B SaaS company (~$180M ARR, mid-market and enterprise segments, workflow automation platform)
- **Value chain position:** Customer success / Revenue retention
- **Source reference:** Synthesized from DIVA portal SaaS churn prediction case study (diva-portal.org/smash/get/diva2:1901072/FULLTEXT01.pdf) + Cascade Insights "5 Reasons SaaS Customers Leave" (cascadeinsights.com/saas-churn-5-reasons-why-your-customers-are-leaving/) + Simon-Kucher churn-proof SaaS growth analysis (simon-kucher.com/en/insights/nurturing-your-customer-base-growth-saas-churn-proof-strategic-advantage)

## Business Context
A B2B SaaS workflow automation company has seen net revenue retention (NRR) decline from 118% to 103% over the past four quarters, driven primarily by a spike in gross revenue churn from 8% to 14% annually. The company serves ~1,400 mid-market and enterprise accounts. The churn spike began eight months ago, approximately three months after the company launched a product re-platforming that migrated customers from v2 to v3 of its core application. Customer success leadership has attributed the churn to "market headwinds," but cohort analysis shows churn is concentrated in accounts that completed migration to v3 between months 2-5 post-launch, not in accounts that migrated later or remain on v2. The board has requested a root-cause report and intervention roadmap within the next 45 days, before the annual investor NRR disclosure.

## Problem Statement
> The VP of Customer Success must identify the primary causal drivers of the churn spike, distinguish product-caused attrition from macro-driven attrition and competitive displacement, and produce a prioritized intervention portfolio — covering product, CS process, and pricing/packaging — estimated to recover NRR to at least 110% within the next two annual renewal cycles (24-month horizon). The primary metric is gross revenue churn rate; secondary metrics are NRR and logo retention rate. Each proposed intervention must include an estimated cost-to-implement, expected churn-reduction effect with confidence range, and the earliest quarter in which the effect would be observable in reported metrics. The intervention portfolio total cost must remain within the $2.8M discretionary CS budget for the next 12 months.

## Key Constraints
- **Hard:** Board NRR disclosure is in 45 days — the root-cause diagnosis must be complete and defensible before that date; the intervention roadmap must be ready simultaneously
- **Hard:** The v3 platform is not being rolled back; product fixes must be delivered through the normal sprint cycle (minimum 6-week lead time for any material feature change)
- **Soft:** The company prefers to avoid public acknowledgment of a migration defect (reputational concern with prospective buyers); interventions framed as "proactive enhancements" are preferred
- **Soft:** The CS team headcount is frozen — any intervention requiring additional CS headcount must be funded from the $2.8M budget as contractor spend

## Available Data / Known Gaps
- **Available:** Account-level ARR, renewal date, churn date, and churn reason code (self-reported by CS rep at time of loss); product telemetry by account (feature adoption heatmap, login frequency, support ticket volume); migration completion date by account; cohort-level NPS scores; competitive win/loss data from CRM (incomplete — captured for ~60% of churned accounts)
- **Gaps:** No direct customer interview data from churned accounts in the migration cohort (exit interviews were not conducted systematically); churn reason codes are CS-rep-assigned and may be biased toward "budget/cost" to avoid escalation; v3 platform error-log data is available but has not been joined to account-level business outcomes

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** indirect
- **Flags:** distributional: true, intractable: false, reflexive: false, gameable: true
- **Classification rationale:** Multiple valid intervention portfolios exist (product fix vs. CS process change vs. pricing adjustment each has different cost/impact profiles). Verifiability is indirect because intervention effects on churn rate manifest over 12-24 months through renewal cycles and are confounded by market conditions. Distributional because the output must express churn-reduction effects as ranges, not point estimates. Gameable because NRR — the primary reported metric — is susceptible to manipulation (e.g., aggressive upsell of at-risk accounts masks gross churn, or delayed recognition of churned contracts inflates reported retention).
