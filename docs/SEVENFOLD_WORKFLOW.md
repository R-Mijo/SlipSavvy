# Sevenfold product contract

Updated November 7, 2026. Intended product, not a claim that every stage is implemented. Supersedes narrower builder interpretations in issues #3/#9.

## Customer flow

1. Choose sport, date/time zone, number of legs (2/3/4 initially), allowed markets and composition.
2. Optionally choose preferred teams, players or games; lock exact selections or choose every desired leg. Set total stake, return floor and explicit price/risk limits. Use selections, not manual game/odds/probability entry.
3. Generate researched candidate tickets. Mix moneyline, spreads, totals and player props. Four legs can come from two games. Never enforce one game per leg as the final design.
4. Show concise assessments, shared per-game evidence and leg-specific implications, expandable Sevenfold findings and supported comparisons. Permit insufficient data, no suitable alternative and no supported edge.

The current phone still browses games/lines before analysis. The NFL props addition is a selection/report milestone; filter-first automatic generation and locked-leg completion are unfinished. Do not label a price-distance filler builder as the researched product. A customer can exclude extreme favorites (for example -900) explicitly; price alone does not establish bad value.

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

All seven have concise expandable findings; no memos or purported external ChatGPT audit. Current findings are deterministic checks, not seven researched LLM calls.

## Delivery and status

New subscriptions budget: **$0**. Reuse configured server-side access; no credentials in clients/logs/documents. No purchases or auto-billing trials. New branches and tested PRs; no merges, deployments or cloud builds without authorization. Exports/synthetic tests do not prove physical-device execution. The user confirmed Android opens after the merged startup repair.

Starting main: `a25b4c9cd296e51343537999a7b3373c1c10593a`.

| State | Functionality |
| --- | --- |
| Merged #4/#5 | Authenticated reports, shared per-game context contract, selection-only tray, date/time-zone filters and seven cards. Research feeds/model not connected. |
| Merged #7 | Android loading-role fix; user confirms rebuilt app opens. |
| Merged #8 | Offered alternate spread/total retrieval, cache and shared weighted reservations. No mobile alternate selector/optimizer. |
| This branch, pending review | On-demand NFL passing/rushing main and alternate lines, mixed-market selection and exact prop matching in reports. Model/joint price/settlement remain unknown. |
| NFL research branch, pending review | Free schedule/roster/injury snapshots and phone display, exact event/GSIS matching, distinct file times and missing/stale/unknown coverage. No confirmation of current participation or probability adjustment. |
| Venue/weather branch, pending review | Exact event venue ID/name plus reviewed sources; Lumen Field NWS weather, fixed-indoor U.S. Bank Stadium and unresolved-retractable Lucas Oil Stadium. Other venues unavailable; no probability adjustment. |
| Separate unpublished experiment | Earlier team-only price-distance builder. No files from it are included here; its one-game-per-leg rule and price-only generation are not accepted product behavior. |
| Unfinished | Filter-first research/generation; complete injury/context/weather feeds; evaluated forecasts; combined SGP offers; settlement-aware fixed-capital comparisons; six-game reports; share/import; production accounts/billing; iPhone/device release checks. |

See [free NFL sources](FREE_NFL_SOURCES.md) and [API contract](GAME_REPORT_API.md).
