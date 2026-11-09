"""Synthetic-only contracts: no provider credentials, network or invented live picks."""
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server, WSGIRequestHandler

from server.game_reports import ReportService, ReportBusy, parse_request
from server.odds import OddsService, application, normalize
from server.report_sources import ContextCatalog, OpenMeteoWeather, iso, read_json_response
from urllib.error import HTTPError

NOW = datetime(2026, 11, 6, 20, tzinfo=timezone.utc).timestamp()
START = iso(NOW + 18000)


def event(identity='game-a'):
    return {'id': identity, 'sport_key': 'basketball_nba', 'commence_time': START,
            'home_team': 'Synthetic Home', 'away_team': 'Synthetic Away', 'bookmakers': [
                {'key': 'fanduel', 'title': 'FanDuel', 'last_update': iso(NOW-30), 'markets': [
                    {'key': 'spreads', 'outcomes': [{'name': 'Synthetic Home', 'price': -110, 'point': -6.5}]},
                    {'key': 'totals', 'outcomes': [{'name': 'Over', 'price': -110, 'point': 229.5}]},
                    {'key': 'h2h', 'outcomes': [{'name': 'Synthetic Home', 'price': -150}]}]}]}


def leg(identity='L1', market='spreads', event_id='game-a'):
    return {'id': identity, 'eventId': event_id, 'sport': 'basketball_nba', 'bookmaker': 'fanduel',
            'market': market, 'outcome': 'Over' if market == 'totals' else 'Synthetic Home',
            'point': 229.5 if market == 'totals' else -6.5 if market == 'spreads' else None}


def request(legs=None):
    return {'totalStake': '10', 'minimumTotalReturn': '90', 'legs': legs if legs is not None else [leg()]}


def evidence(identity, kind='context'):
    return {'id': identity, 'kind': kind, 'url': 'https://example.test/'+identity,
            'publisher': 'Synthetic test source', 'observedAt': iso(NOW-60), 'validUntil': iso(NOW+600)}


def catalog(roof='indoor', model=False):
    entry = {'homeTeam': 'Synthetic Home', 'awayTeam': 'Synthetic Away', 'startAt': START,
             'evidence': [evidence('context'), evidence('venue', 'venue'), evidence('evaluation', 'model_evaluation')],
             'facts': [{'text': 'Synthetic test fact, not a real game assertion.', 'evidenceIds': ['context']}],
             'venue': {'name': 'Synthetic test venue', 'latitude': 0, 'longitude': 0,
                       'roof': roof, 'evidenceIds': ['venue']}}
    if model:
        entry['forecast'] = {'modelId': 'synthetic-test-model', 'modelVersion': 'test-only',
            'generatedAt': iso(NOW-60), 'validUntil': iso(NOW+300), 'evaluationEvidenceId': 'evaluation',
            'scenarios': [{'id': 'fast', 'summary': 'Synthetic higher pace.', 'probability': .6, 'evidenceIds': ['context']},
                          {'id': 'slow', 'summary': 'Synthetic lower pace.', 'probability': .4, 'evidenceIds': ['context']}],
            'selections': [{'market': 'spreads', 'outcome': 'Synthetic Home', 'point': -6.5, 'winProbability': .52}]}
    return {'schemaVersion': 1, 'events': {'basketball_nba:game-a': entry}}


class NoWeather:
    def get(self, *args, **kwargs):
        raise AssertionError('Weather should not be fetched')


class ReportTests(unittest.TestCase):
    def test_six_distinct_games_reach_the_report_and_ninth_leg_is_rejected(self):
        self.odds = OddsService('synthetic-only', fetch=lambda *args: [event('six-'+str(i)) for i in range(6)], clock=lambda: NOW)
        result = self.service().build(request([leg('L'+str(i), event_id='six-'+str(i)) for i in range(6)]))
        self.assertEqual(len(result['events']), 6)
        self.assertTrue(all(l['matchStatus']=='matched' for l in result['legs']))
        with self.assertRaises(ValueError):
            parse_request(request([leg('L'+str(i), event_id='nine-'+str(i)) for i in range(9)]))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'context.json'
        self.calls = []
        def fetch(route, params):
            self.calls.append((route, params))
            return [event(), event('game-b')]
        self.odds = OddsService('synthetic-only', fetch=fetch, clock=lambda: NOW)

    def service(self, data=None, weather=None, clock=lambda: NOW):
        if data is None:
            context = ContextCatalog('')
        else:
            self.path.write_text(json.dumps(data), encoding='utf8')
            context = ContextCatalog(str(self.path))
        return ReportService(self.odds, context=context, weather=weather or NoWeather(), clock=clock)

    def test_exact_matching_metadata_prices_and_seven_concise_responses(self):
        result = self.service().build(request())
        report = result['legs'][0]
        self.assertEqual(report['matchStatus'], 'matched')
        self.assertEqual(report['quote']['point'], -6.5)
        self.assertEqual(report['quote']['outcome'], 'Synthetic Home')
        self.assertEqual(report['price']['decimalFraction'], {'numerator': 21, 'denominator': 11})
        self.assertAlmostEqual(report['price']['breakEvenPercent'], 52.38095238)
        self.assertEqual([s['name'] for s in report['seven']], ['Jeeves','Luna','Pax','Winston','Lisa','Diego','Gus'])
        self.assertTrue(all(len(s['bullets']) == 1 for s in report['seven']))
        self.assertIsNone(report['modelWinProbability'])
        self.assertEqual(result['assessment']['status'], 'insufficient_data')
        self.assertEqual(result['assessment']['comparisonContext'], {
            'totalStake': '10.00', 'minimumTotalReturn': '90.00', 'stakeBasis': 'fixed_total_capital'})
        self.assertEqual(result['events'][0]['startAtPhoenix'], '2026-11-06T18:00:00-07:00')

    def test_same_game_research_once_with_leg_specific_implications(self):
        service = self.service(catalog(model=True))
        original = service.context.lookup
        lookups = []
        service.context.lookup = lambda *args: (lookups.append(args[0]['eventId']) or original(*args))
        result = service.build(request([leg(), leg('L2','totals')]))
        self.assertEqual(lookups, ['game-a'])
        self.assertEqual(len(result['events']), 1)
        a, b = result['legs']
        self.assertEqual(a['gameScript'], b['gameScript'])
        self.assertEqual(a['gameScript']['mostLikelyScenarioId'], 'fast')
        self.assertNotEqual(a['legImplication'], b['legImplication'])
        self.assertEqual(a['modelWinProbability'], .52)
        self.assertIsNone(b['modelWinProbability'])
        self.assertIsNone(result['assessment']['estimatedWinProbability'])
        self.assertEqual(len(self.calls), 2)

    def test_four_legs_produce_four_reports_and_two_research_objects(self):
        legs = [leg(), leg('L2','totals'), leg('L3',event_id='game-b'), leg('L4','totals','game-b')]
        result = self.service().build(request(legs))
        self.assertEqual(len(result['legs']), 4)
        self.assertEqual(len(result['events']), 2)
        self.assertTrue(all(len(r['seven']) == 7 for r in result['legs']))
        self.assertEqual(len(self.calls), 2)

    def test_unmatched_first_leg_can_reference_research_verified_by_another_leg(self):
        legs=[dict(leg(),point=-5.5),leg('L2','totals')]
        result=self.service(catalog(model=True)).build(request(legs))
        a,b=result['legs']
        self.assertEqual(a['matchStatus'],'quote_unavailable')
        self.assertEqual(a['eventRef'],b['eventRef'])
        self.assertEqual(a['gameScript'],b['gameScript'])
        self.assertIsNone(a['modelWinProbability'])
        self.assertIsNone(a['price'])

    def test_ambiguous_changed_unmatched_or_old_quotes_are_not_guessed(self):
        original = normalize([event()], 'basketball_nba', 'spreads', NOW)[0]
        class Quotes:
            def __init__(self, values): self.values = values
            def get(self, *args, **kwargs): return {'quotes': self.values}
        old = dict(original, updatedAt=iso(NOW-901))
        for quotes, expected in [([original, dict(original, americanOdds='100')], 'ambiguous_match'),
                                 ([old], 'quote_unavailable'), ([], 'quote_unavailable')]:
            s = ReportService(Quotes(quotes), context=ContextCatalog(''), clock=lambda: NOW)
            self.assertEqual(s.build(request())['legs'][0]['matchStatus'], expected)
        data = request(); data['legs'][0]['americanOdds'] = '+100'
        report = self.service().build(data)['legs'][0]
        self.assertEqual(report['matchStatus'], 'price_changed')
        self.assertEqual(report['price']['americanOdds'], '-110')
        self.assertEqual(report['seven'][-1]['status'], 'blocked')

    def test_same_provider_event_with_conflicting_identity_is_blocked(self):
        quotes = []
        for market in ('spreads','totals'):
            q = normalize([event()], 'basketball_nba', market, NOW)[0]
            if market == 'totals': q['homeTeam'] = 'Different team'
            quotes.append(q)
        class Quotes:
            def get(self, sport, market, **kwargs): return {'quotes': [q for q in quotes if q['market'] == market]}
        result = ReportService(Quotes(), clock=lambda: NOW).build(request([leg(),leg('L2','totals')]))
        self.assertTrue(all(r['matchStatus'] == 'event_identity_conflict' for r in result['legs']))
        self.assertEqual(result['events'], [])

    def test_stale_evidence_and_forecasts_do_not_generate_scripts(self):
        data = catalog(model=True)
        for e in data['events']['basketball_nba:game-a']['evidence']: e['validUntil'] = iso(NOW-1)
        report = self.service(data).build(request())
        self.assertEqual(report['events'][0]['context']['facts'], [])
        self.assertEqual(report['legs'][0]['gameScript']['status'], 'unavailable')
        self.assertIsNone(report['legs'][0]['modelWinProbability'])
        for mutate in ('stale','no_evaluation','bad_weights'):
            data = catalog(model=True); model = data['events']['basketball_nba:game-a']['forecast']
            if mutate == 'stale': model['generatedAt'] = iso(NOW-3601)
            if mutate == 'no_evaluation': model['evaluationEvidenceId'] = 'context'
            if mutate == 'bad_weights': model['scenarios'][0]['probability'] = .9
            self.assertEqual(self.service(data).build(request())['legs'][0]['gameScript']['status'], 'unavailable', mutate)

    def test_tied_scenarios_are_not_labeled_uniquely_most_probable(self):
        data = catalog(model=True)
        for scenario in data['events']['basketball_nba:game-a']['forecast']['scenarios']: scenario['probability'] = .5
        script = self.service(data).build(request())['events'][0]['gameScript']
        self.assertEqual(script['status'], 'model_supplied')
        self.assertIsNone(script['mostLikelyScenarioId'])

    def test_wrong_catalog_event_cannot_supply_venue_or_scripts(self):
        data = catalog(model=True); data['events']['basketball_nba:game-a']['homeTeam'] = 'Wrong team'
        result = self.service(data).build(request())
        self.assertEqual(result['events'][0]['context']['status'], 'unavailable')
        self.assertIsNone(result['events'][0]['context']['venue'])

    def test_roof_evidence_controls_weather_and_outdoor_is_researched_once(self):
        for roof in ('indoor','retractable'):
            data = catalog(roof)
            v = data['events']['basketball_nba:game-a']['venue']
            v.update(roofState='closed', roofEvidenceIds=['context'])
            result = self.service(data).build(request())
            self.assertEqual(result['events'][0]['weather']['status'], 'not_applicable')
        data = catalog('retractable')
        result = self.service(data).build(request())
        self.assertEqual(result['events'][0]['weather']['reason'], 'roof_state_unknown')
        class Weather:
            def __init__(self): self.calls = 0
            def get(self, *args, **kwargs):
                self.calls += 1
                return {'status':'available', 'kind':'forecast', 'retrievedAt':iso(NOW)}
        weather = Weather(); s = self.service(catalog('outdoor'), weather=weather)
        result = s.build(request([leg(),leg('L2','totals')]))
        self.assertEqual(weather.calls, 1)
        self.assertEqual(result['legs'][0]['weather'], result['legs'][1]['weather'])
        s.build(request()); self.assertEqual(weather.calls, 1)

    def test_provider_failure_is_sanitized_without_credits_or_fake_probabilities(self):
        class Broken:
            def get(self, *args, **kwargs): raise RuntimeError('secret-not-for-output')
        result = ReportService(Broken(), clock=lambda: NOW).build(request())
        self.assertEqual(result['legs'][0]['matchStatus'], 'provider_unavailable')
        self.assertNotIn('secret-not-for-output', json.dumps(result))
        self.assertEqual(len(result['legs'][0]['seven']), 7)

    def test_input_limits_duplicates_and_urls_are_rejected_before_provider_calls(self):
        cases = [request([]), request([leg(str(i),event_id='g'+str(i)) for i in range(9)]),
                 request([leg(),leg()]), request([leg(),dict(leg(),id='other')]),
                 dict(request(), totalStake='NaN'), dict(request(), totalStake='10001'),
                 dict(request(), url='https://example.test')]
        for field, value in [('eventId','https://example.test'),('point',True),('sport',[]),
                             ('market','alternate_spreads'),('bookmaker','unknown'),('outcome','')]:
            d=request();d['legs'][0][field]=value;cases.append(d)
        for d in cases:
            with self.assertRaises((ValueError, TypeError)): parse_request(d)
        self.assertEqual(self.calls, [])

    def test_busy_rate_limit_budget_and_expiry_during_research(self):
        s=self.service();s.gate.acquire()
        with self.assertRaises(ReportBusy):s.build(request())
        s.gate.release()
        for _ in range(20):s.build(request())
        with self.assertRaises(ReportBusy):s.build(request())
        times=iter([NOW,NOW+901])
        result=self.service(catalog(model=True),clock=lambda:next(times)).build(request())
        self.assertEqual(result['legs'][0]['matchStatus'],'expired_during_report')
        self.assertIsNone(result['legs'][0]['modelWinProbability'])
        self.assertEqual(result['legs'][0]['gameScript']['status'],'unavailable')

    def test_source_credentials_and_unknown_quote_fields_are_not_exposed(self):
        data=catalog();data['events']['basketball_nba:game-a']['evidence'][0]['url']='https://example.test/?apiKey=not-for-output'
        result=self.service(data).build(request())
        self.assertNotIn('not-for-output',json.dumps(result))
        original=self.odds.get
        def extra(*args,**kwargs):
            result=deepcopy(original(*args,**kwargs))
            for q in result['quotes']:q['privateApiKey']='not-for-output'
            return result
        self.odds.get=extra
        self.assertNotIn('not-for-output',json.dumps(self.service().build(request())))

    def test_budget_exhaustion_and_locked_odds_service_do_not_wait_indefinitely(self):
        ticks=[0]
        class Slow:
            def get(self,*args,**kwargs):
                ticks[0]=21
                return {'quotes':normalize([event()],'basketball_nba','spreads',NOW)}
        result=ReportService(Slow(),clock=lambda:NOW,monotonic=lambda:ticks[0]).build(request())
        self.assertEqual(result['legs'][0]['matchStatus'],'provider_unavailable')
        self.odds.lock.acquire()
        try:
            with self.assertRaisesRegex(RuntimeError,'busy'):self.odds.get('basketball_nba',timeout=.001)
        finally:self.odds.lock.release()

    def test_weather_failure_stale_catalog_and_context_failure_are_explicit(self):
        class BrokenWeather:
            def get(self,*args,**kwargs):raise RuntimeError('private-weather-key')
        result=self.service(catalog('outdoor'),weather=BrokenWeather()).build(request())
        self.assertEqual(result['legs'][0]['weather']['reason'],'weather_provider_unavailable')
        self.assertNotIn('private-weather-key',json.dumps(result))
        service=self.service(catalog());self.path.write_text('{broken',encoding='utf8')
        result=service.build(request())
        self.assertEqual(result['events'][0]['context']['reason'],'context_provider_unavailable')
        self.assertEqual(result['legs'][0]['gameScript']['status'],'unavailable')


class WeatherTests(unittest.TestCase):
    def payload(self):
        return {'utc_offset_seconds':0,'hourly':{'time':['2026-11-07T01:00'],
            'temperature_2m':[65], 'precipitation_probability':[10], 'wind_speed_10m':[5], 'wind_gusts_10m':[9]},
            'hourly_units':{'temperature_2m':'°F','precipitation_probability':'%',
                            'wind_speed_10m':'mp/h','wind_gusts_10m':'mp/h'}}

    def test_fixed_host_kickoff_hour_units_and_secret_free_provenance(self):
        calls=[]
        adapter=OpenMeteoWeather('commercial','synthetic-credential',fetch=lambda url,timeout:(calls.append(url) or self.payload()))
        result=adapter.get({'startAt':START},{'latitude':0,'longitude':0},NOW,5)
        self.assertTrue(calls[0].startswith('https://customer-api.open-meteo.com/v1/forecast?'))
        self.assertEqual(result['kind'],'forecast')
        self.assertEqual(result['values']['temperature_2m'],65)
        self.assertNotIn('synthetic-credential',json.dumps(result))
        for field in ('utc_offset_seconds','units','hour'):
            data=self.payload()
            if field=='utc_offset_seconds':data[field]=3600
            if field=='units':data['hourly_units']['temperature_2m']='°C'
            if field=='hour':data['hourly']['time']=['2026-11-06T20:00']
            adapter.fetch=lambda *args:data
            with self.assertRaises(ValueError):adapter.get({'startAt':START},{'latitude':0,'longitude':0},NOW,5)

    def test_disabled_or_missing_commercial_key_does_not_fetch(self):
        for mode,key in [('disabled',''),('commercial','')]:
            adapter=OpenMeteoWeather(mode,key,fetch=lambda *args:self.fail('must not fetch'))
            self.assertEqual(adapter.get({'startAt':START},{},NOW,5)['status'],'unavailable')

    def test_network_reader_caps_bytes_and_slow_stream_deadline(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read1(self,size):return b'x'*size
        with patch('server.report_sources.open_request',return_value=Response()):
            with self.assertRaises(ValueError):read_json_response('synthetic-request',5,10)
            with patch('server.report_sources.time.monotonic',side_effect=[0,6]):
                with self.assertRaises(TimeoutError):read_json_response('synthetic-request',5,10)

    def test_provider_reader_does_not_follow_redirects(self):
        calls=[]
        def app(environ,start_response):
            calls.append(environ['PATH_INFO'])
            start_response('302 Found',[('Location','/must-not-follow')])
            return [b'']
        class Quiet(WSGIRequestHandler):
            def log_message(self,*args):pass
        server=make_server('127.0.0.1',0,app,handler_class=Quiet)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with self.assertRaises(HTTPError):
                read_json_response(f'http://127.0.0.1:{server.server_port}/redirect',2,100)
            self.assertEqual(calls,['/redirect'])
        finally:server.shutdown();thread.join(timeout=5);server.server_close()


class EndpointTests(unittest.TestCase):
    def call(self, payload=None, auth=True, **overrides):
        raw=json.dumps(request() if payload is None else payload).encode()
        environ={'PATH_INFO':'/api/game-reports','REQUEST_METHOD':'POST','CONTENT_TYPE':'application/json',
                 'CONTENT_LENGTH':str(len(raw)),'wsgi.input':BytesIO(raw)}
        if auth:environ['HTTP_AUTHORIZATION']='Bearer synthetic-access'
        environ.update(overrides);response=[]
        with patch.dict(os.environ,{'ODDS_PREVIEW_TOKEN':'synthetic-access'}):
            body=b''.join(application(environ,lambda status,headers:response.append((status,dict(headers)))))
        return response[0][0],response[0][1],json.loads(body)

    def test_authentication_runs_before_body_read_and_unicode_auth_is_safe(self):
        class NoRead:
            def read(self,*args):raise AssertionError('Unauthenticated input was read')
        self.assertEqual(self.call(auth=False,**{'wsgi.input':NoRead()})[0],'401 Unauthorized')
        self.assertEqual(self.call(HTTP_AUTHORIZATION='Bearer 非ASCII')[0],'401 Unauthorized')

    def test_post_route_contract_and_successful_synthetic_report(self):
        service=OddsService('synthetic-only',fetch=lambda *args:[event()],clock=lambda:NOW)
        report=ReportService(service,context=ContextCatalog(''),clock=lambda:NOW)
        with patch('server.odds.report_service',report):
            status,headers,body=self.call()
        self.assertEqual(status,'200 OK');self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(body['schemaVersion'],1)
        self.assertEqual(len(body['legs'][0]['seven']),7)

    def test_body_method_and_json_limits(self):
        for overrides,status in [({'REQUEST_METHOD':'GET'},'405 Method Not Allowed'),
                ({'CONTENT_TYPE':'text/plain'},'415 Unsupported Media Type'),
                ({'CONTENT_LENGTH':'32769'},'413 Payload Too Large'),
                ({'CONTENT_LENGTH':''},'400 Bad Request'),
                ({'CONTENT_LENGTH':'3','wsgi.input':BytesIO(b'xx')},'400 Bad Request'),
                ({'CONTENT_LENGTH':'3','wsgi.input':BytesIO(b'NaN')},'400 Bad Request'),
                ({'CONTENT_LENGTH':'13','wsgi.input':BytesIO(b'{"x":1,"x":2}')},'400 Bad Request')]:
            self.assertEqual(self.call(**overrides)[0],status,overrides)

    def test_busy_and_internal_failure_do_not_expose_exception_messages(self):
        class Broken:
            def __init__(self,error):self.error=error
            def build(self,*args):raise self.error
        for error,status in [(ReportBusy('private-token'),'429 Too Many Requests'),
                             (RuntimeError('private-token'),'503 Service Unavailable')]:
            with patch('server.odds.report_service',Broken(error)):
                response=self.call()
            self.assertEqual(response[0],status)
            self.assertNotIn('private-token',json.dumps(response))

    def test_real_local_http_post_uses_existing_auth_and_returns_report(self):
        class Quiet(WSGIRequestHandler):
            def log_message(self,*args):pass
        odds=OddsService('synthetic-only',fetch=lambda *args:[event()],clock=lambda:NOW)
        reports=ReportService(odds,context=ContextCatalog(''),clock=lambda:NOW)
        server=make_server('127.0.0.1',0,application,handler_class=Quiet)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        try:
            with patch.dict(os.environ,{'ODDS_PREVIEW_TOKEN':'synthetic-access'}), patch('server.odds.report_service',reports):
                thread.start()
                req=Request(f'http://127.0.0.1:{server.server_port}/api/game-reports',
                    data=json.dumps(request()).encode(),headers={'Content-Type':'application/json',
                    'Authorization':'Bearer synthetic-access'})
                with urlopen(req,timeout=5) as response:
                    self.assertEqual(response.status,200)
                    body=json.load(response)
                self.assertEqual(body['legs'][0]['matchStatus'],'matched')
                self.assertEqual(len(body['legs'][0]['seven']),7)
        finally:
            server.shutdown();thread.join(timeout=5);server.server_close()
