# Gemini Argon findings: independent verification

## Native odds-browser review — November 6, 2026

The user supplied Gemini Argon's written review of PR #1 at `1404ec4c790f158f9b7cecf3b423ecf91945518a`. Independent reproduction used current branch head `375e36a17faeb30a75a9725850c6ca75d85762c5`, whose intervening branding change left the affected odds behavior unchanged. Gemini's findings arrived in chat; they were not already published as a GitHub review or code commit.

| Finding | Independent reproduction | Resolution |
| --- | --- | --- |
| A price edit can retain a hidden quote and revert on a later edit; changing only the user's win estimate loses feed provenance | Reproduced with a leaked-quote unit input and the actual exported app. Edited +150 reverted to -110 after reopening; an assumption-only edit changed the source to unverified. | Drafts now copy only editable fields, manual review clears quote metadata, and quote-detail edits detach the feed and get a manual ID. Assumption-only edits keep feed identity, attribution and freshness checks. Review, confirmation and calculation all recheck freshness. |
| Market/refresh changes reset the selected game; quote buttons remain after an expired-line error | Reproduced in the exported app. Spread selection required selecting the same game again, and the expired button remained after an error. | Retain the game across market/refresh changes while returned quotes contain its ID. Clear it on sport change or removal from the results. Hide games and quotes while an error is shown. |
| Upstream clock skew, zero total/signed-zero spread formatting, and slicing before event filtering | Reproduced in server regressions. A 30-second-future update was omitted, Over 0 was accepted, and 100 started/wrong-sport entries hid a later valid event. | Apply the same 60-second future tolerance on fresh and cached quotes, reject nonpositive totals, normalize zero spreads to +0, and cap 100 eligible upcoming events after filtering. |
| Provider IDs and mixed manual/feed names are not consistently excluded as same-game selections | Reproduced: changed display names for one provider event and a feed/manual pair without the ID suffix both produced a combination. | Compare provider IDs when both picks carry quotes; otherwise compare normalized base names, removing a known suffix on either side. Distinct provider IDs with identical matchup names remain distinct. Manual aliases remain a documented limitation. |

Gemini's suggested fresh manual ID needed an additional safeguard: blindly appending the new ID would leave the original entry in the list or fail at eight selections. The editor now tracks the original replacement ID, and `replacePick` replaces that slot while rejecting collisions. Both unit and exported-app checks cover the capacity case.

New targeted regressions failed against the unchanged implementation before source fixes. Final verification: **49 Python tests, 28 mobile unit tests, seven exported-web interaction scenarios, TypeScript and all-platform Expo exports**. Fixtures are explicitly synthetic; no provider API credits or credentials are needed. The provider-key isolation and UTC-day quota design are unchanged. Hosting, durable production metering/authentication, new phone builds and physical-device verification remain pending.

---

November 6, 2026. Reviewed baseline: `afb5a5bf923a7fd45d8bd8d6c716f2b115d569ae` on `R-Mijo/SlipSavvy`. Every file in the clean verification source matched its GitHub blob SHA before edits. Main still matched this baseline. The separate native manual-entry work is in PR #1 at `ad9de928183d2c75a05754ae4a85f11c11525e8a`; this change neither replaces that branch nor claims it was reviewed by Gemini.

The user supplied Gemini's written findings. The note said Gemini had not pushed changes. No automatic cross-chat synchronization or independent access to Gemini's environment is assumed. Only affected SlipSavvy and Scrubbee code was reviewed; completed four-project setup and naming reviews were not repeated.

## Disposition

| Finding or suggestion | Independent result | Action |
| --- | --- | --- |
| Two -110 selections in the opt-in price-only scenario give 27.43764172335601% and zero expected net | Reproduced. The implied-rate calculation is internally consistent and already labeled, but the zero is circular and cannot establish house edge or true expected return. A single price cannot justify replacing the rate with 50%. | Withhold expected net when any scenario probability relies only on a single-sided price. Explain why in JSON and the local UI. |
| Assistant should accept `opposing_american_odds` | Baseline ignored the field and required an explicit probability or raw-price opt-in. The engine's existing proportional two-way normalization can supply a market-derived assumption. | Validate optional opposing prices, reuse `ProbabilityModeler.devig_two_way`, add a manual form field and distinguish its basis. Explicit user estimates and game scripts retain precedence. |
| Balanced -110/-110 example hides approximately 9.09% loss | Numerical qualification required. For two independent normalized 50% selections, multiplied price 441/121 and $10 stake, expected net is -215/242 dollars = -$0.8884297520661157: an 8.8842975% expected loss. Each complete market's overround is 4.7619048%. | Document the distinct quantities and assumptions; do not claim an observed or true loss rate. |
| Website preview renders a stray + before break-even percentage | Not reproduced. Running the current `site/index.html` with two -110 inputs renders `27.44%`. The source's plus operator concatenates strings; it is not a displayed plus character. | Preserve the working payout preview. |
| Two Pinnacle references are dead | Not established. The calculator press URL fetched successfully. The returns article appeared with its full relevant text in primary-site search results while direct retrieval timed out. Walsh/Joshi's arXiv page fetched successfully. | Preserve all three references; do not substitute unverified URLs. |
| Add stadium database and National Weather Service adapter | New feature, not a reproduced bug. Roof status and coordinates need sources, dates and maintenance; commercial suitability requires its own review. | Defer to a separately scoped source/weather milestone. No provider switch, endpoint request or Site deployment is part of these fixes. |

## Behavior and validation

Probability precedence without explicit game scripts: user `win_probability`, then both complete-market prices, then explicit price-only opt-in. Opposing prices are validated even if an explicit estimate is present. Both prices must be mutually exclusive, exhaustive outcomes of the same market and time. Markets with a draw or a third outcome require the full market, not this two-way interface. No-vig estimates are uncalibrated market-derived assumptions.

`expected_net_under_model` is now nullable. Single-sided price-only scenarios return null, including mixed estimated/raw scenarios and custom quoted payouts. Explicit game-script probabilities supply their own assumptions and permit a model expected-net calculation. Existing simulation and payout fields remain available. Consumers must handle null rather than format it as a number.

Before the fix, new targeted tests reproduced the old zero expected net and failure to consume opposing prices. After the changes, `python -m unittest discover -s tests -v` passed all **40 tests**, including HTTP JSON null and two-way price requests. Local DOM interactions verified that blank opposing fields are omitted, entered fields are sent, unavailable expected net is explained, and the balanced example displays 25/100 and -$0.89. These are functional checks, not visual or physical-phone tests. The public payout preview's no-stray-plus reproduction also passed.

The initial local HTTP runs could not connect until network permission for temporary loopback apps was granted; full suites then passed. GitHub CI results and the exact resulting commit SHA are recorded in the accompanying pull request. No mobile implementation, live weather provider, signed build, billing, license or main branch was changed.

## Reproduce the principal calculation

```python
from slipsavvy.assistant import simulate
data = {'stake':'10', 'assume_conditional_independence':True, 'legs':[
    {'id':str(i), 'american_odds':-110, 'opposing_american_odds':-110}
    for i in range(2)]}
r = simulate(data, 1000, 42)
assert r['analytic_model_win_percent'] == 25
assert abs(r['expected_net_under_model'] - (-215/242)) < 1e-12
for leg in data['legs']:
    del leg['opposing_american_odds']
data['use_price_implied_probabilities'] = True
r = simulate(data, 1000, 42)
assert r['expected_net_under_model'] is None
```

Further Gemini reviews should name the exact PR head commit, file/line, reproduction input, expected/observed behavior and evidence. Reproduce a finding against that version before changing behavior. PR #1 remains the separate phone-interface milestone; this verification does not imply Gemini reviewed it.
