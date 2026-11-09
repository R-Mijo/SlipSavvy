# Two-tab mobile research preview

This implementation is a usable UI and candidate-search and source-check milestone, not the completed research-driven AI recommendation engine. It does not reuse or publish the earlier local price-only builder experiment.

## Flow

- Sport icons appear first. Savvy Parlay Builder starts with sportsbook, 2–4 legs, $5/$10/$20 stake and desired total return including stake.
- Build requests three team markets only after a tap. Optional NFL props check main passing/rushing lines on the four earliest available events; alternate props require a separate explicit toggle. There are at most eight event-prop requests, in sequence, and the existing server cache/quota remains authoritative. This can consume existing free odds credits; it does not buy a subscription.
- The bounded price search considers at most 24 upcoming event groups and 64 offers per event, retaining 128 states per ticket length. It returns up to three nearest candidates found, without claiming a global optimum or predictive ranking. Each ticket uses one sportsbook and distinct events; the current report limit remains four games/four market lookups. An unattainable target returns the nearest found ticket and a dollar shortfall when a complete ticket exists. Missing markets are disclosed.
- Chosen lines retain their provider identities and prices. Duplicate IDs, conflicting event identity, expired quotes, unsupported fields and unclear integer alternate milestones cannot enter generated tickets. Changing filters or cancelling aborts pending work; obsolete responses cannot install a ticket.
- Up to three price-matched candidates receive sequential reports before a ticket is suggested. Review order prefers matched prices and eligible players, then fewer missing evidence fields, then fewer listed concerns, then proximity to the return target. Listed Out player props and changed/unmatched prices are withheld from automatic selection. Missing evidence does not become reassurance. The chosen ticket reuses its current decoded report; expired or failed research can be retried. These rules rank evidence readiness, not win likelihood, and are not a trained or generative AI model. Main/alternate rationale compares supplied prices where available and says when no comparison was checked.
- My Picks & Research retains dates/time zones, team markets and on-demand NFL props. Users can select up to eight lines including same-game combinations, within report limits. Both tabs share the in-memory ticket. Switching tabs or changing stake/target can invalidate a report. Analyze sits below selection controls and the ticket.
- Parlay Info, Weather Info and Analytic Info start collapsed. Per-game weather is displayed once. The customer sees a brief finding plus evidence, without named Sevenfold personas. Internal report validation still requires all seven responsibility checks.

## Price score and comparisons

The score is `100 / decimal odds`, with five equal 20-point color bands (very low, low, moderate, high, very high). It is explicitly based on sportsbook odds, includes margin, and is not a calibrated forecast, research-confidence score or bet-value rating. A high score must not be labeled a great bet.

For different games at one sportsbook, multiplication of individual decimal prices is only an estimated combined price; actual acceptance and pricing require sportsbook confirmation. Same-game, mixed-book, stale or altered quotes do not get a combined score or payout. No actual SGP quote input is connected in this milestone. Individual captured line scores remain labeled as such.

Parlay Info compares two smaller tickets with the same total capital. Odd cents go to the second ticket. Both-win, first-only, second-only and neither-win return scenarios are explicit; amounts include stake. These estimates assume standard all-win/all-loss settlement. They are not expected returns or probabilities, and pushes/voids can change them. No promotional grading rules are inferred.

## Research and revenue boundaries

The carried-forward research adds free nflverse snapshots and the three-venue NWS pilot. It does not establish current participation, cover every stadium, or provide evaluated game-script forecasts. Missing information remains visible. The ranking now uses source checks, but full matchup/role/usage/recent-form ranking, generative game scripts, locked-leg completion, same-game generation and settlement-aware comparisons remain outstanding. A listed injury creates a concern, not a quantified outcome effect. Forecast wind of at least 20 mph triggers a review note (a transparent heuristic, not an evaluated betting rule); no automatic Over/Under or win-probability adjustment is made. Weather and sourced context remain available in the expandable evidence.

Offers & Sponsors is a collapsed, empty section after core analysis and the session notice. No advertiser, ad SDK, tracking, paid placement, ad revenue or eligibility is claimed. Future ads must be clearly labeled and independent of candidate ranking; adding a provider requires a separate reviewed change. This source revision makes no purchases, deployment, cloud build or store submission.

## Verification

Unit tests cover price conversion, ticket eligibility, generated-offer identity and main/alternate price tradeoffs. Exported-app interaction tests cover filters, automatic research, target shortfall, fixed-budget split scenarios, research-driven reordering, cancellation, stale/changed selections, collapsed evidence, weather units/provenance and mixed player research. Expo exports cover Android/iOS/web bundles. Physical-device layout, accessibility and production connectivity still require the owner’s next test build.
