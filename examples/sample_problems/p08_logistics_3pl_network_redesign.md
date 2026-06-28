# 3PL Last-Mile Network Redesign — Depot Location and Route Optimization Under E-Commerce Growth

## Industry & Value Chain
- **Industry:** Logistics / Third-Party Logistics (3PL)
- **Company type:** Regional 3PL carrier (~$800M revenue, operates parcel and freight last-mile delivery for e-commerce retailers across a 12-state footprint)
- **Value chain position:** Distribution / Logistics network design
- **Source reference:** Synthesized from MIT last-mile distribution network case study in São Paulo (dspace.mit.edu/handle/1721.1/121320) + ScienceDirect 3PL warehousing and distribution network optimization (sciencedirect.com/science/article/pii/S2405896322022200) + MDPI multi-criteria last-mile optimization including smart lockers (mdpi.com/2305-6290/8/2/52)

## Business Context
A regional 3PL operates 18 delivery depots across a 12-state footprint, a network designed in 2015 for a retailer-dominated parcel volume mix. Since 2020, the volume mix has shifted dramatically: e-commerce now represents 71% of parcel volume (up from 34%), driving a 2.4x increase in residential stop density, smaller average package size, and higher delivery-attempt failure rates (currently 11.3%, up from 6.8%). Three of the 18 existing depots are on long-term leases through 2031 and cannot be closed without significant penalty. The 3PL's two largest e-commerce clients together represent 58% of revenue and have signaled they will re-bid their contracts in 18 months; both are benchmarking the 3PL against national carriers on cost-per-stop and on-time delivery rate. The 3PL's cost-per-stop has risen 31% over three years, from $4.12 to $5.39, while the two largest clients' contracts are indexed to a fixed-rate schedule that was set in 2021.

## Problem Statement
> The COO has been asked to produce a network redesign recommendation for the next 36-month planning horizon: which of the 18 depots to retain, consolidate, or relocate; whether to add micro-fulfillment nodes or parcel locker partnerships in dense urban zones; and what the optimal depot-to-route assignment should look like given current and projected volume by zip code. The primary metric is cost-per-stop; the secondary constraint is maintaining or improving the on-time delivery rate (currently 94.2%, client SLA threshold is 96%). The redesign must be implementable in phases that do not expose the 3PL to a service disruption gap during the 18-month client re-bid window. The capital budget for depot changes (new leases, fit-out, technology) is $22M over 36 months.

## Key Constraints
- **Hard:** Three depots are locked on leases through 2031 — they cannot be closed; the network must be designed around these anchors
- **Hard:** During the 18-month client re-bid window, on-time delivery rate must not fall below 94.2% at any point — a service dip during re-bid would likely result in contract loss
- **Soft:** The COO prefers to avoid depot relocations that require relocating more than 40 drivers (labor disruption risk); smaller consolidations and new micro-node additions are preferred
- **Soft:** The 3PL's sustainability commitments to its clients call for reducing vehicle miles traveled per package by 15% by 2027; solutions that worsen VMT are acceptable only if they significantly reduce cost-per-stop

## Available Data / Known Gaps
- **Available:** 24 months of stop-level delivery data (zip code, delivery attempt outcome, vehicle, depot origin, timestamp); lease terms and penalty schedules for all 18 depots; driver headcount and union agreement terms by depot; projected volume by zip code for 3 years (provided by top-5 clients); parcel locker locations available from three national locker networks (API available); real estate cost indices for the 12-state footprint
- **Gaps:** Competitor depot locations are not publicly mapped — the 3PL is operating without visibility into where national carriers have added capacity; failed delivery re-attempt cost is tracked at the aggregate level but not by zip code, preventing precise identification of the highest-cost failure zones; client volume forecasts beyond 18 months are uncertain and clients have contractual flexibility to shift 15% of volume to a secondary carrier

## Pre-Qualifier Annotation
*(For generator reference — not seen by consultant)*
- **Cardinality:** multiple
- **Verifiability:** indirect
- **Flags:** distributional: false, intractable: true, reflexive: false, gameable: false
- **Classification rationale:** Multiple valid network configurations exist (no single optimum given lease anchors, capital constraints, and volume uncertainty). Verifiability is indirect because cost-per-stop improvements manifest over 12-24 months after network changes and are confounded by volume growth, fuel prices, and labor costs. Intractable because the joint facility-location-and-vehicle-routing problem across 18 potential depot sites, thousands of zip-code delivery zones, and multi-period phasing is NP-hard — exact optimization is infeasible at this scale.
