"""Boundary evidence must not turn into an invented sportsbook settlement rule."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from server.odds import normalize_props, pair_opposing_quotes, OddsService
from server.game_reports import ReportService
from server.report_sources import ContextCatalog
from server.prop_settlement import prop_settlement
from test_player_props import event, request, NOW, SPORT

ALT = 'player_rush_yds_alternate'


def offers(point=60, paired=True, market=ALT):
    data = event()
    data['bookmakers'][0]['markets'] = [{'key': market, 'outcomes': [
        {'description': 'Synthetic Player A', 'name': side, 'point': point, 'price': -110}
        for side in (['Over', 'Under'] if paired else ['Over'])]}]
    return data


def settlement_fixture():
    odds = OddsService('synthetic-only', fetch=lambda *a: offers(), clock=lambda: NOW)
    service = ReportService(odds, context=ContextCatalog(''), clock=lambda: NOW, research=False)
    leg = dict(request()['legs'][-1], id='leg-1', market=ALT, point=60)
    return service.build({'totalStake': '10', 'legs': [leg]})


class PropSettlementTests(unittest.TestCase):
    def test_alternate_integer_never_implies_milestone_or_push_even_with_opposite_quote(self):
        for paired in (False, True):
            for market in ('player_rush_yds_alternate', 'player_pass_yds_alternate'):
                quotes = normalize_props(offers(paired=paired, market=market), SPORT, 'game-a', NOW, [market])
                self.assertEqual(len(quotes), 2 if paired else 1)
                for q in quotes:
                    self.assertEqual(q['settlement']['thresholdSemantics'], 'alternate_integer_unverified')
                    self.assertIsNone(q['settlement']['pushPossible'])
                    self.assertIsNone(q['pushPossible'])
                    self.assertIsNone(q['opposingAmericanOdds'])
                    self.assertEqual(q['point'], 60)
                    self.assertIn(q['outcome'], ['Over', 'Under'])
                    self.assertEqual(q['americanOdds'], '-110')
                    self.assertEqual(q['settlement']['status'], 'rules_required')

    def test_half_point_numeric_boundary_is_distinct_from_participation_and_void_rules(self):
        # Integer yardage cannot land on 59.5: Over wins at 60+, Under at 59 or less,
        # conditional on the wager having action under independently verified rules.
        for market in ('player_rush_yds', ALT):
            quotes = normalize_props(offers(59.5, market=market), SPORT, 'game-a', NOW, [market])
            for q in quotes:
                self.assertEqual(q['settlement']['thresholdSemantics'], 'over_under_half_point')
                self.assertIs(q['pushPossible'], False)
                self.assertEqual(q['opposingAmericanOdds'], '-110')
                self.assertEqual(q['settlement']['nonParticipation'], 'unknown')
                self.assertEqual(q['settlement']['overtime'], 'unknown')
            for field, value in [('playerName', 'Someone Else'), ('point', 60.5),
                                 ('bookmakerKey', 'draftkings'), ('updatedAt', '2026-11-07T00:00:00Z')]:
                changed = dict(quotes[1], **{field: value})
                self.assertIsNone(pair_opposing_quotes([quotes[0], changed])[0]['opposingAmericanOdds'])

    def test_main_integer_is_only_a_possible_push_and_unsupported_fractions_remain_unknown(self):
        main = normalize_props(offers(market='player_rush_yds'), SPORT, 'game-a', NOW, ['player_rush_yds'])
        self.assertIs(main[0]['pushPossible'], True)
        self.assertEqual(main[0]['settlement']['status'], 'rules_required')
        q = normalize_props(offers(60.25), SPORT, 'game-a', NOW, [ALT])[0]
        self.assertIsNone(q['pushPossible'])
        self.assertIsNone(q['opposingAmericanOdds'])
        for point in (True, None, float('nan'), float('inf'), -1, 1001):
            self.assertEqual(prop_settlement(ALT, point)['thresholdSemantics'], 'unsupported_threshold')

    def test_repairing_old_metadata_is_idempotent_and_does_not_mutate_source_quotes(self):
        q = normalize_props(offers(), SPORT, 'game-a', NOW, [ALT])
        q[0]['pushPossible'] = True
        q[0]['settlement']['pushPossible'] = True
        original = deepcopy(q)
        corrected = pair_opposing_quotes(q)
        self.assertEqual(q, original)
        self.assertIsNone(corrected[0]['settlement']['pushPossible'])
        self.assertEqual(pair_opposing_quotes(corrected), corrected)

    def test_report_withholds_a_supplied_estimate_when_threshold_is_unverified(self):
        result = settlement_fixture()
        leg = result['legs'][0]
        service = ReportService(None, context=ContextCatalog(''), research=False)
        event_report = deepcopy(result['events'][0])
        event_report['gameScript'] = {'status': 'model_supplied', 'selections': [
            dict(leg['selection'], winProbability=.8)]}
        checked = service._leg(leg['selection'], 'matched', leg['quote'], leg['eventRef'], event_report)
        self.assertIsNone(checked['modelWinProbability'])
        self.assertEqual(checked['probabilityBasis'], 'unavailable')
        self.assertIn('At exactly 60 yards', checked['legImplication'])
        self.assertNotIn('Requires Synthetic Player A to record over', checked['legImplication'])
        self.assertEqual(checked['seven'][4]['status'], 'needs_data')
        self.assertIsNone(result['assessment']['offeredParlayDecimalPrice'])
        self.assertEqual(result['assessment']['alternatives'], [])
        path = Path(__file__).parents[1]/'mobile/tests/fixtures/player-settlement-v1.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf8')), result)


if __name__ == '__main__':
    unittest.main()
