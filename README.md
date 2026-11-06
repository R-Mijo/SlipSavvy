# SlipSavvy

**Check the math behind your bet slip.**

SlipSavvy is an offline Python library for scenario probabilities, payout calculations and portfolio risk. It moves arithmetic and bounded searches out of model conversations and into reproducible code.

**0.2.0 | Python 3.11+ | Apache-2.0 | No third-party runtime dependencies**

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
