# Game-report backend v1

Implements bounded backend slices of [issue #3](https://github.com/R-Mijo/SlipSavvy/issues/3). The phone uses these structured reports. No deployment, betting, paid subscription, LLM call or trained forecasting model is implied. See the [full product contract](SEVENFOLD_WORKFLOW.md) for the intended workflow and remaining work.

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

Limits: 1–8 unique legs, at most four distinct events and four sport/market combinations. Main-market requests batch by sport/market; props batch by event and main/alternate family. Each prop batch has one or two selected markets, sharing the existing credit/time limits. Repeated selections under different IDs, arbitrary extra fields, URLs, duplicate JSON keys, nonfinite numbers, malformed amounts and unsupported markets are rejected before fetching. Dynamic all-sport discovery remains separate work.

## Offered alternate quotes

`GET /api/odds/alternates?sport=basketball_nba&eventId=provider-id`, with the existing preview Bearer token, requests actually offered `alternate_spreads` and `alternate_totals`. Repeat `eventId` for up to eight selections / four distinct games of one allowlisted sport. Duplicate IDs reuse one event lookup. Only `sport` and `eventId` are accepted. Query length is at most 1,024 characters.

Quotes retain the provider market key, event identity, sportsbook, raw outcome, point, American price and provider/retrieval timestamps. No main-market relabeling. Duplicate book/market/outcome rows are omitted conservatively; conflicting identities, stale/started games and malformed data are rejected or unavailable. Quotes recheck freshness after network work and at completion. Main-market report requests still do not accept alternate-market selections.

One event returns `eventId`, `quotes`, `markets`, `fetchedAt`, `refreshSeconds`, `maxQuoteAgeSeconds`, `provider`, `sport` and `comparison`. Multiple events return `eventIds`, per-event `events` and combined `quotes`. Clients should use IDs rather than infer response shape from selection count. Empty valid results mean no usable offers, not a fabricated replacement line.

`opposingAmericanOdds` is present only for a unique opposing outcome from the same event/book/market/update timestamp and matching threshold (opposite signed spread or identical total). Whole-number points set `pushPossible: true`; no push/void probability is inferred. `comparison` remains `insufficient_data` / `no_supported_edge`, with null win estimate, joint price and supported edge. These are offered candidate prices, not optimized recommendations.

### Budget, cache and errors

Main and alternate lookups share a conservative ten-credit/UTC-day process-local reservation: one credit per normal single-market lookup, two per two-market alternate event lookup. Reservations precede I/O, including failures. Cache hits cost zero new reserved credits. This can over-reserve when fewer markets return. It is not authoritative provider billing or durable monthly accounting; restarts/workers retain the existing limitations.

Event quotes cache for five minutes. Expired alternate cache entries are pruned and total cache growth from event entries is capped at 64 slots alongside normal caches. Fresh conflicting identities block ambiguous results; expired caches cannot permanently block reschedules. Shared locking deduplicates same-game requests. The endpoint supplies a 20-second work/lock budget; readers have at most five-second socket waits, so in-flight reads can overrun by up to five seconds. Injected adapters must honor their timeout contract. Upstream alternates are capped at 1 MiB; serialized responses are capped at 256 KiB. Oversized combined responses return 503, not a truncated ticket.

Authentication runs first (401). Invalid fields/IDs/method return 400; missing route 404; unavailable sources/quota/busy/oversize return sanitized 503. Unknown keys and unsupported markets are rejected before provider work. No provider URL/key is accepted from a client. No route aliases are added.

## NFL player props

`GET /api/odds/props?sport=americanfootball_nfl&eventId=provider-id`, with the existing preview Bearer gate, requests main passing/rushing yards for **one** event. Optional repeated `market` parameters select one or two distinct keys from `player_pass_yds`, `player_rush_yds`, `player_pass_yds_alternate`, `player_rush_yds_alternate`. No other sport, query parameter or provider route is accepted. The phone loads two main or two alternate markets only after the customer presses Load; changing the displayed player/category uses the returned data.

Response shape matches a single-event alternate response. Quotes add `playerName` (the exact provider outcome `description`), `playerIdentityBasis: provider_description` and settlement metadata with unknown participation/overtime terms and an integer-threshold push flag. This is not an established roster/GSIS ID. No fuzzy player matching or inferred player team. Duplicate/invalid names, books, markets and exact player/outcome/point rows are omitted conservatively. Opposing-price pairing includes player, threshold, book, event, market and update time; one-sided alternate offers remain one-sided.

The same four keys are accepted by `POST /api/game-reports` for NFL only. Prop legs require `playerName`, positive numeric `point` and `Over`/`Under`. Non-prop legs cannot contain `playerName`. Exact player identity participates in deduplication, quote matching and the echoed selection. Several players at the same threshold remain distinct. Team/prop selections may share games and research. Prop estimates remain unavailable: no evaluated player forecast or identity mapping is connected. Whole-ticket forecasts, combined prices and alternatives remain null/empty.

Props share the unchanged ten-credit/UTC-day reservation with main/alternate lookups, one credit per requested market before I/O, including failures. Five-minute cache hits/subsets of an existing market batch consume no new credits. Provider response is capped at 1 MiB, 128 outcomes per book/market and 256 normalized quotes per event; malformed/oversized markets are unavailable. Existing fixed host/no redirects, request deadline, final freshness/identity rechecks and 256 KiB HTTP response cap apply. Cache and counters remain process-local. No live provider calls in tests.

## Free NFL research

NFL reports add `events[].research`: partial/unavailable status, exact schedule mapping, per-dataset missing/stale/unknown coverage, selected-player roster/GSIS matching, reported injury/practice fields, a bounded team injury list and attributed source snapshots. All file update, retrieval and metadata-check times remain separate; per-player confirmation is null. No current participation, healthy-player conclusion or probability adjustment is inferred. See [identity, source/cache bounds, deployment defaults and full schema behavior](NFL_RESEARCH.md). Existing curated context/forecasts remain separate. Non-NFL reports do not fetch NFL sources, and older clients may ignore this additive field.

## Event venue and NWS kickoff weather

The updated phone sends `X-SlipSavvy-Weather-Schema: nws-v1`. Omitted header defaults to `legacy-v1`; an older phone receives an explicitly unavailable NWS weather state instead of a new value format its reader would reject. Other report fields, existing Open-Meteo weather and indoor/unavailable states remain readable. `weatherSchema` identifies the selected response capability. Unsupported explicit capability values are rejected before research. See [compatibility details](VENUE_WEATHER.md#installed-client-compatibility).

Additive `events[].venue` matches the reported event stadium ID/name to independently reviewed roof/coordinate facts, with source and validity times. The current pilot covers Lumen Field forecasts, fixed-indoor U.S. Bank Stadium and unknown-retractable Lucas Oil Stadium. Other venues do not inherit a home-city forecast. NWS available forecasts preserve update versus retrieval time, exact kickoff hour, nullable unit-bearing values, wind ranges and missing fields. No probability change. Default free `REPORT_WEATHER_MODE=nws`; explicit disabled and existing Open-Meteo modes are respected. See [coverage, schema and bounds](VENUE_WEATHER.md).

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

`OddsService` supplies fresh quotes using its existing provider key, five-minute cache and ten-credit/day shared reservation (one per main lookup, two per alternate event lookup). Lookups are grouped by sport/market, so multiple legs do not fetch a sport market repeatedly. The report reuses the cache populated by browsing where available. Failures consume reservations as before. Reports never accept a provider URL or provider credential from clients.

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

The default `REPORT_WEATHER_MODE=nws` uses the free NWS adapter and reviewed venue catalog described above. Explicit `REPORT_WEATHER_MODE=disabled` performs no weather network calls. The retained `OpenMeteoWeather` adapter uses a fixed provider host and verified server-owned coordinates: `evaluation` selects the free endpoint **only where use qualifies under its noncommercial terms**; `commercial` selects the customer endpoint and requires server-only `OPEN_METEO_API_KEY`. No paid plan is activated by this code. Commercial Open-Meteo usage requires an appropriate provider agreement, not merely setting the evaluation flag.

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

Odds, NWS and Open-Meteo HTTP reads reject redirects, including same-host redirects. The credential-free nflverse CSV transport permits only its separately validated single public GitHub-CDN redirect. Redirect chains cannot expand the work budget.

Preview access is extractable from an APK and is not individual production authentication. Rate/cache/quota state is in memory, lost on restart and not shared across workers. Keep the documented single-worker beta setup; durable shared controls and per-user authentication remain required for broader distribution.

No route is deployed until an authorized release. Source and mobile changes do not imply a new native build or device execution. Synthetic tests do not establish live sportsbook integration; separately labeled public-source checks do not verify deployment.

## Verification and remaining work

Run `python -m unittest discover -s tests -v`. The backend fixtures cover four reports/two events, exact matching, ambiguous/conflicting identities, prices, missing/stale context/model data, indoor/retractable/outdoor weather, source failures, source/quote expiry, bounded requests/reads, auth and all seven responses. Fixtures never use live provider keys or quota.

Remaining: licensed roster/injury/team data and venue coverage; a researched and independently evaluated forecasting model; a supported joint score/settlement model for same-game legs; actual SGP and alternate offers; optimizer and fixed-capital portfolio comparison; promo rule integration; mobile rendering/sharing; authenticated hosted/device testing; durable production auth/metering.

Primary references checked November 6, 2026: [The Odds API guide](https://the-odds-api.com/liveapi/guides/v4/), [provider terms](https://the-odds-api.com/terms-and-conditions.html), [Open-Meteo API](https://open-meteo.com/en/docs), [Open-Meteo terms](https://open-meteo.com/en/terms).
