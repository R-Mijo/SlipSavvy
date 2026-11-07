from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import threading
import unittest
from unittest.mock import patch
from server.odds import (
    ALTERNATE_LOOKUP_CREDITS,
    MAIN_LOOKUP_CREDITS,
    OddsService,
    application,
    normalize,
    normalize_alternates,
    pair_opposing_quotes,
)

NOW=datetime(2026,11,6,20,tzinfo=timezone.utc).timestamp()
def events(market='h2h'):
    return [{'id':'game-a','sport_key':'basketball_nba','commence_time':'2026-11-07T01:00:00Z',
        'home_team':'Synthetic Home','away_team':'Synthetic Away','bookmakers':[{
            'key':'fanduel','title':'FanDuel','last_update':'2026-11-06T19:59:00Z',
            'markets':[{'key':market,'outcomes':[{'name':'Synthetic Home','price':-110,'point':-3.5}]}]}]}]


def alternate_event(event_id='game-a', sport='basketball_nba'):
    return {
        'id': event_id,
        'sport_key': sport,
        'commence_time': '2026-11-07T01:00:00Z',
        'home_team': 'Synthetic Home',
        'away_team': 'Synthetic Away',
        'bookmakers': [
            {
                'key': 'fanduel',
                'title': 'FanDuel',
                'last_update': '2026-11-06T19:59:00Z',
                'markets': [
                    {
                        'key': 'alternate_spreads',
                        'last_update': '2026-11-06T19:59:10Z',
                        'outcomes': [
                            {'name': 'Synthetic Home', 'price': -160, 'point': -3.5},
                            {'name': 'Synthetic Away', 'price': 130, 'point': 3.5},
                            {'name': 'Synthetic Home', 'price': 145, 'point': -8.0},
                        ],
                    },
                    {
                        'key': 'alternate_totals',
                        'last_update': '2026-11-06T19:59:20Z',
                        'outcomes': [
                            {'name': 'Over', 'price': -140, 'point': 224.5},
                            {'name': 'Under', 'price': 114, 'point': 224.5},
                            {'name': 'Over', 'price': 155, 'point': 235.0},
                        ],
                    },
                ],
            },
            {
                'key': 'draftkings',
                'title': 'DraftKings',
                'last_update': '2026-11-06T19:59:05Z',
                'markets': [
                    {
                        'key': 'alternate_spreads',
                        'last_update': '2026-11-06T19:59:15Z',
                        'outcomes': [
                            {'name': 'Synthetic Away', 'price': -175, 'point': 8.0},
                        ],
                    },
                ],
            },
        ],
    }


class OddsTests(unittest.TestCase):
    def test_normalizes_real_contract_and_preserves_book_and_timestamp(self):
        q=normalize(events(),'basketball_nba','h2h',NOW)[0]
        self.assertEqual(q['americanOdds'],'-110');self.assertEqual(q['bookmaker'],'FanDuel')
        self.assertEqual(q['updatedAt'],'2026-11-06T19:59:00Z')
        self.assertNotIn('probability',q)
    def test_spreads_and_totals_keep_the_actual_line(self):
        self.assertEqual(normalize(events('spreads'),'basketball_nba','spreads',NOW)[0]['label'],'Synthetic Home -3.5')
        d=events('totals');d[0]['bookmakers'][0]['markets'][0]['outcomes'][0].update(name='Over',point=48.5)
        self.assertEqual(normalize(d,'basketball_nba','totals',NOW)[0]['label'],'Over 48.5')
    def test_stale_started_missing_timestamp_and_invalid_odds_omitted(self):
        for change in ('stale','started','timestamp','odds'):
            d=events()
            if change=='stale':d[0]['bookmakers'][0]['last_update']='2026-11-06T18:00:00Z'
            if change=='started':d[0]['commence_time']='2026-11-06T19:00:00Z'
            if change=='timestamp':del d[0]['bookmakers'][0]['last_update']
            if change=='odds':d[0]['bookmakers'][0]['markets'][0]['outcomes'][0]['price']=True
            self.assertEqual(normalize(d,'basketball_nba','h2h',NOW),[],change)
    def test_cache_budget_and_expired_cache_filter(self):
        calls=[];clock=[NOW]
        service=OddsService('not-a-real-key',fetch=lambda route,params:(calls.append(route) or events()),clock=lambda:clock[0],daily_limit=1)
        service.get('basketball_nba');service.get('basketball_nba')
        self.assertEqual(len(calls),1)
        clock[0]+=301
        with self.assertRaisesRegex(RuntimeError,'allowance'):service.get('basketball_nba')
    def test_query_allowlist_prevents_arbitrary_upstream_requests(self):
        s=OddsService('',fetch=lambda *args:self.fail('must not fetch'))
        for sport,market in [('anything','h2h'),('basketball_nba','anything')]:
            with self.assertRaises(ValueError):s.get(sport,market)
    def test_wsgi_preview_gate_and_generic_error_do_not_leak_key(self):
        statuses=[]
        with patch.dict(os.environ,{'ODDS_PREVIEW_TOKEN':'test-access'}):
            body=b''.join(application({'PATH_INFO':'/api/sports','REQUEST_METHOD':'GET'},lambda status,headers:statuses.append(status)))
            self.assertEqual(statuses[-1],'401 Unauthorized')
            body=b''.join(application({'PATH_INFO':'/api/odds','REQUEST_METHOD':'GET','HTTP_AUTHORIZATION':'Bearer test-access','QUERY_STRING':'sport=invalid'},lambda status,headers:statuses.append(status)))
            self.assertEqual(statuses[-1],'400 Bad Request')
            self.assertNotIn(b'apiKey',body)

    def test_upstream_clock_skew_is_consistent_on_initial_and_cached_reads(self):
        for seconds, count in [(30,1),(60,1),(61,0)]:
            d=events()
            d[0]['bookmakers'][0]['last_update']=datetime.fromtimestamp(NOW+seconds,timezone.utc).isoformat()
            s=OddsService('not-a-real-key',fetch=lambda *args:d,clock=lambda:NOW)
            self.assertEqual(len(s.get('basketball_nba')['quotes']),count,seconds)
            self.assertEqual(len(s.get('basketball_nba')['quotes']),count,seconds)

    def test_zero_totals_are_omitted_and_signed_zero_spreads_are_normalized(self):
        for point in (0,-0.0):
            d=events('totals')
            d[0]['bookmakers'][0]['markets'][0]['outcomes'][0].update(name='Over',point=point)
            self.assertEqual(normalize(d,'basketball_nba','totals',NOW),[])
            d=events('spreads')
            d[0]['bookmakers'][0]['markets'][0]['outcomes'][0]['point']=point
            self.assertEqual(normalize(d,'basketball_nba','spreads',NOW)[0]['label'],'Synthetic Home +0')

    def test_event_limit_applies_after_filtering_started_or_wrong_sport_events(self):
        started=deepcopy(events()[0]);started['commence_time']='2026-11-06T19:00:00Z'
        wrong_sport=deepcopy(events()[0]);wrong_sport['sport_key']='baseball_mlb'
        for excluded in (started,wrong_sport):
            d=[deepcopy(excluded) for _ in range(100)]+events()
            self.assertEqual(len(normalize(d,'basketball_nba','h2h',NOW)),1)
        d=[dict(deepcopy(events()[0]),id=str(i)) for i in range(101)]
        self.assertEqual(len(normalize(d,'basketball_nba','h2h',NOW)),100)

    def test_alternate_normalization_preserves_exact_fields_and_opposing_pairs(self):
        quotes = normalize_alternates(alternate_event(), 'basketball_nba', 'game-a', NOW)
        self.assertEqual(len(quotes), 7)
        by_id = {q['id']: q for q in quotes}
        home_spread = by_id['game-a:fanduel:alternate_spreads:Synthetic Home -3.5']
        away_spread = by_id['game-a:fanduel:alternate_spreads:Synthetic Away +3.5']
        unpaired_fd = by_id['game-a:fanduel:alternate_spreads:Synthetic Home -8']
        unpaired_dk = by_id['game-a:draftkings:alternate_spreads:Synthetic Away +8']
        over_total = by_id['game-a:fanduel:alternate_totals:Over 224.5']
        under_total = by_id['game-a:fanduel:alternate_totals:Under 224.5']
        unpaired_over = by_id['game-a:fanduel:alternate_totals:Over 235']

        self.assertEqual(home_spread['eventId'], 'game-a')
        self.assertEqual(home_spread['market'], 'alternate_spreads')
        self.assertEqual(home_spread['bookmaker'], 'FanDuel')
        self.assertEqual(home_spread['bookmakerKey'], 'fanduel')
        self.assertEqual(home_spread['outcome'], 'Synthetic Home')
        self.assertEqual(home_spread['point'], -3.5)
        self.assertEqual(home_spread['americanOdds'], '-160')
        self.assertEqual(home_spread['startAt'], '2026-11-07T01:00:00Z')
        self.assertEqual(home_spread['updatedAt'], '2026-11-06T19:59:10Z')
        self.assertEqual(home_spread['opposingAmericanOdds'], '130')
        self.assertEqual(away_spread['opposingAmericanOdds'], '-160')
        self.assertFalse(home_spread['pushPossible'])

        # Do not pair opposing outcomes across different books or unrelated alternate points.
        self.assertIsNone(unpaired_fd['opposingAmericanOdds'])
        self.assertIsNone(unpaired_dk['opposingAmericanOdds'])
        self.assertTrue(unpaired_fd['pushPossible'])

        self.assertEqual(over_total['market'], 'alternate_totals')
        self.assertEqual(over_total['opposingAmericanOdds'], '114')
        self.assertEqual(under_total['opposingAmericanOdds'], '-140')
        self.assertFalse(over_total['pushPossible'])
        self.assertIsNone(unpaired_over['opposingAmericanOdds'])
        self.assertTrue(unpaired_over['pushPossible'])
        for q in quotes:
            self.assertNotIn('probability', q)
            self.assertNotIn('supportedEdge', q)

    def test_duplicate_stale_started_and_conflicting_alternate_rows_rejected(self):
        # Conflicting event ID, sport, or identical home/away teams must fail closed.
        for bad in (
            dict(alternate_event(), id='wrong-id'),
            dict(alternate_event(), sport_key='icehockey_nhl'),
            dict(alternate_event(), away_team='Synthetic Home'),
            [alternate_event(), alternate_event('game-b')],
        ):
            with self.assertRaises(ValueError):
                normalize_alternates(bad, 'basketball_nba', 'game-a', NOW)

        # Started games return no active quotes.
        started = alternate_event()
        started['commence_time'] = '2026-11-06T19:59:00Z'
        self.assertEqual(normalize_alternates(started, 'basketball_nba', 'game-a', NOW), [])

        # Duplicate outcome+point rows (same or conflicting price) and unknown teams are omitted.
        dup = alternate_event()
        spread_outcomes = dup['bookmakers'][0]['markets'][0]['outcomes']
        spread_outcomes.append({'name': 'Synthetic Home', 'price': -155, 'point': -3.5})
        spread_outcomes.append({'name': 'Unknown Team', 'price': -110, 'point': -1.5})
        quotes = normalize_alternates(dup, 'basketball_nba', 'game-a', NOW)
        labels = [q['label'] for q in quotes if q['bookmakerKey'] == 'fanduel' and q['market'] == 'alternate_spreads']
        self.assertNotIn('Synthetic Home -3.5', labels)
        self.assertNotIn('Unknown Team -1.5', labels)
        # With Synthetic Home -3.5 omitted as ambiguous, Synthetic Away +3.5 has no opposing pair.
        away_quote = next(q for q in quotes if q['label'] == 'Synthetic Away +3.5')
        self.assertIsNone(away_quote['opposingAmericanOdds'])

        # Duplicate bookmaker blocks or duplicate market blocks are rejected.
        dup_book = alternate_event()
        dup_book['bookmakers'].append(deepcopy(dup_book['bookmakers'][0]))
        self.assertTrue(all(q['bookmakerKey'] != 'fanduel' for q in normalize_alternates(dup_book, 'basketball_nba', 'game-a', NOW)))

    def test_same_game_alternate_cache_reuses_data_and_filters_on_expiry(self):
        calls = []
        clock = [NOW]
        service = OddsService(
            'synthetic-key',
            fetch=lambda route, params: (calls.append((route, params)) or alternate_event()),
            clock=lambda: clock[0],
            daily_limit=10,
        )
        first = service.get_alternates('basketball_nba', 'game-a')
        second = service.get_alternates('basketball_nba', 'game-a')
        batch_same_game = service.get_alternates('basketball_nba', ['game-a', 'game-a'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'sports/basketball_nba/events/game-a/odds')
        self.assertEqual(calls[0][1]['markets'], 'alternate_spreads,alternate_totals')
        self.assertEqual(service.credits, ALTERNATE_LOOKUP_CREDITS)
        self.assertEqual(first['quotes'], second['quotes'])
        self.assertEqual(first['quotes'], batch_same_game['quotes'])
        self.assertEqual(first['comparison']['status'], 'insufficient_data')
        self.assertEqual(first['comparison']['recommendation'], 'no_supported_edge')
        self.assertIn('push_void_settlement_rules', first['comparison']['dependencies'])

        # Advance clock within 5-minute cache TTL but past game start: cached quotes filter to empty.
        clock[0] = datetime(2026, 11, 7, 1, 0, 1, tzinfo=timezone.utc).timestamp()
        service.cache[('alternates', 'basketball_nba', 'game-a')] = (clock[0] - 10, first)
        self.assertEqual(service.get_alternates('basketball_nba', 'game-a')['quotes'], [])
        self.assertEqual(len(calls), 1)

    def test_shared_credit_allowance_weights_normal_and_alternate_including_failures(self):
        calls = []
        def fetch(route, params):
            calls.append(route)
            if 'fail' in route:
                raise RuntimeError('Odds provider returned HTTP 500.')
            return alternate_event() if '/events/' in route else events()

        # Daily limit of 5 credits:
        # 1) Normal lookup (1 credit) -> 1 used
        # 2) Failed alternate lookup (2 credits reserved before failure) -> 3 used
        # 3) Successful alternate lookup (2 credits) -> 5 used
        # 4) Cached alternate lookup (0 credits) -> 5 used
        # 5) Another normal lookup -> blocked by allowance
        service = OddsService('synthetic-key', fetch=fetch, clock=lambda: NOW, daily_limit=5)
        service.get('basketball_nba', 'h2h')
        self.assertEqual(service.credits, MAIN_LOOKUP_CREDITS)
        with self.assertRaisesRegex(RuntimeError, 'HTTP 500'):
            service.get_alternates('basketball_nba', 'game-fail')
        self.assertEqual(service.credits, MAIN_LOOKUP_CREDITS + ALTERNATE_LOOKUP_CREDITS)
        service.get_alternates('basketball_nba', 'game-a')
        self.assertEqual(service.credits, 5)
        service.get_alternates('basketball_nba', 'game-a')
        self.assertEqual(service.credits, 5)
        with self.assertRaisesRegex(RuntimeError, 'allowance'):
            service.get('basketball_nba', 'spreads')

        # When 1 credit remains (9 of 10 used), a 2-credit alternate lookup is rejected without
        # consuming the final credit, and a 1-credit normal lookup can still use the final credit.
        boundary = OddsService('synthetic-key', fetch=fetch, clock=lambda: NOW, daily_limit=10)
        boundary.credits = 9
        boundary.calls = 9
        boundary.day = int(NOW // 86400)
        with self.assertRaisesRegex(RuntimeError, 'allowance'):
            boundary.get_alternates('basketball_nba', 'game-a')
        self.assertEqual(boundary.credits, 9)
        boundary.get('basketball_nba', 'h2h')
        self.assertEqual(boundary.credits, 10)

    def test_concurrent_normal_and_alternate_requests_share_same_budget(self):
        barrier = threading.Barrier(4)
        def fetch(route, params):
            return alternate_event(route.split('/')[-2]) if '/events/' in route else events()
        service = OddsService('synthetic-key', fetch=fetch, clock=lambda: NOW, daily_limit=4)
        outcomes = []
        lock = threading.Lock()

        def worker(kind, arg):
            barrier.wait()
            try:
                if kind == 'main':
                    service.get('basketball_nba', arg)
                else:
                    service.get_alternates('basketball_nba', arg)
                with lock:
                    outcomes.append(('ok', kind))
            except RuntimeError as err:
                with lock:
                    outcomes.append(('err', str(err)))

        threads = [
            threading.Thread(target=worker, args=('alt', 'game-a')),
            threading.Thread(target=worker, args=('alt', 'game-b')),
            threading.Thread(target=worker, args=('main', 'h2h')),
            threading.Thread(target=worker, args=('main', 'spreads')),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        self.assertLessEqual(service.credits, 4)
        self.assertTrue(any(status == 'err' and 'allowance' in msg for status, msg in outcomes))

    def test_cross_cache_event_identity_conflict_is_rejected(self):
        def fetch(route, params):
            if '/events/' in route:
                bad = alternate_event()
                bad['home_team'] = 'Different Home Team'
                return bad
            return events('spreads')
        service = OddsService('synthetic-key', fetch=fetch, clock=lambda: NOW, daily_limit=10)
        service.get('basketball_nba', 'spreads')
        with self.assertRaisesRegex(RuntimeError, 'Conflicting provider event data'):
            service.get_alternates('basketball_nba', 'game-a')

    def test_wsgi_alternate_endpoint_auth_validation_and_secret_safety(self):
        def call(query='', auth='Bearer test-access', method='GET', path='/api/odds/alternates'):
            statuses = []
            env = {'PATH_INFO': path, 'REQUEST_METHOD': method, 'QUERY_STRING': query}
            if auth is not None:
                env['HTTP_AUTHORIZATION'] = auth
            body = b''.join(application(env, lambda status, headers: statuses.append(status)))
            return statuses[-1], json.loads(body)

        fake_service = OddsService(
            'secret-odds-key',
            fetch=lambda route, params: alternate_event(route.split('/')[-2]),
            clock=lambda: NOW,
            daily_limit=10,
        )
        with patch.dict(os.environ, {'ODDS_PREVIEW_TOKEN': 'test-access'}), patch('server.odds.service', fake_service):
            self.assertEqual(call('sport=basketball_nba&eventId=game-a', auth=None)[0], '401 Unauthorized')
            self.assertEqual(call('sport=basketball_nba&eventId=game-a', method='POST')[0], '400 Bad Request')
            for bad_query in (
                'sport=basketball_nba',
                'sport=invalid&eventId=game-a',
                'sport=basketball_nba&eventId=https://evil.test',
                'sport=basketball_nba&eventId=../etc/passwd',
                'sport=basketball_nba&eventId=game-a&extra=1',
                'sport=basketball_nba&market=alternate_spreads',
            ):
                status, payload = call(bad_query)
                self.assertEqual(status, '400 Bad Request', bad_query)
                self.assertNotIn('secret-odds-key', json.dumps(payload))

            # Main /api/odds must reject alternate market keys so alternate quotes are never mixed into main browser slates.
            status, _ = call('sport=basketball_nba&market=alternate_spreads', path='/api/odds')
            self.assertEqual(status, '400 Bad Request')

            status, payload = call('sport=basketball_nba&eventId=game-a&eventId=game-a')
            self.assertEqual(status, '200 OK')
            self.assertEqual(payload['eventId'], 'game-a')
            self.assertEqual(payload['markets'], ['alternate_spreads', 'alternate_totals'])
            self.assertEqual(len(payload['quotes']), 7)
            self.assertEqual(fake_service.credits, 2)
            self.assertNotIn('secret-odds-key', json.dumps(payload))


class AlternateReviewTests(unittest.TestCase):
    def test_late_provider_response_cannot_return_started_quotes(self):
        clock=[NOW]
        def fetch(*args):
            clock[0]=NOW+6*3600
            return alternate_event()
        result=OddsService('synthetic',fetch=fetch,clock=lambda:clock[0]).get_alternates('basketball_nba','game-a')
        self.assertEqual(result['quotes'],[])

    def test_expired_identity_cache_does_not_block_rescheduled_game(self):
        clock=[NOW]
        def fetch(route,params):
            if '/events/' not in route:return events()
            data=alternate_event();data['commence_time']='2026-11-07T02:00:00Z';return data
        service=OddsService('synthetic',fetch=fetch,clock=lambda:clock[0])
        service.get('basketball_nba')
        clock[0]+=301
        self.assertTrue(service.get_alternates('basketball_nba','game-a')['quotes'])

    def test_cached_alternates_recheck_fresh_identity_conflict(self):
        service=OddsService('synthetic',fetch=lambda *args:alternate_event(),clock=lambda:NOW)
        service.get_alternates('basketball_nba','game-a')
        q=normalize(events(),'basketball_nba','h2h',NOW)[0];q['homeTeam']='Conflicting Home'
        service.cache[('basketball_nba','h2h')]=(NOW,{'quotes':[q]})
        with self.assertRaisesRegex(RuntimeError,'Conflicting'):
            service.get_alternates('basketball_nba','game-a')

    def test_response_budget_discards_late_network_result(self):
        ticks=[0]
        def fetch(*args):ticks[0]=21;return alternate_event()
        service=OddsService('synthetic',fetch=fetch,clock=lambda:NOW)
        with patch('server.odds.time.monotonic',side_effect=lambda:ticks[0]):
            with self.assertRaisesRegex(RuntimeError,'budget'):
                service.get_alternates('basketball_nba','game-a',timeout=20)
        self.assertEqual(service.credits,2)

    def test_distinct_close_thresholds_have_distinct_quote_ids(self):
        data=alternate_event();market=data['bookmakers'][0]['markets'][0]
        market['outcomes']=[{'name':'Synthetic Home','price':-110,'point':-3.500001},
                            {'name':'Synthetic Home','price':-110,'point':-3.500002}]
        quotes=normalize_alternates(data,'basketball_nba','game-a',NOW)
        self.assertEqual(len({q['id'] for q in quotes}),len(quotes))

    def test_multi_event_request_deduplicates_and_charges_per_distinct_game(self):
        calls=[]
        def fetch(route,params):
            calls.append(route);return alternate_event(route.split('/')[-2])
        service=OddsService('synthetic',fetch=fetch,clock=lambda:NOW)
        data=service.get_alternates('basketball_nba',['game-a','game-a','game-b'],timeout=20)
        self.assertEqual(data['eventIds'],['game-a','game-b'])
        self.assertEqual(len(calls),2);self.assertEqual(service.credits,4)
