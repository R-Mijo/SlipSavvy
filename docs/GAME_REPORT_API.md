# Game-report backend v1

Implements the first backend slice of [issue #3](https://github.com/R-Mijo/SlipSavvy/issues/3). No mobile UI, deployment, betting, paid subscription, LLM call or trained forecasting model is included.

## Request

`POST /api/game-reports`, `Content-Type: application/json`, `Authorization: Bearer <existing ODDS_PREVIEW_TOKEN>`.

```json
{
  "totalStake": "10.00",
  "minimumTotalReturn": "90.00",
  "legs": [
    {
      "id": "L1",
      "eventId": "provider-event-id",
      "sport": "basketball_nba",
      "bookmaker": "fanduel",
      "market": "spreads",
      "outcome": "Exact provider team name",
      "point": -6.5,
      "americanOdds": "-110"
    }
  ]
}
```

All illustrated inputs are placeholders, not current game recommendations. `totalStake` is fixed total capital for a future comparison, **not a separate stake on every leg**. It is a required positive monetary string, at most $10,000 with up to two decimal places. `minimumTotalReturn` is an optional positive monetary string capped at $10 million; it preserves the customer's total-return floor for a future optimizer and does not itself cause any recommendation.

Leg fields are exact and case-sensitive. `id` is a unique local ID of 1–100 characters. `eventId` is the exact provider ID, 1–100 ASCII letters/digits/underscores/hyphens. `sport` uses the existing six-sport allowlist. `bookmaker` uses the provider key `fanduel` or `draftkings`, not its display name. `market` is `h2h`, `spreads` or `totals`; `outcome` is the raw team/outcome name, not a formatted label. `point` is required and numeric for spreads/totals, null/omitted for moneyline. Totals require positive points and `Over`/`Under`. `americanOdds` is an optional expected price; a differing current price returns `price_changed` and requires reconfirmation. It is never silently substituted into a value recommendation.

`GET /api/odds` now **additively** supplies `bookmakerKey`, `homeTeam`, `awayTeam`, `outcome` and `point`. Existing IDs, formatted labels and mobile fields remain unchanged. The future UI should map these fields directly into the report input. No parsing of selection labels or fuzzy event guessing is performed.

Limits: 1–8 unique legs, at most four distinct events and four sport/market lookups. Repeated selections under different IDs, arbitrary extra fields, URLs, duplicate JSON keys, nonfinite numbers, malformed amounts and unsupported markets are rejected before fetching. The first PR preserves current sport/book coverage; dynamic all-sport discovery and alternate-market support are separate work.

## Response

`200` means a report was assembled; it does not mean every source is available or the bet is endorsed.

| Field | Meaning |
| --- | --- |
| `schemaVersion` | `1` |
| `generatedAt` | UTC completion timestamp |
| `generationMethod` | `deterministic_evidence_findings`; seven responsibility-based findings, not seven independent AI model calls |
| `events[]` | One shared object per successfully matched event: provider identity, UTC and Phoenix/MST start, cited context, venue, weather and optional model script |
| `legs[]` | One mini report per requested leg, in request order, including failures |
| `assessment` | Whole-ticket state and fixed-capital comparison context |

Every leg contains `id`, original structured `selection`, `matchStatus`, nullable `eventRef`, nullable normalized `quote`/`quoteSource`, nullable `price`, nullable `gameScript`, `legImplication`, `weather`, nullable `modelWinProbability`, `probabilityBasis` and exactly seven short `seven[]` findings.

Each finding has `seat`, `name`, `status`, a one-item `bullets` list and `evidenceIds`. Names/order: **Jeeves, Luna, Pax, Winston, Lisa, Diego, Gus**. Status is `ok`, `needs_data`, `blocked` or `not_applicable`. `ok` indicates the specific structural/calculation check passed; it is not an assertion of independently validated predictive accuracy. Quote references resolve through that leg's `quoteSource`; other references resolve through the shared event's `context.evidence`.

Quote sources identify The Odds API, the provider update time and retrieval time. Context evidence is tagged `operator_supplied_reference`. The service validates identity, shape, timestamps and references; it does not fetch those source links or prove their semantic content. There are no memos, fabricated external Gus reviews, inferred roster facts or synthesized numerical forecasts.

`price` includes the exact decimal fraction and bookmaker break-even percentage. This percentage is a price threshold, **not a win forecast**. All same-game legs share the same `eventRef` and underlying script/weather; their settlement implications and model selection probabilities remain leg-specific.

`matchStatus` is `matched`, `price_changed`, `quote_unavailable`, `ambiguous_match`, `event_identity_conflict`, `provider_unavailable` or `expired_during_report`. Duplicate matching provider rows are conservatively ambiguous. Started/stale games are not guessed or replaced with another event. Facts and model references are checked again at completion for expiry.

### Scripts and probabilities

With no trusted model snapshot, `gameScript.status` is `unavailable`, scenarios are empty, and win probability is null. The existing Python scenario simulator does not supply a researched forecast automatically.

A valid server-owned model snapshot produces `model_supplied`. Scenarios must have unique IDs, cited evidence and probabilities summing to one; a fresh model ID/version and evaluation reference are required. `mostLikelyScenarioId` is set only for a unique largest probability **among those supplied model scenarios**. Ties are not broken arbitrarily. This does not establish that the scenario set is exhaustive or that the operator's model is calibrated. A matching marginal selection estimate may be shown with `probabilityBasis: operator_supplied_model`.

Whole-ticket probability remains null, the offered combined price remains null, alternatives remain empty and `assessment.status` remains `insufficient_data` in this slice. Marginals are never multiplied into an SGP forecast. The next stage needs a supported joint outcome model, actual combined sportsbook offers and an optimizer with a fixed total stake/payout floor. Increased hit rate alone is not positive expected value; this endpoint does not stamp a ticket “smart.”

## Server-owned source adapters

### Odds/event identity

`OddsService` supplies fresh quotes using its existing provider key, five-minute cache and ten-attempt/day guard. Lookups are grouped by sport/market, so multiple legs do not fetch a sport market repeatedly. The report reuses the cache populated by browsing where available. Failures consume reservations as before. Reports never accept a provider URL or provider credential from clients.

### Context and venue

Optional `GAME_CONTEXT_FILE` points to an operator-managed JSON catalog, capped at 256 KiB and 128 event entries. With no configured catalog, event/quote facts still work and context is explicitly unavailable. No unlicensed scraping or public injury/lineup API has been added. Replace/subclass the `lookup(event, now)` adapter when a suitable licensed feed is selected.

Catalog structure:

```json
{
  "schemaVersion": 1,
  "events": {
    "basketball_nba:provider-event-id": {
      "homeTeam": "Exact provider home name",
      "awayTeam": "Exact provider away name",
      "startAt": "2026-11-07T01:00:00+00:00",
      "evidence": [
        {
          "id": "venue-reference",
          "kind": "venue",
          "url": "https://example.test/venue",
          "publisher": "Example operator-supplied source",
          "observedAt": "2026-11-06T20:00:00+00:00",
          "validUntil": "2026-11-07T02:00:00+00:00"
        }
      ],
      "facts": [],
      "venue": {
        "name": "Example venue",
        "latitude": 0,
        "longitude": 0,
        "roof": "indoor",
        "evidenceIds": ["venue-reference"]
      }
    }
  }
}
```

This is a schema example only; do not install it as actual event research. Exact team names and start time must match the provider event. Evidence IDs use 1–100 ASCII letters/digits/underscores/hyphens; the `quote:` namespace is reserved. Evidence needs a public HTTPS URL without embedded credentials, publisher, observed time and valid-until time. `kind` is `context` (maximum age/lifetime six hours), `venue` (30 days) or `model_evaluation` (one year). Future skew is capped at 60 seconds. Up to 24 references and eight cited facts per event are accepted. Invalid/stale references and facts depending on them are omitted. A fact is `{text, evidenceIds}` with up to 280 characters; context still requires operator source/semantic verification.

Venue roof is `indoor`, `outdoor`, `retractable` or `unknown`. Retractable venues also need `roofState: open|closed` and fresh `roofEvidenceIds` of kind `context`; otherwise roof state is unknown. Weather is not fetched for an unknown roof state. The service does not infer roof/venue from city or sport.

An optional entry `forecast` has `modelId`, `modelVersion`, `generatedAt`, `validUntil`, `evaluationEvidenceId`, `scenarios` and optional `selections`. It must be generated within one hour, not expired and valid no later than game start. Provide 2–6 scenarios `{id, summary, probability, evidenceIds}`; selection estimates (up to 16) are `{market, outcome, point, winProbability}` with exactly matching structured identity. An evaluation reference of kind `model_evaluation` is mandatory. All probabilities are finite numeric values in [0,1]. Tests contain clearly synthetic examples; no real model or evaluation data is distributed.

### Weather

`OpenMeteoWeather` uses a fixed provider host and verified server-owned coordinates. Default `REPORT_WEATHER_MODE=disabled` performs no weather network calls. `evaluation` selects the free endpoint **only where use qualifies under its noncommercial terms**. `commercial` selects the customer endpoint and requires server-only `OPEN_METEO_API_KEY`. No paid plan is activated by this code. Commercial product/research usage requires an appropriate provider agreement, not merely setting the evaluation flag.

Weather uses the forecast hour containing kickoff UTC, with explicit °F, mph and percent units; it is a forecast, not an observation. Missing kickoff hours, wrong units, provider failures and games outside the six-day supported window return unavailable. Known indoor or confirmed closed-roof games return `not_applicable` without fetching. Unknown venue/roof returns unavailable. Relevant outdoor weather is researched once per event/request and cached for five minutes across reports (32-entry LRU). There is no automatic weather-to-win-probability adjustment.

## Errors, limits and deployment boundary

Authentication is checked before reading POST bodies. Errors never expose provider exceptions, credential-bearing URLs or local catalog paths.

| HTTP | Meaning |
| --- | --- |
| 400 | Invalid structured request/JSON or missing length |
| 401 | Missing/incorrect preview access |
| 405 | Method other than POST (`Allow: POST`) |
| 413 | Empty/over-32-KiB body |
| 415 | Content type other than JSON |
| 429 | Another report is active, or 20 requests/minute/process exceeded (`Retry-After: 5`) |
| 503 | Unexpected internal failure or serialized response above 256 KiB |

Partially unavailable sources normally yield 200 with explicit per-leg/source states. One report runs per process. There is a 20-second work budget; no new source work starts after expiry and late odds/weather results are discarded. Built-in HTTP adapters cap bytes and check elapsed time between reads with socket waits capped at five seconds; an in-progress socket read can overrun the work budget by up to five seconds. Trusted injected adapters must honor their timeout contract. The WSGI host must also enforce connection/body-read timeouts; an application-level content-length cap does not prevent slow clients by itself.

Built-in provider HTTP reads reject redirects, including same-host redirects, to keep credential-bearing requests on the configured endpoints and prevent redirect chains from expanding the work budget.

Preview access is extractable from an APK and is not individual production authentication. Rate/cache/quota state is in memory, lost on restart and not shared across workers. Keep the documented single-worker beta setup; durable shared controls and per-user authentication remain required for broader distribution.

No route is deployed until the PR is merged and the operator deploys it. This PR changes no mobile files and does not start a build. Live endpoint/provider integration is not claimed by synthetic tests.

## Verification and remaining work

Run `python -m unittest discover -s tests -v`. The backend fixtures cover four reports/two events, exact matching, ambiguous/conflicting identities, prices, missing/stale context/model data, indoor/retractable/outdoor weather, source failures, source/quote expiry, bounded requests/reads, auth and all seven responses. Fixtures never use live provider keys or quota.

Remaining: licensed roster/injury/team data and venue coverage; a researched and independently evaluated forecasting model; a supported joint score/settlement model for same-game legs; actual SGP and alternate offers; optimizer and fixed-capital portfolio comparison; promo rule integration; mobile rendering/sharing; authenticated hosted/device testing; durable production auth/metering.

Primary references checked November 6, 2026: [The Odds API guide](https://the-odds-api.com/liveapi/guides/v4/), [provider terms](https://the-odds-api.com/terms-and-conditions.html), [Open-Meteo API](https://open-meteo.com/en/docs), [Open-Meteo terms](https://open-meteo.com/en/terms).
