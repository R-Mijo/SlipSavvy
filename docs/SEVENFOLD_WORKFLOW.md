# Sevenfold product contract

Updated November 9, 2026. Intended product, not a claim that every stage is implemented. Supersedes narrower builder interpretations in issues #3/#9.

## Customer flow

1. Choose sport, date/time zone, number of legs (2/3/4 initially), allowed markets and composition.
2. Optionally choose preferred teams, players or games; lock exact selections or choose every desired leg. Set total stake, return floor and explicit price/risk limits. Use selections, not manual game/odds/probability entry.
3. Generate researched candidate tickets. Mix moneyline, spreads, totals and player props. Four legs can come from two games. Never enforce one game per leg as the final design.
4. Show concise assessments, shared per-game evidence and leg-specific implications, expandable Parlay Info, Weather Info and Analytic Info, with supported comparisons. Permit insufficient data, no suitable alternative and no supported edge.

The current review branch adds a filters-first two-tab UI and bounded price-matched candidate search with source checks before suggestion. This is not the completed research-driven recommender. The manual tab allows mixed and same-game selections. Builder generation temporarily uses 2–4 distinct games so it can display a clearly estimated combined price without fabricating SGP offers. Locked-leg completion, predictive matchup ranking and same-game generation remain unfinished. Show useful available candidates even without an established edge; explain missing inputs and target shortfalls. The old unpublished price-distance experiment remains separate and untouched.

## Research and forecast requirements

Verify event/player identity, matchup, start/time zone and pregame status. Cover material injuries, practice/game status, availability/starters, role/usage/snaps, recent form, opposition, pace/game scripts, rest/travel, venue and actual roof state. Retain source URLs, provider observation/update time, retrieval time, validity and missing/stale/ambiguous status. No injury rows does not mean everyone is healthy. A provider player description is not an established roster/GSIS mapping.

Use event-specific venue evidence. Weather must describe the kickoff hour, units and missing fields. Never infer indoor status from a sport/team name or a closed retractable roof from a stadium's existence. Narratives do not create numerical probability adjustments.

Forecasts require as-of inputs, chronological held-out evaluation, calibration and baseline comparisons. Spread/total/prop and joint forecasts need appropriate outcomes, beyond a winning-team classifier. Represent uncertainty and dependence. Simulation precision is not calibration; evaluation-reference metadata is not independent validation. De-vigged prices remain market-derived estimates.

## Comparisons and settlement

Compare the original, dropping a leg, actually offered alternate points, and useful splits including three two-leg tickets versus one six-leg ticket. Hold total capital fixed, allocate it explicitly, and state which settlement outcome each payout describes. Distinguish any ticket cashing from positive overall net profit. Show supported expected net, full-stake downside, payout sacrificed and return-floor feasibility. Allow no supported comparison.

Use actual combined prices with book, timestamp and settlement terms. Never multiply same-game marginals/prices into a joint forecast or alleged sportsbook quote. Joint simulations settle same-game legs on shared outcomes. Handle pushes, voids, non-participation, overtime and partial-void repricing. Correlation pricing is not automatically additional vig. Unknown terms stay unknown; never invent promotional rules.

## Seven internal responsibilities

| Seat | Responsibility |
| --- | --- |
| Jeeves | Verify facts, identities, schedule, availability and research. |
| Luna | Compare eligible combinations, alternate lines and payout tradeoffs. |
| Pax | Check exposure, conflicting bets, concentration and downside. |
| Winston | Reconcile exact odds, stake, gross/net payouts and margin arithmetic. |
| Lisa | Assess game scripts, dependence, model basis and sensitivity. |
| Diego | Check actual promotion and settlement terms/eligibility. |
| Gus | Audit evidence, arithmetic and unresolved assumptions internally. |

All seven remain internal checks; the customer sees concise advice and expandable evidence without seven named responses. Current findings are deterministic checks, not seven researched LLM calls.

## Delivery and status

New subscriptions budget: **$0**. Reuse configured server-side access; no credentials in clients/logs/documents. No purchases or auto-billing trials. New branches and tested PRs; no merges, deployments or cloud builds without authorization. Exports/synthetic tests do not prove physical-device execution. The user confirmed Android opens after the merged startup repair.

Verified main on November 9: `ac5346e` (PR #10 merge). GitHub marks PRs #11–#13 merged, but their base branches were the preceding feature branches. They did not reach main through those merges. This review branch includes their reviewed code; it does not deploy or merge anything into GitHub main.

| State | Functionality |
| --- | --- |
| Verified main | Android startup fix, report contract, team/prop selection, dates/time zones, alternate retrieval backend. |
| Included dependencies in this PR | Free NFL snapshots, three-venue weather pilot and uncertain alternate settlement handling from #11–#13. |
| New in this PR | Two tabs, sport icons, filters-first bounded candidates, automatic research, odds-derived score, collapsed evidence, candidate and split price comparisons, bottom analysis action, inactive sponsors section. |
| Separate unpublished experiment | Earlier team-only price-distance builder; untouched and not the finished product. |
| Still unfinished | Predictive matchup ranking beyond source-check rules; locked-leg completion; same-game candidate generation/actual combined quotes; full venue and role/usage/recent-form coverage; evaluated forecasts; settlement-aware expected outcomes; accounts, ads integration and release verification. |

See [mobile flow and implementation bounds](MOBILE_FLOW.md).
See [free NFL sources](FREE_NFL_SOURCES.md) and [API contract](GAME_REPORT_API.md).
