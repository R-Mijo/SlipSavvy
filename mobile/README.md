# SlipSavvy phone preview

Select a sport → date → game → sportsbook lines → Analyze. Betting selections come from The Odds API through the [private-beta service](../server/README.md); the app no longer offers manual selection, event, odds or win-chance fields. Up to eight lines stay in session memory. Nothing is placed with a bookmaker.

The interface starts with the device time zone. Users can choose another city/time zone, including international zones; game dates, start times, morning/afternoon/night groups and report timestamps follow that choice with daylight-saving rules. The choice lasts for the session. Morning is before noon, afternoon is noon–4:59 PM and night starts at 5 PM in the chosen zone. NCAA and other sports share the same date/day-part filters and eight-game pages. Dates represent games returned by the current feed, not an unlimited historical/future calendar.

The shared [SlipSavvy identity](../brand/README.md) remains configured for native icons, launch screen, header and favicon. This is an unsigned source preview; a new build/install is required to use this revision on a phone. The existing Expo project and signing credentials should be retained. See [PHONE_TESTING.md](PHONE_TESTING.md).

## Run and verify

Node 24 and npm are required. From `mobile/`:

```sh
npm ci
npm run check
npm test
npx expo install --check
npm run export
node tests/ui.cjs
node tests/odds-ui.cjs
npm start
```

For connected data, set `EXPO_PUBLIC_ODDS_API_URL` to the HTTPS backend and `EXPO_PUBLIC_ODDS_PREVIEW_TOKEN` to its preview-access value. Keep `ODDS_API_KEY` on the server only. Public Expo variables are embedded in the client; the preview token is an extractable beta gate, not per-user production authentication. Tests/export use `https://odds.example.test` and synthetic fixtures; they do not contact an odds provider or prove live credentials are configured.

## Parlay and reports

- Tap current lines to add them directly; tap the same line again to update its price rather than duplicate it. Remove any leg from the tray. Games from the same event remain recognizable across market changes.
- Adding legs updates a clearly labeled hypothetical independent-50% illustration. It educates about the extra conditions needed to win; it never labels price-derived probabilities as forecasts or multiplies same-game marginals.
- Choose a $5/$10/$25 total stake with one tap. A custom stake and optional minimum total return are under expandable options. No other betting details need typing.
- Analyze sends exact provider event IDs and structured market/outcome/point/player fields to `POST /api/game-reports`. Preview limits are eight legs, four games and four sport/market combinations. These are inherited server bounds, not a promise of unlimited coverage.
- NFL games expose on-demand main/alternate passing and rushing yards. Choose the market and load offered player lines; switch player/category from the returned choices without typing or another request. Mix props with team lines, including several legs in one game. Exact provider player descriptions are retained, not promoted to verified roster IDs. Participation/settlement and model estimates remain unknown. These are offered selections, not automated researched recommendations. See [full workflow and unfinished stages](../docs/SEVENFOLD_WORKFLOW.md).
- Expand mini reports for exact line/price, matchup/local date, game-script status, applicable weather, all seven short responses (Jeeves, Luna, Pax, Winston, Lisa, Diego, Gus), sources and timestamps. Same-game legs share event research and receive leg-specific findings. No memos.
- Changing picks, stake or return target cancels pending work and hides earlier reports. Cancelled/obsolete results cannot reappear. Expired quotes/evidence require another analysis. A changed or unavailable price is flagged rather than substituted into a recommendation.

The seven responses currently consist of deterministic responsibility-based evidence/math checks, not seven independent researched AI forecasts. With default server settings, context, venue/weather and model scripts will often be unavailable; that missing status is shown. See the [backend contract and source dependencies](../docs/GAME_REPORT_API.md). Whole-ticket win estimates, offered combined parlay prices, alternate-line optimization and split-ticket comparisons remain unavailable. The UI does not claim a smart bet or supported edge from missing research.

## Coverage and release gates

Current backend coverage: NFL, NCAAF, NBA, NCAAB, NHL and MLB; FanDuel and DraftKings; moneyline, spread and total. Current quotes are cached and can change. Actual sportsbooks must confirm availability and prices. Eight lines need not form a valid single-book ticket; no offered joint quote is assumed.

No screenshot/share import, trained prediction model, same-game joint model, automatic injury/lineup research, billing, account or wager placement is supplied by this UI. Existing math/manual-review utilities remain tested as libraries but are no longer entry flows. Entries and time-zone preferences clear on reload. The service receives selected lines and stake/return choices when analyzing; provider/source requests and infrastructure behavior need the release privacy audit. Source links open only on a user tap.

TypeScript, unit tests, all-platform Expo exports and exported-web interaction checks cover this revision. They do not replace native layout, accessibility, Hermes execution, or physical iPhone/Android tests. The [milestone record](../docs/MOBILE_MILESTONE.md) preserves earlier history and current boundaries. No cloud build, deployment or store submission is started by these checks.
