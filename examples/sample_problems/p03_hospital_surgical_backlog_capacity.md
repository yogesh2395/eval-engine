# Hospital Surgical Backlog and Inpatient Bed Capacity — Post-Pandemic Throughput Recovery

## Industry & Value Chain
- **Industry:** Healthcare (acute-care hospital system)
- **Company type:** Regional not-for-profit health system (3 hospitals, ~900 licensed beds, tertiary-level surgical services)
- **Value chain position:** Capacity planning / Operations
- **Source reference:** Synthesized from ScienceDirect lean-AI hospital bed capacity study (sciencedirect.com/science/article/pii/S3050837126000019) + PMC study on managing cancer surgical backlog (ncbi.nlm.nih.gov/pmc/articles/PMC10350851/) + PMC COVID elective surgery case distribution study (ncbi.nlm.nih.gov/pmc/articles/PMC7711259/)

## Business Context
A three-hospital regional health system is carrying a surgical backlog of approximately 4,200 cases as of Q1, representing elective and semi-elective procedures deferred during COVID-19 and not yet cleared. Simultaneously, inpatient occupancy across the system is averaging 87% — above the 85% threshold that research associates with measurable deterioration in patient safety outcomes. The surgical backlog is not uniform: 38% are orthopedic procedures (high bed-days-per-case), 29% are general surgery (shorter LOS), and 19% are cardiovascular (high ICU dependency). Staffing shortfalls compound the problem: OR nursing vacancy rate is 14%, and post-surgical recovery bed nursing vacancy is 19%. The system's board has set a target of clearing 80% of the backlog within 18 months while maintaining current safety and quality metrics.

## Problem Statement
> The CMO has been asked to produce a 12-month operational plan that maximizes surgical throughput given current staffing, OR, and inpatient bed constraints. The plan must specify: (a) which procedure categories to prioritize, in what sequence, and at what weekly volume; (b) what levers — extended OR hours, weekend sessions, bed management protocols, step-down unit redesign — should be activated and in what order; and (c) what the realistic probability distribution of backlog clearance looks like at 6, 12, and 18 months given the stochastic nature of staffing, emergency case volume, and patient no-shows. The primary metric is backlog cases cleared per week; secondary metrics are inpatient occupancy rate and surgical complication rate. The plan cannot exceed the board-approved supplemental staffing budget of $3.2M for FY-current.

## Key Constraints
- **Hard:** Inpatient occupancy must not be deliberately driven above 92% at any hospital (patient safety threshold)
- **Hard:** Supplemental staffing budget is capped at $3.2M for the planning year; capital requests require a 9-month approval cycle and are out of scope
- **Soft:** The CMO prefers to avoid adding Saturday OR sessions in perpetuity — one-time surge acceptable, sustained structural change requires union negotiation
- **Soft:** Payer-mix implications matter: the CFO wants backlog clearance weighted toward commercially-insured cases where possible, but clinical prioritization (urgency, wait time) must remain the primary criterion

## Available Data / Known Gaps
- **Available:** Backlog case list with procedure code, acuity class, wait time, and payer; OR block schedule and utilization data (24 months); inpatient bed census by unit by day (18 months); nursing vacancy and agency utilization data; historical case duration distributions by CPT code; emergency case arrival rate by day of week
- **Gaps:** No probabilistic model exists for staffing vacancy trajectory; patient no-show rates post-backlog scheduling are unknown (historical no-show data pre-dates the backlog accumulation period and may not generalize); ICU step-down protocol changes required for cardiovascular cases are pending medical staff approval with uncertain timeline

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** indirect
- **Flags:** distributional: true, intractable: true, reflexive: false, gameable: false
- **Classification rationale:** Multiple valid sequencing and lever-activation plans exist; verifiability is indirect because backlog clearance outcomes are not observable until months into the plan and depend on stochastic inputs (emergency case volume, staff attrition). Distributional because the key deliverable is explicitly a probability distribution over clearance milestones, not a point estimate. Intractable because joint optimization of procedure sequencing, OR slot allocation, bed assignment, and staffing across three hospitals and multiple procedure categories is NP-hard — heuristics and simulation are required.
