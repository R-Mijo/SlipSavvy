# Event venue and free kickoff weather

The first weather integration uses NWS hourly forecasts for explicitly reviewed venues. It does not apply a home-team city forecast, trust a schedule's roof string, change a win probability or claim complete NFL weather coverage.

## Current pilot coverage

| Schedule stadium ID and exact name | Independent venue evidence | Behavior |
| --- | --- | --- |
| `SEA00` / Lumen Field | [Washington State Public Stadium Authority](https://stadium.org/lumen-field/stadium-features-facts/) describes its open-air field despite spectator roof cover. Coordinates come from [Wikidata Q612736, revision 2541715106](https://www.wikidata.org/w/index.php?title=Q612736&oldid=2541715106), structured data under [CC0](https://www.wikidata.org/wiki/Wikidata:Licensing). | Request the applicable NWS kickoff hour at the stadium coordinates, if within seven days. |
| `MIN01` / U.S. Bank Stadium | Its official [A–Z guide, Roof](https://www.usbankstadium.com/plan-your-visit/a-z-guide) describes a fixed roof and climate-controlled interior. | Outdoor weather is not applied to play; no city-weather request. |
| `IND00` / Lucas Oil Stadium | The [Colts stadium FAQ](https://www.colts.com/game-day/stadium/) establishes a retractable roof. | Current event roof state remains unknown. No open/closed assumption or city-weather request. |
| Any other venue or conflicting ID/name | Not yet in this reviewed catalog. | Explicitly unavailable. No home-stadium fallback, guessed coordinates or indoor exemption. |

The catalog contains paraphrased venue facts and source links, not copied pages/images or a blanket license claim over stadium websites. Its facts were checked November 7, 2026 and expire after 30 days; expired records stop matching. Coverage must be expanded through source review, not by assuming that a team always plays at home. A source schedule row is event-specific but remains a provider snapshot, not a guarantee of later venue changes.

## Identity and provenance

NFL schedule matching preserves the reported venue ID and name separately from the game identity. `VenueCatalog` requires both to match a single reviewed entry and fresh schedule evidence for the exact event/start. A reported venue alone does not establish roof behavior. Neutral/international games cannot inherit the designated home team's ordinary stadium. SoFi/open-sided or retractable venues outside the catalog remain unknown regardless of a schedule `dome` value.

Additive `events[].venue` contains the matched catalog name/ID, roof type, explicit unknown retractable state, sourced coordinates where needed, review time, expiry and source URLs. Its lifetime cannot exceed the schedule source's validity. Existing fresh operator-supplied context venues retain their existing explicit route; this catalog does not silently replace them. Venue evidence that expires during reporting removes weather, including indoor exclusions.

## NWS contract

[NWS API documentation](https://www.weather.gov/documentation/services-web-API) describes free open data, an identifying User-Agent, `/points` and hourly forecasts. [Reuse/disclaimer](https://www.weather.gov/disclaimer). No key, subscription, phone location permission or additional customer setup is required. NWS coverage/outages/rate limits are not guaranteed.

Default server mode is now `REPORT_WEATHER_MODE=nws`. Explicit `disabled` prevents weather requests. Existing explicitly selected Open-Meteo evaluation/commercial modes retain their prior behavior and terms; no paid plan is activated. NWS makes at most a point lookup plus an hourly lookup for a cache miss, within the existing report deadline. Its exact HTTPS host/path is validated, redirects/userinfo/query/fragment/alternate ports rejected, reads capped at 512 KiB and socket waits bounded. A User-Agent identifies SlipSavvy without sending provider credentials. Forecasts share the existing five-minute event cache and are rechecked for expiry.

Match one actual hourly period containing the event's UTC kickoff, including timezone offsets/DST. Missing/overlapping hours, wrong point coordinates, malformed data, provider failure, started games and forecasts older than six hours remain unavailable. Six hours is an application acceptance bound, not a provider freshness promise. Retain NWS `updateTime` separately from retrieval time; the current-hour selection is not a nearest-hour guess.

NWS `values` use explicit `temperatureF`, `precipitationChance`, `windSpeedMph` and `windGustMph` fields with units. Supported Celsius/quantitative units convert explicitly. A wind range is preserved in `windRangeMph`; it is not replaced with an invented midpoint. Missing precipitation/gusts remain null with `missingFields`, never zero. Standard hourly data often omits gusts. Output is labeled partial as appropriate, with provider update/retrieval/validity, source URL and exact hour. This is an approximately 2.5 km grid forecast, not a stadium instrument observation or an automatic adjustment to betting probability.

The phone validates the event venue/source/expiry and forecast hour/units/ranges/missing values, displays source times and roof uncertainty, and expires reports when evidence expires. Older responses and the existing Open-Meteo schema remain supported.

### Installed-client compatibility

NWS ranges and null fields do not fit the old v1 Open-Meteo-only weather reader. A request without a capability header receives `weatherSchema: legacy-v1`: NWS available weather is withheld as `unavailable / client_update_required_for_nws_weather` in both shared events and leg reports, leaving the rest of the report readable. It is not converted to fabricated numeric fields. The new phone sends `X-SlipSavvy-Weather-Schema: nws-v1` to request complete NWS weather; a new phone can still read older backend responses. Unsupported explicit capabilities fail before research starts. Projection creates response objects without modifying the shared source cache. Regression tests include the frozen report reader from main `a25b4c9` and both actual Python wire formats. Backend deployment still does not update an installed APK.

Automated verification uses synthetic provider files/forecasts and Python-produced mobile fixtures. A separate public-source smoke check exercised the actual free schedule → Lumen Field catalog → NWS hourly path. It did not query sportsbook prices, validate a model, deploy the service, create an APK or prove physical-device execution. Broader verified venue coverage, current retractable-roof evidence, performance/usage data, evaluated probabilities and actual-priced settlement comparisons remain unfinished.
