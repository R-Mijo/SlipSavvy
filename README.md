![SlipSavvy](docs/assets/banner.svg)

# SlipSavvy

Brand assets and usage: [SlipSavvy visual identity](brand/README.md).

**Check the math behind your bet slip.**

SlipSavvy is a local ticket assistant and Python library for scenario probabilities, payout calculations and portfolio risk. Optional weather retrieval makes an explicit outbound request. It moves arithmetic and bounded searches out of model conversations and into reproducible code.

**0.3.1 | Python 3.11+ | Apache-2.0 | Python engine: no third-party runtime dependencies**

## In plain English

SlipSavvy is a ticket-research and math assistant. It explains each leg, compares ticket probabilities and payouts, and runs transparent scenarios. For example, it shows why six independent 60% legs have only a 4.6656% chance of all winning. Its current probabilities are supplied by the user or scenario author, not produced by a validated sports prediction model.


## Your bets. We’ll do the math.

The local app now starts with the selection, American odds and stake. It uses “bet,” “selection” and “parlay” in the main flow. Sources, weather notes and custom probabilities sit under optional details. You do not need to invent a win probability: an explicitly labeled odds-only starting point can be used for calculator scenarios. That starting point includes bookmaker margin and is not a prediction or calibrated confidence score.

The hosted product page introduces the product and provides an interactive payout preview. The full Python simulations run in the local app. Native iPhone/Android apps remain in development.

The local assistant also accepts an optional opposing American price for a complete two-outcome market. It proportionally removes the supplied market margin unless you provide your own probability estimate. Both outcomes must belong to the same market and time. A one-sided odds-only scenario leaves expected net unavailable; its price-derived hit score is not a forecast. See the [quantitative methods](docs/QUANTITATIVE_METHODS.md) for the assumptions and a worked example.

See [comparison with established quantitative methods](docs/QUANTITATIVE_METHODS.md). No access to private syndicate models or equivalent profitability is claimed.

## Native phone preview

The [iPhone/Android development preview](mobile/README.md) now has a manual selection → review → confirm → payout flow, plus an education tab. It uses exact fractional payout math and keeps user-supplied win estimates separate from price thresholds. Independent combinations require explicit opt-in; same-game combinations are excluded by the entered event names. Entries stay in memory for the session.

This preview does not include screenshot recognition, live feeds, the Python simulations, billing, signed phone binaries or store approval. Platform bundle compilation and web interaction checks are separate from physical-device testing. See the [milestone and next release gates](docs/MOBILE_MILESTONE.md).

## Ticket assistant and 100,000-run simulations

```sh
python -m slipsavvy ui
python -m slipsavvy simulate examples/assistant-ticket.json --trials 100000 --seed 42
python -m slipsavvy education
```

The local app opens at `http://127.0.0.1:8766`. Its Ticket Assistant, Learn the Odds and Weather Desk tabs provide:

- Per-leg source/capture-time, weather/roof and game-script context, with missing fields shown.
- Seeded Python Monte Carlo runs (100,000 by default), checked against an exact analytical result under the same assumptions.
- Weighted game scripts shared across a trial, with explicit conditional-independence assumptions.
- A model-estimated hit score out of 100 for each leg and the ticket. This is a probability display, not calibrated confidence, a data-quality grade or a betting recommendation.
- Simulated wins/losses, gross and net return, expected net, and a sampling-only 95% interval. Model error is not included in that interval.
- An interactive 1–6-leg probability lesson and American-odds / decimal-price / break-even ladder. Multiply decimal odds; do not add American prices.
- Optional stadium-coordinate weather forecasts with UTC timestamps and Open-Meteo attribution. Forecasts do not automatically adjust probabilities. Review commercial API terms before charging for a connected service.

**Advertisable now:** “Explore your ticket with Python-powered 100,000-run Monte Carlo simulations and transparent game-script assumptions.”

**Not established:** predictive accuracy, a verified edge, calibrated confidence scores, automated live odds/injury feeds, screenshot parsing in a released native app, paid subscriptions or App Store availability. The iPhone/Android app remains in development. See [product roadmap](docs/PRODUCT_UPDATE.md).

## Run it

```sh
python -m slipsavvy demo
python -m slipsavvy analyze examples/scenario.json
python -m unittest discover -s tests -v
```

Install with `python -m pip install .` to use the `slipsavvy` command. Inputs are caller-supplied scenarios; the program fetches no live odds and places no bets.

| Component | Implemented responsibility |
| --- | --- |
| Scenario engine | Enumerates up to 16 binary outcomes with valid exclusive groups and conserved probability mass. |
| Stake comparison | Searches a declared stake grid under capital, candidate-count and time limits. |
| Risk report | Calculates wipeout, loss, net-positive and target probabilities from the full state distribution. |
| Payout calculator | Calculates exact rational prices, returns, boosts and expected net without double-counting stake. |
| Probability model | De-vigs complete markets and validates explicitly supplied dependence through joint distributions. |
| Promotion checks | Validates promotion expiry, minimum odds, use limits and permitted cap treatment. |
| Independent audit | Recomputes the ledger and risk results, checks evidence references, and reports vetoes/assumptions. |

## State the assumptions

`game_id` denotes **one mutually exclusive outcome group**, not all props in a sporting event. For two exhaustive 50/50 outcomes, `(1,0)` and `(0,1)` each receive 0.5; `(1,1)` and `(0,0)` receive zero. Partial groups retain an explicit neither-outcome remainder.

Different groups require `assume_independent_groups=True` or a full joint distribution. Nonzero pairwise covariance is rejected because it cannot specify a multi-event distribution. Joint probabilities must be nonnegative, sum exactly to one, match marginals and exclude impossible states. Inconsistent exclusive probabilities are rejected rather than silently normalized.

Supply scenario probabilities or both market-side prices for two-way de-vigging. Prices are not proof of true win probability. Evidence defaults to unverified. A Tier-1 label needs a reference whose authenticity remains your responsibility. `ANALYSIS_READY` is an analysis status, not execution authorization.

## Precision and promotions

Inputs accept decimal strings or fractions such as `"1/3"`. Internal probabilities/payouts use `Fraction`, so `$299.99` never becomes `$300` in a target comparison. JSON renders readable decimal strings; internal comparisons stay exact.

Payouts model the stated mathematical contract before sportsbook rounding, taxes, voids, pushes and other settlement rules. Supply quoted decimal prices where applicable. Stakes above a promotion cap are rejected unless `allow_split_stake=True` explicitly states the real promotion permits boosted-plus-base treatment. Reuse requires a matching `max_uses` rule.

## Bounded optimization

```python
from slipsavvy import BinaryEvent, Ticket, StakeOptimizer

events = [BinaryEvent('A', 'GROUP-1', 'Scenario A', 100, fair_prob_override='0.5')]
result = StakeOptimizer.search(
    events, [Ticket('T1', ('A',), '1')], [0, 5, 10],
    capital_limit='10', target_gross='20', max_candidates=1000,
)
print(result['optimality'])
```

`OPTIMAL_WITHIN_DECLARED_GRID` means every combination in the supplied templates/stake grid was visited. Limits return `BEST_FOUND_LIMIT_REACHED`. Neither claims optimality outside that grid. Search supports at most 10 templates and 10 events.

Created by Marco Armijo. [License](LICENSE) · [Notice](NOTICE) · [Contributing](CONTRIBUTING.md)
