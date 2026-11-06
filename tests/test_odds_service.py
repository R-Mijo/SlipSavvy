from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import patch
from server.odds import OddsService, normalize, application

NOW=datetime(2026,11,6,20,tzinfo=timezone.utc).timestamp()
def events(market='h2h'):
    return [{'id':'game-a','sport_key':'basketball_nba','commence_time':'2026-11-07T01:00:00Z',
        'home_team':'Synthetic Home','away_team':'Synthetic Away','bookmakers':[{
            'key':'fanduel','title':'FanDuel','last_update':'2026-11-06T19:59:00Z',
            'markets':[{'key':market,'outcomes':[{'name':'Synthetic Home','price':-110,'point':-3.5}]}]}]}]

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
