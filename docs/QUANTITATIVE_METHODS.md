# Professional methods, plain-English interface

This is a comparison with publicly documented quantitative betting methods, not a claim to know a particular syndicate's private process, data, profitability or algorithms.

| Quantitative practice | SlipSavvy today | What remains |
| --- | --- | --- |
| Convert prices and compare payouts | Exact Python price arithmetic; accessible payout preview | Live licensed cross-book price comparison |
| Remove bookmaker margin | Python engine and local assistant can proportionally de-vig complete two-way markets; the local form accepts the opposing price | A reviewed retail import flow verifying both sides belong to the same market and time |
| Evaluate uncertainty with simulations | Seeded 100,000-run Monte Carlo and analytical cross-check | Sports-specific validated generative models |
| Account for dependence | Explicit independence assumptions and shared weighted scenarios; full engine accepts joint distributions | Calibrated same-game models, not a universal correlation guess |
| Verify predictive probabilities | User estimates or an explicitly labeled odds-only starting point | Held-out backtesting, calibration curves and scoring such as Brier score |
| Track market-relative performance | No live closing-line tracker | Timestamped comparable markets and no-vig closing prices |
| Control risk | Existing scenario loss analysis and bounded stake searches | Consumer bankroll workflow and independently validated sizing assumptions |

The retail interface says “bet,” “selection” and “parlay.” More technical terms appear only when useful, with explanations. Users can enter odds and a stake without inventing win probabilities. In odds-only mode the starting probabilities are the prices' implied break-even rates, including bookmaker margin. These are not calibrated forecasts or a discovered edge. Reusing the same prices for probabilities and payouts creates a circular zero expected net at multiplied prices. The assistant therefore returns `expected_net_under_model: null` whenever a scenario relies on any single-sided price-only probability. A custom quoted payout does not establish the missing probabilities.

An optional `opposing_american_odds` value lets the assistant use proportional two-way normalization from `ProbabilityModeler.devig_two_way`. Both prices must describe mutually exclusive, exhaustive outcomes from the same market and time; a draw or third outcome invalidates that interpretation. An explicit `win_probability` takes precedence, followed by complete two-way prices, followed by the opted-in raw price scenario. Explicit game-script probabilities supply the scenario assumptions. De-vigging is a market-derived estimate, not a validated forecast or proof of true probability.

For illustration, two independent selections each priced at -110, each with an opposing -110 price, normalize to 50% each and 25% together. Their hypothetical multiplied decimal price is 441/121. On a $10 stake the model's expected net is -215/242 dollars, about -$0.89, or an 8.8843% expected loss under these assumptions. The two-way market overround is 4.7619% per market; overround, a selected bet's expected loss and a combined bet's expected loss are different quantities. With only one price for each selection, the true loss rate is not established.

## Evidence for the comparison

- [Pinnacle's own description of its calculators](https://www.pinnacle.com/en/corporate/press/press-release/pinnacle-launches-interactive-betting-tools) documents stake/odds payout calculations, odds conversion and bookmaker-margin tools.
- [Walsh and Joshi's sports-betting calibration study](https://arxiv.org/abs/2303.06021) examines calibration versus accuracy. Its results do not validate SlipSavvy or guarantee returns in other markets.
- [Pinnacle on professional betting returns](https://www.pinnacle.com/betting-resources/en/betting-strategy/how-often-do-professional-bettors-get-paid/k2s22xf7s22scgmz) discusses variability and Monte Carlo for more complicated betting histories. Sharing a mathematical technique is not evidence of matching a professional operation's capabilities.

Appropriate marketing: “Clear betting math and transparent scenarios, using established quantitative techniques.” Avoid “the same system as winning syndicates,” “syndicate-grade edge,” and untested accuracy or confidence claims.
