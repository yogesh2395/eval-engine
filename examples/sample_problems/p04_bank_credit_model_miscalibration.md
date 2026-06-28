# Bank Credit Pricing Model Miscalibration — Risk-Adjusted Return Reconciliation

## Industry & Value Chain
- **Industry:** Financial Services (regional commercial bank)
- **Company type:** Mid-size U.S. regional bank (~$28B in assets, commercial & industrial lending focus)
- **Value chain position:** Credit model / Risk-adjusted pricing
- **Source reference:** Synthesized from arxiv model validation in banking practice (arxiv.org/pdf/2410.13877) + Springer Nature credit risk explainability study (link.springer.com/article/10.1007/s10479-024-06134-x) + regulatory guidance on model risk management (SR 11-7)

## Business Context
A regional commercial bank's C&I lending portfolio ($6.8B outstanding) has been generating net interest margin (NIM) consistently 40-55 bps below the hurdle rate set by the pricing committee for the past seven quarters. The bank's RAROC (risk-adjusted return on capital) model, implemented in 2019, assigns a risk weight and a required spread to each credit facility at origination. Post-close performance tracking shows that the model is systematically underpricing credit risk for a specific segment — middle-market borrowers in the construction and real estate services industries — while overpricing for investment-grade healthcare borrowers. The result is adverse selection: the bank is winning too many deals in the higher-risk segment (where it is cheapest) and losing deals in the lower-risk segment (where it is most expensive). The Chief Credit Officer has commissioned a model validation review with a 60-day deadline before the next quarterly earnings call.

## Problem Statement
> The model validation team must determine whether the RAROC model's probability-of-default (PD) and loss-given-default (LGD) calibrations are statistically fit for purpose across industry segments, identify which specific parameters are miscalibrated and by how much, and produce a revised pricing adjustment — expressed as spread corrections in basis points by segment — that would have generated RAROC at or above the 14.5% hurdle rate on the trailing 28-quarter backbook. The correction must be implementable within the existing origination system within 60 days. A secondary deliverable is an estimate of the expected-loss reserve impact if the revised PD/LGD estimates are applied to the current live portfolio, which will be disclosed to the Audit Committee before the next earnings call.

## Key Constraints
- **Hard:** The revised model must pass SR 11-7 model risk management standards — any change constitutes a material model change and requires independent validation sign-off before deployment
- **Hard:** The expected-loss reserve impact must be calculated and disclosed to the Audit Committee before the earnings call (60-day deadline is immovable)
- **Soft:** The pricing committee prefers continuous spread adjustments rather than discrete band reclassification, to minimize disruption to relationship managers' quoting workflows
- **Soft:** The CCO wants the corrected model to remain explainable to regulators without black-box ML approaches — logistic regression or scorecard form preferred

## Available Data / Known Gaps
- **Available:** 28 quarters of origination data including facility terms, industry code, RAROC model output at origination, and actual credit outcome (default/non-default, recovery); current live portfolio detail; model documentation and validation history; peer bank benchmark loss rates from FR Y-14 data (publicly available at aggregate level)
- **Gaps:** LGD actuals are available only for defaulted loans (selection bias — healthy loan recoveries are unobserved); the 2019 model was calibrated on a 2009-2018 historical period that may not reflect post-pandemic credit dynamics; competitor pricing data is not available, so adverse selection can only be inferred indirectly from win-rate patterns

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** unique
- **Verifiability:** direct
- **Flags:** distributional: true, intractable: false, reflexive: false, gameable: false
- **Classification rationale:** There is one statistically correct answer to whether the PD/LGD parameters are miscalibrated and by how much — this is a parameter estimation problem with a defined objective function (minimize systematic pricing bias on backbook). Verifiability is direct because actual credit outcomes (default/non-default) are observable within the 28-quarter window. Distributional because both PD and LGD are distributional quantities and the reserve impact output is explicitly a distribution over expected losses, not a point estimate.
