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
