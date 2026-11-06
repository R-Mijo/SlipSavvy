# Sport, game and sportsbook line browser

The private-beta phone app adds sport → upcoming game → sportsbook line → review → confirm. The Python service keeps The Odds API key outside the phone and supplies curated pregame moneyline, spread and total quotes. Initial sports: active NFL, NCAA football, NBA, NCAA basketball, NHL and MLB. Initial bookmakers: DraftKings and FanDuel. Coverage depends on the feed.

Quotes retain provider event ID, market, sportsbook, actual point/price, provider update time and retrieval time. Stale/started events and invalid prices are omitted; the app rechecks a quote when chosen, reviewed, confirmed and calculated. Same provider event IDs stay together for same-game exclusions; mixed feed/manual selections also compare normalized event names after removing a known provider-ID suffix. This fallback cannot resolve arbitrary manual aliases or establish independence. Quote-detail edits become unverified manual entries with no hidden feed quote; editing only the user's optional win assumption preserves feed provenance and freshness checks. There is no inferred forecast, no native simulation integration, no player props or automatic wager placement.

## Verification

All 49 Python tests and 28 mobile unit tests passed locally after independently reproducing and fixing Gemini Argon's four native-odds findings. The exported-web interaction scripts cover seven scenarios: the existing manual flow plus six odds-browser scenarios, including re-editing a changed price, keeping a user's assumption separate from feed provenance, review/confirmation/calculation freshness checks, game retention across market/refresh changes, hiding expired lines and editing at eight-selection capacity. TypeScript and iOS/Android/web exports passed. See [independent review](COLLABORATION.md). This is not a physical-phone test of this new revision.

One successful real provider check returned five active supported sports and 36 fresh NBA pregame quotes using one odds fetch. The preceding connectivity checks failed before the successful run; their provider sports-list calls do not consume odds credits. No fabricated live quotes or fallback fixtures are served by the deployed adapter. Tests use clearly synthetic inputs. The key was used only for a private local check and is absent from these source files.

## Activation still required

Deploy the service and set its secret `ODDS_API_KEY` and a private-beta `ODDS_PREVIEW_TOKEN`. Configure the app's EAS preview environment with `EXPO_PUBLIC_ODDS_API_URL` and the matching public preview-access value. This preview gate is extractable from an APK and is not individual authentication. Never put the provider key in an Expo public variable. See [server setup](../server/README.md). Rebuild/install the APK after configuration; the user's previous working APK has no odds browser.

The process caches sport/market requests for five minutes and caps odds fetch attempts at ten per UTC day per process. Free Render restarts lose that state, so the cap is not durable. Before broader distribution add durable shared quotas/cache, user authentication, monitoring and load controls. The upstream free plan's monthly credit cap is still relevant. Free Render is a testing host with cold starts, not a production recommendation. No hosted service, new signed build, subscription or paid provider plan was activated by this implementation.

## Gemini Argon review targets

Review the exact PR head recorded in GitHub. Inspect `server/odds.py`, `mobile/src/odds.ts`, `mobile/src/BrowseOdds.tsx`, `mobile/App.tsx`, the tests and `server/README.md`. Reproduce concrete findings; give file/line, input, expected and observed behavior. Check secret isolation, timestamp freshness, actual handicap/total preservation, stale asynchronous responses, review/confirmation, edited provenance, same-event exclusions, nullable/unknown win chance, cache/quota limits and error handling. Do not use the API key or activate external services for this review. Native device and hosted end-to-end verification remain pending.
