# Phone odds service — limited private beta

The app browses active supported sports, upcoming games and pregame moneylines/spreads/totals from DraftKings and FanDuel via The Odds API. Missing or stale quotes are omitted. There is no forecast, wager placement, in-play selection or player-prop integration in this slice. Provider titles are descriptive references, not sponsorship.

Create a free provider account. Store `ODDS_API_KEY` only in the hosting service's secret environment settings. Never put it in GitHub, Expo public variables, app.json or an APK. The user must configure that secret; no key is committed here.

For a Render test service: connect this repository's phone branch, choose Python and the Free instance, use build command `pip install -r server/requirements.txt` and start command `gunicorn server.odds:application --workers 1 --threads 4 --bind 0.0.0.0:$PORT`. Set secret variables `ODDS_API_KEY` and `ODDS_PREVIEW_TOKEN` (choose a random value for preview access). Use the resulting HTTPS URL as `EXPO_PUBLIC_ODDS_API_URL` for the mobile build, and the matching preview-access value as `EXPO_PUBLIC_ODDS_PREVIEW_TOKEN`. The latter is bundled with the test app and is only a casual-access gate, not production user authentication. The provider key remains server-only.

The service serializes requests, caches each sport/market for five minutes, and allows ten paid-quota odds fetch attempts per UTC day per process. This is a testing guard only: counters/cache reset on restart. Free Render instances sleep and lose local state. Provider's free monthly quota remains the ultimate cap. Before production, add durable shared metering/cache, individual user authentication, per-user rate limits and monitoring. Do not expose this as a public standalone raw-data API or sell the feed itself. No cloud service, paid subscription or signing/build has been activated by adding these files.

Only the endpoint URL and private-beta access gate go in the EAS preview environment. On Windows PowerShell from `mobile/`, create the two public build variables (substitute the deployed URL and the same access value used by the server):

```powershell
npx.cmd eas-cli env:set --environment preview --name EXPO_PUBLIC_ODDS_API_URL --value https://YOUR-SERVICE.onrender.com --visibility plaintext
npx.cmd eas-cli env:set --environment preview --name EXPO_PUBLIC_ODDS_PREVIEW_TOKEN --value YOUR-PREVIEW-ACCESS-VALUE --visibility plaintext
npx.cmd eas-cli build --platform android --profile preview
```

Existing variables can also be managed in the EAS environment dashboard. The preview profile explicitly uses the `preview` environment. Local shell variables alone are not the remote build environment. Install the new APK; the previous installed build has no data browser. Record the tested commit/device and verify real quotes with their source before relying on them. Cold starts can take about a minute, so the phone allows a 90-second initial request timeout.

Primary references checked November 6, 2026: [API](https://the-odds-api.com/liveapi/guides/v4/), [provider terms](https://the-odds-api.com/terms-and-conditions.html), [free-plan quota](https://the-odds-api.com/#get-access), [Render limitations](https://render.com/docs/free). Commercial display/derived analytics is allowed under stated conditions; standalone redistribution is restricted. The free tier has 500 credits/month. Refreshing one sport/market typically uses one credit; coverage, freshness and availability are provider dependent. This adapter does not establish commercial store eligibility.
