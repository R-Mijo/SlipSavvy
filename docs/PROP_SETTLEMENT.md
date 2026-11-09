# Player-prop threshold evidence

The Odds API's [market catalog](https://the-odds-api.com/sports-odds-data/betting-markets.html) and [NFL guide](https://the-odds-api.com/sports/nfl-odds.html) place milestones and alternate Over/Under offerings under the same alternate keys. These pages establish market coverage, not a universal mapping from every sportsbook label to an exact numeric boundary.

Quotes preserve the supplied player, outcome, point and price. `settlement.status` remains `rules_required`; participation and overtime remain unknown. Numeric classification is:

| thresholdSemantics | pushPossible | Meaning |
| --- | --- | --- |
| over_under_half_point | false | Integer yardage cannot equal the supplied half-point threshold; participation/void rules remain unverified. |
| over_under_integer | true | A main Over/Under line can land exactly on its threshold; this is a possibility, not a confirmed settlement rule. |
| alternate_integer_unverified | null | The original milestone/strict Over/Under boundary is not established, even when another outcome is present. |
| unsupported_threshold | null | Other fractional or invalid thresholds are not interpreted. |

For uncertain thresholds, both nested and top-level push flags are null and `opposingAmericanOdds` is withheld. Merely finding opposite labels does not prove complementary settlement. Reports withhold supplied leg forecasts at these boundaries. The phone explains uncertainty before selection, in the selected ticket and in research; it applies the same protection to older server responses without the new metadata.

This is not a bet-grading engine. Book/jurisdiction/market-specific participation, overtime, promotions, settlement and SGP repricing still require verified rules. Whole-ticket forecasts and comparisons remain unavailable. Synthetic regression fixtures do not establish live sportsbook mappings or profitable recommendations.
