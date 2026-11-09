"""Synthetic offers only; never call a live odds provider or consume credits."""
from copy import deepcopy
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from server.odds import OddsService, application, normalize_props, pair_opposing_quotes
from server.game_reports import ReportService, parse_request
from server.report_sources import ContextCatalog, iso

NOW = 1794078000
SPORT = 'americanfootball_nfl'


def event(identity='game-a'):
    return {'id': identity, 'sport_key': SPORT, 'commence_time': iso(NOW+7200),
            'home_team': 'Synthetic Home', 'away_team': 'Synthetic Away', 'bookmakers': [{
                'key': 'fanduel', 'title': 'FanDuel', 'last_update': iso(NOW-30), 'markets': [
                    {'key': market, 'last_update': iso(NOW-10), 'outcomes': [
                        {'description': player, 'name': side, 'point': point, 'price': price}
                        for player in ('Synthetic Player A', 'Synthetic Player B')
                        for side, price in (('Over', -110), ('Under', -105))]}
                    for market, point in [('player_pass_yds', 220.5), ('player_rush_yds', 50),
                                          ('player_pass_yds_alternate', 200.5), ('player_rush_yds_alternate', 40.5)]] + [
                    {'key': 'spreads', 'outcomes': [{'name': 'Synthetic Home', 'point': -3.5, 'price': -110}]},
                    {'key': 'totals', 'outcomes': [{'name': 'Over', 'point': 42.5, 'price': -110}]}]}]}


def request():
    return {'totalStake': '30', 'legs': [
        {'id': f'leg-{i+1}', 'eventId': 'game-a', 'sport': SPORT, 'bookmaker': 'fanduel',
         'market': market, 'outcome': outcome, 'point': point, 'americanOdds': '-110',
         **({'playerName': 'Synthetic Player A'} if market.startswith('player_') else {})}
        for i, (market, outcome, point) in enumerate([
            ('spreads', 'Synthetic Home', -3.5), ('totals', 'Over', 42.5),
            ('player_pass_yds', 'Over', 220.5), ('player_rush_yds', 'Over', 50)])]}


def fixture():
    odds = OddsService('synthetic-only', fetch=lambda route, params: event() if '/events/' in route else [event()], clock=lambda: NOW)
    result = ReportService(odds, context=ContextCatalog(''), clock=lambda: NOW, research=False).build(request())
    # Keep the original v1 fixture usable by clients predating the additive research field.
    for item in result['events']:
        item.pop('research',None);item.pop('venue',None)
    return result


class PlayerPropsTests(unittest.TestCase):
    def service(self, limit=10):
        self.calls = []
        def fetch(route, params):
            self.calls.append((route, params))
            return event() if '/events/' in route else [event()]
        return OddsService('synthetic-only', fetch=fetch, clock=lambda: NOW, daily_limit=limit)

    def test_normalized_identity_keeps_players_points_original_keys_and_settlement_unknowns(self):
        q = normalize_props(event(), SPORT, 'game-a', NOW)
        self.assertEqual(len(q), 8)
        self.assertEqual(len({x['id'] for x in q}), 8)
        a, b = q[0], q[2]
        self.assertNotEqual(a['playerName'], b['playerName'])
        self.assertEqual(a['point'], b['point'])
        self.assertEqual(a['outcome'], b['outcome'])
        self.assertEqual(a['playerIdentityBasis'], 'provider_description')
        self.assertEqual(a['updatedAt'], iso(NOW-10))
        self.assertEqual(a['fetchedAt'], iso(NOW))
        self.assertEqual(a['opposingAmericanOdds'], '-105')
        self.assertEqual(q[-1]['settlement'], {'status': 'rules_required', 'thresholdSemantics': 'over_under_integer', 'pushPossible': True,
                                              'nonParticipation': 'unknown', 'overtime': 'unknown'})
        alt = normalize_props(event(), SPORT, 'game-a', NOW, ['player_rush_yds_alternate'])
        self.assertTrue(all(x['market'] == 'player_rush_yds_alternate' for x in alt))

    def test_pairing_never_uses_another_player_threshold_book_or_timestamp(self):
        q = normalize_props(event(), SPORT, 'game-a', NOW)
        a, under = q[:2]
        for changed in [dict(under, playerName='Another Player'), dict(under, point=221.5),
                        dict(under, bookmakerKey='draftkings'), dict(under, updatedAt=iso(NOW-20))]:
            self.assertIsNone(pair_opposing_quotes([a, changed])[0]['opposingAmericanOdds'])
        self.assertIsNone(pair_opposing_quotes([a, a, under])[0]['opposingAmericanOdds'])
        self.assertIsNone(pair_opposing_quotes([a, under, under])[0]['opposingAmericanOdds'])

    def test_bad_or_duplicate_subjects_and_rows_are_not_repaired_or_selected(self):
        for player in (None, '', ' ', ' Ambiguous ', ['invalid'], 'A\nB', 'X'*121):
            data = event(); data['bookmakers'][0]['markets'][0]['outcomes'][0]['description'] = player
            q = normalize_props(data, SPORT, 'game-a', NOW, ['player_pass_yds'])
            self.assertEqual(len(q), 3, repr(player))
        data = event(); outcomes = data['bookmakers'][0]['markets'][0]['outcomes']; outcomes.append(deepcopy(outcomes[0]))
        self.assertEqual(len(normalize_props(data, SPORT, 'game-a', NOW, ['player_pass_yds'])), 3)
        data = event(); data['bookmakers'].append(deepcopy(data['bookmakers'][0]))
        self.assertEqual(normalize_props(data, SPORT, 'game-a', NOW), [])

    def test_invalid_stale_and_started_events_fail_closed(self):
        for key, value in [('id', 'wrong'), ('sport_key', 'basketball_nba'), ('home_team', 'Synthetic Away')]:
            data = event(); data[key] = value
            with self.assertRaises(ValueError): normalize_props(data, SPORT, 'game-a', NOW)
        for value in (iso(NOW-901), iso(NOW+61)):
            data = event()
            for market in data['bookmakers'][0]['markets']: market['last_update'] = value
            self.assertEqual(normalize_props(data, SPORT, 'game-a', NOW), [])
        data = event(); data['commence_time'] = iso(NOW)
        self.assertEqual(normalize_props(data, SPORT, 'game-a', NOW), [])

    def test_market_allowlist_validation_precedes_io(self):
        odds = self.service()
        for sport, eid, markets in [('basketball_nba', 'game-a', ['player_pass_yds']),
                (SPORT, '../secret', ['player_pass_yds']), (SPORT, 'game-a', ['alternate_player_rush_yds']),
                (SPORT, 'game-a', ['player_pass_yds']*2), (SPORT, 'game-a', []),
                (SPORT, 'game-a', ['player_pass_yds','player_rush_yds','player_rush_yds_alternate'])]:
            with self.assertRaises(ValueError): odds.get_props(sport, eid, markets)
        self.assertEqual(self.calls, [])
        self.assertEqual(odds.credits, 0)

    def test_response_bounds_and_partial_one_sided_alternates_stay_explicit(self):
        data = event(); market = data['bookmakers'][0]['markets'][0]
        market['outcomes'] *= 33  # 132 outcomes: reject this whole oversized market.
        q = normalize_props(data, SPORT, 'game-a', NOW)
        self.assertEqual({x['market'] for x in q}, {'player_rush_yds'})
        data = event(); market = data['bookmakers'][0]['markets'][2]
        market['outcomes'] = market['outcomes'][:1]
        q = normalize_props(data, SPORT, 'game-a', NOW, ['player_pass_yds_alternate'])
        self.assertEqual(len(q), 1)
        self.assertIsNone(q[0]['opposingAmericanOdds'])

    def test_cached_props_recheck_start_and_conflicting_main_identity(self):
        odds = self.service(); odds.get_props(SPORT, 'game-a')
        odds.clock = lambda: NOW+7200
        self.assertEqual(odds.get_props(SPORT, 'game-a')['quotes'], [])
        odds = self.service(); odds.get(SPORT, 'spreads')
        def conflicting(*args):
            data = event(); data['home_team'] = 'Changed Home'
            return data
        odds.fetch = conflicting
        with self.assertRaisesRegex(RuntimeError, 'Conflicting'): odds.get_props(SPORT,'game-a')

    def test_mobile_contract_fixture_is_actual_python_output(self):
        path = Path(__file__).parents[1]/'mobile/tests/fixtures/player-props-v1.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf8')), fixture())

    def test_shared_cache_subset_reuse_and_weighted_reservations(self):
        odds = self.service(limit=5)
        odds.get(SPORT, 'spreads')
        odds.get_alternates(SPORT, 'game-a')
        q = odds.get_props(SPORT, 'game-a')
        self.assertEqual(odds.credits, 5)
        subset = odds.get_props(SPORT, 'game-a', ['player_pass_yds'])
        self.assertEqual(len(subset['quotes']), 4)
        self.assertEqual(subset['markets'], ['player_pass_yds'])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.calls[-1][1]['markets'], 'player_pass_yds,player_rush_yds')
        self.assertIsNone(q['comparison']['estimatedWinProbability'])
        with self.assertRaises(RuntimeError): odds.get_props(SPORT, 'game-b')
        self.assertEqual(len(self.calls), 3)

    def test_failure_reserves_credits_and_concurrent_routes_share_the_same_limit(self):
        odds = self.service(limit=1)
        def fail(*args): raise RuntimeError('synthetic failure')
        odds.fetch = fail
        with self.assertRaises(RuntimeError): odds.get_props(SPORT, 'game-a', ['player_pass_yds'])
        self.assertEqual(odds.credits, 1)
        odds = self.service(limit=3)
        errors = []
        def invoke(fn):
            try: fn()
            except RuntimeError as e: errors.append(e)
        jobs = [lambda: odds.get_props(SPORT,'game-a'), lambda: odds.get_alternates(SPORT,'game-a'),
                lambda: odds.get(SPORT,'spreads')]
        threads = [threading.Thread(target=invoke,args=(fn,)) for fn in jobs]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(odds.credits, 3)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(errors), 1)

    def test_report_mixes_four_markets_in_one_event_research_without_a_fake_forecast(self):
        odds = self.service(); service = ReportService(odds, context=ContextCatalog(''), clock=lambda: NOW, research=False)
        result = service.build(request())
        self.assertEqual([l['matchStatus'] for l in result['legs']], ['matched']*4)
        self.assertEqual(len(result['events']), 1)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(odds.credits, 4)
        for leg in result['legs']:
            self.assertIsNone(leg['modelWinProbability'])
            self.assertEqual(len(leg['seven']), 7)
        self.assertIn('participation', result['legs'][-1]['legImplication'].lower())
        self.assertEqual(result['assessment']['alternatives'], [])
        self.assertIsNone(result['assessment']['offeredParlayDecimalPrice'])

    def test_report_rejects_missing_player_wrong_sport_and_duplicate_identity(self):
        data = request(); del data['legs'][-1]['playerName']
        with self.assertRaises(ValueError): parse_request(data)
        data = request(); data['legs'][-1]['sport'] = 'basketball_nba'
        with self.assertRaises(ValueError): parse_request(data)
        data = request(); data['legs'].append(dict(data['legs'][-1], id='duplicate'))
        with self.assertRaises(ValueError): parse_request(data)
        data = request(); data['legs'].append(dict(data['legs'][-1], id='other-player', playerName='Synthetic Player B'))
        self.assertEqual(len(parse_request(data)['legs']), 5)

    def test_report_will_not_match_another_player_or_changed_price(self):
        data = request(); data['legs'][-1]['playerName'] = 'Not In Feed'
        service = ReportService(self.service(), context=ContextCatalog(''), clock=lambda: NOW, research=False)
        result = service.build(data)
        self.assertEqual(result['legs'][-1]['matchStatus'], 'quote_unavailable')
        data = request(); data['legs'][-1]['americanOdds'] = '100'
        result = service.build(data)
        self.assertEqual(result['legs'][-1]['matchStatus'], 'price_changed')
        self.assertIsNone(result['legs'][-1]['modelWinProbability'])

    def test_endpoint_authentication_and_query_bounds(self):
        odds = self.service()
        def call(query, authorized=True):
            status = []
            env = {'PATH_INFO':'/api/odds/props', 'REQUEST_METHOD':'GET','QUERY_STRING':query,
                   'HTTP_AUTHORIZATION':'Bearer synthetic-gate' if authorized else ''}
            body = b''.join(application(env,lambda s,h:status.append(s)))
            return status[0], json.loads(body)
        with patch.dict(os.environ, {'ODDS_PREVIEW_TOKEN':'synthetic-gate'}), patch('server.odds.service', odds):
            query = f'sport={SPORT}&eventId=game-a'
            self.assertEqual(call(query, False)[0], '401 Unauthorized')
            self.assertEqual(self.calls, [])
            for extra in ('&eventId=game-b', '&sport='+SPORT, '&unknown=1', '&market=bad'):
                self.assertEqual(call(query+extra)[0], '400 Bad Request')
            self.assertEqual(self.calls, [])
            status, result = call(query)
            self.assertEqual(status, '200 OK')
            self.assertEqual(len(result['quotes']), 8)
            self.assertNotIn('synthetic-only', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
