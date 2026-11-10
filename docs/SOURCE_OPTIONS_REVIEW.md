# Data-source review — November 9, 2026

No account, trial, subscription or paid API was activated. Gemini's list is a lead list, not proof of suitability.

- Open-Meteo: hosted free access is non-commercial; the underlying attribution license is distinct from hosted-service terms. Keep the existing NWS adapter for the current US venue pilot. https://open-meteo.com/en/terms and https://open-meteo.com/en/pricing
- WeatherAPI advertises 100,000 free monthly requests and commercial use. Signup is required and onboarding advertises a seven-day higher-plan trial. No account created; free-plan endpoint coverage and ongoing limits must be checked before integration. https://www.weatherapi.com/pricing.aspx and https://www.weatherapi.com/signup.aspx
- MySportsFeeds current-season free access is explicitly non-commercial and requires contacting them for the discount. Not approved for this planned ad-supported product. https://www.mysportsfeeds.com/register
- API-SPORTS advertises 100 requests/day per API. This alone does not establish NFL injury fields, current-season coverage, rights or adequate quota for this app. https://api-sports.io/
- GoalServe advertises trials and paid packages, not a verified permanent zero-cost production source. No trial started. https://www.goalserve.com/en/contact-us
- The Odds API historical snapshots require a paid plan, contrary to the suggested free-history claim. Existing configured current odds access remains unchanged. https://the-odds-api.com/historical-odds-data/
- Sportradar/Stats Perform and OpenWeather historical products were not selected or subscribed to. A free wrapper/scraper does not grant underlying data rights; do not equate a Python library license with permission to commercialize scraped content.

## Verified current NFL statistics lead

The public GitHub release API for nflverse/nflverse-data tag stats_player was checked directly. It lists stats_player_week_2026.csv (4,178,818 bytes), updated 2026-11-09T19:53:56Z, plus 2026 regular-season aggregate files. This verifies asset availability, not schema, completeness, identity matching, rights for every upstream component or production ingestion.

https://github.com/nflverse/nflverse-data/releases/tag/stats_player
https://nflreadr.nflverse.com/reference/load_player_stats.html
https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html

Next integration work requires actual schema/row inspection, GSIS identity and team mapping, completed-game/date cutoff checks to prevent future-data leakage, last-N-game samples, missing-versus-zero distinction, shared bounded caching and attributed file timestamps. It must not infer player participation from a historical stat row. Current conditional education deliberately states these inputs are absent. No evaluated forecasts or predictive scripts are claimed.
