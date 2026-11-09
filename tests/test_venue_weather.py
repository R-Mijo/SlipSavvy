from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from server.game_reports import ReportService
from server.odds import OddsService
from server.report_sources import ContextCatalog, iso, timestamp
from server.venue_weather import VenueCatalog, NwsWeather, nws_url

NOW=timestamp('2026-11-07T23:30:00Z')
START='2026-11-08T21:25:00Z'
SPORT='americanfootball_nfl'
HOURLY='https://api.weather.gov/gridpoints/SEW/125,67/forecast/hourly'


def event():
    return {'eventId':'synthetic-weather','sport':SPORT,'homeTeam':'Seattle Seahawks','awayTeam':'Arizona Cardinals','startAt':START}


def research(venue='Lumen Field',identity='SEA00'):
    return {'status':'partial','reason':None,'mapping':{'status':'matched','gameId':'2026_09_ARI_SEA','season':2026,'week':9,
        'seasonType':'REG','homeTeamCode':'SEA','awayTeamCode':'ARI','startAt':START,
        'reportedVenue':{'id':identity,'name':venue}},'sources':[{'id':'nflverse-schedule-2026','dataset':'schedule',
        'sourceUrl':'https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv',
        'licenseUrl':'https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md','attribution':'Synthetic test source',
        'providerUpdatedAt':iso(NOW-60),'retrievedAt':iso(NOW),'metadataCheckedAt':iso(NOW),
        'validUntil':iso(NOW+900),'recordUpdatedAt':None,'timeBasis':'file_snapshot_not_record_confirmation','sha256':'0'*64}],
        'coverage':{'schedule':'matched','injuries':'unavailable','roster':'not_requested'},
        'players':[],'teamInjuries':[],'listedInjuryCount':0,'injuriesTruncated':False,'warnings':['Synthetic fixture: additional research unavailable.']}


def forecast():
    return {'properties':{'updateTime':iso(NOW-3600),'periods':[{'startTime':'2026-11-08T13:00:00-08:00',
        'endTime':'2026-11-08T14:00:00-08:00','temperature':48,'temperatureUnit':'F',
        'windSpeed':'5 to 10 mph','probabilityOfPrecipitation':{'unitCode':'wmoUnit:percent','value':60}}]}}


def weather_fixture():
    point={'geometry':{'type':'Point','coordinates':[-122.3317,47.5953]},'properties':{'forecastHourly':HOURLY}}
    weather=NwsWeather(fetch=lambda url,timeout:point if '/points/' in url else forecast(),clock=lambda:NOW)
    return weather.get(event(),{'latitude':47.595277777778,'longitude':-122.33166666667},NOW,20)


def report_fixture():
    ev=event()
    provider={'id':ev['eventId'],'sport_key':SPORT,'commence_time':START,'home_team':ev['homeTeam'],
        'away_team':ev['awayTeam'],'bookmakers':[{'key':'fanduel','title':'FanDuel','last_update':iso(NOW-10),
        'markets':[{'key':'h2h','outcomes':[{'name':ev['homeTeam'],'price':-110}]}]}]}
    class Research:
        def lookup(self,*args,**kwargs):return research()
    odds=OddsService('synthetic',fetch=lambda *args:[provider],clock=lambda:NOW)
    class Weather:
        def get(self,*args,**kwargs):return weather_fixture()
    req={'totalStake':'10','legs':[{'id':'leg-1','eventId':ev['eventId'],'sport':SPORT,'market':'h2h',
        'bookmaker':'fanduel','outcome':ev['homeTeam'],'point':None,'americanOdds':'-110'}]}
    return ReportService(odds,context=ContextCatalog(''),weather=Weather(),research=Research(),clock=lambda:NOW).build(req)


class VenueTests(unittest.TestCase):
    def test_exact_event_id_and_name_are_both_required_never_use_home_team_or_schedule_roof(self):
        catalog=VenueCatalog()
        v=catalog.lookup(event(),research(),NOW)
        self.assertEqual(v['status'],'matched_catalog')
        self.assertEqual(v['roof'],'outdoor')
        self.assertEqual(v['scheduleSourceId'],'nflverse-schedule-2026')
        for r in [research('Bernabeu','MAD01'),research('Tottenham Hotspur Stadium','JAX00'),
                  research('U.S. Bank Stadium','SEA00'),research('Lumen Field','MIN01')]:
            self.assertEqual(catalog.lookup(event(),r,NOW)['status'],'unavailable')
        r=research();r['mapping']['reportedVenue']={'id':None,'name':'Lumen Field'}
        self.assertEqual(catalog.lookup(event(),r,NOW)['reason'],'schedule_venue_missing')
        r=research();r['mapping']['startAt']=iso(timestamp(START)+3600)
        self.assertEqual(catalog.lookup(event(),r,NOW)['status'],'unavailable')

    def test_indoor_retractable_and_expired_evidence_states_remain_distinct(self):
        c=VenueCatalog()
        self.assertEqual(c.lookup(event(),research('U.S. Bank Stadium','MIN01'),NOW)['roof'],'indoor')
        v=c.lookup(event(),research('Lucas Oil Stadium','IND00'),NOW)
        self.assertEqual(v['roof'],'retractable');self.assertEqual(v['roofState'],'unknown')
        self.assertIsNone(v['latitude'])
        self.assertEqual(c.lookup(event(),research(),NOW+31*86400)['status'],'unavailable')
        r=research();r['sources'][0]['validUntil']=iso(NOW)
        self.assertEqual(c.lookup(event(),r,NOW)['reason'],'schedule_venue_evidence_unavailable')

    def test_indoor_and_unknown_retractable_roof_do_not_fetch_city_weather(self):
        class NoWeather:
            def get(self,*a,**kw):raise AssertionError('No city weather should be fetched')
        service=ReportService(None,weather=NoWeather(),clock=lambda:NOW,research=False)
        for name,identity,expected in [('U.S. Bank Stadium','MIN01','not_applicable'),('Lucas Oil Stadium','IND00','unavailable')]:
            ev=event();ev['venue']=VenueCatalog().lookup(ev,research(name,identity),NOW)
            w=service._weather(ev,{'venue':None},NOW,service.monotonic()+20)
            self.assertEqual(w['status'],expected)
            if expected=='unavailable':self.assertEqual(w['reason'],'roof_state_unknown')

    def test_report_fixture_has_matched_venue_and_weather_without_forecast_or_edge(self):
        r=report_fixture()
        self.assertEqual(r['events'][0]['venue']['stadiumId'],'SEA00')
        self.assertEqual(r['events'][0]['weather']['provider'],'NWS')
        self.assertIsNone(r['legs'][0]['modelWinProbability'])
        self.assertIsNone(r['assessment']['estimatedWinProbability'])
        path=Path(__file__).parents[1]/'mobile/tests/fixtures/venue-weather-v1.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf8')),r)

    def test_venue_expiry_during_forecast_removes_weather_and_indoor_exemption(self):
        ticks=[NOW]
        ev=event()
        class Research:
            def lookup(self,*a,**kw):
                r=research();r['sources'][0]['validUntil']=iso(NOW+1);return r
        class Weather:
            def get(self,*a,**kw):ticks[0]=NOW+2;return weather_fixture()
        provider={'id':ev['eventId'],'sport_key':SPORT,'commence_time':START,'home_team':ev['homeTeam'],
            'away_team':ev['awayTeam'],'bookmakers':[{'key':'fanduel','last_update':iso(NOW-10),
                'markets':[{'key':'h2h','outcomes':[{'name':ev['homeTeam'],'price':-110}]}]}]}
        odds=OddsService('synthetic',fetch=lambda *a:[provider],clock=lambda:ticks[0])
        req={'totalStake':'10','legs':[{'id':'L','eventId':ev['eventId'],'sport':SPORT,'market':'h2h',
            'bookmaker':'fanduel','outcome':ev['homeTeam'],'point':None,'americanOdds':'-110'}]}
        r=ReportService(odds,context=ContextCatalog(''),weather=Weather(),research=Research(),clock=lambda:ticks[0]).build(req)
        self.assertEqual(r['events'][0]['venue']['reason'],'venue_evidence_expired')
        self.assertEqual(r['legs'][0]['weather']['status'],'unavailable')

    def test_explicit_disabled_weather_mode_is_respected(self):
        with patch.dict('os.environ',{'REPORT_WEATHER_MODE':'disabled'}):
            service=ReportService(None,research=False)
            self.assertIsInstance(service.weather,NwsWeather)
            self.assertEqual(service.weather.mode,'disabled')


class NwsTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.data=forecast()
        self.point={'geometry':{'type':'Point','coordinates':[-122.3317,47.5953]},'properties':{'forecastHourly':HOURLY}}
        def fetch(url,timeout):self.calls.append((url,timeout));return self.point if '/points/' in url else self.data
        self.weather=NwsWeather(fetch=fetch,clock=lambda:NOW)
        self.venue={'latitude':47.595277777778,'longitude':-122.33166666667}

    def get(self):return self.weather.get(event(),self.venue,NOW,20)

    def test_kickoff_hour_preserves_wind_range_null_gusts_and_source_times(self):
        r=self.get()
        self.assertEqual(r['status'],'available');self.assertEqual(r['coverage'],'partial')
        self.assertEqual(r['windRangeMph'],{'low':5,'high':10})
        self.assertIsNone(r['values']['windSpeedMph']);self.assertIsNone(r['values']['windGustMph'])
        self.assertEqual(r['values']['precipitationChance'],60)
        self.assertEqual(r['missingFields'],['windGustMph'])
        self.assertEqual(r['providerUpdatedAt'],iso(NOW-3600))
        self.assertEqual(r['retrievedAt'],iso(NOW))
        self.assertEqual(r['hourAt'],'2026-11-08T21:00:00+00:00')
        self.assertEqual(len(self.calls),2)

    def test_celsius_quantitative_units_and_missing_precipitation_never_become_zero(self):
        h=self.data['properties']['periods'][0]
        h.update(temperature=10,temperatureUnit='C',windSpeed={'unitCode':'wmoUnit:m_s','value':10},
                 probabilityOfPrecipitation={'unitCode':'wmoUnit:percent','value':None})
        r=self.get();self.assertEqual(r['values']['temperatureF'],50)
        self.assertAlmostEqual(r['values']['windSpeedMph'],22.369362920544)
        self.assertIsNone(r['values']['precipitationChance'])
        h['temperature']={'unitCode':'wmoUnit:degF','value':50}
        self.assertEqual(self.get()['values']['temperatureF'],50)
        h['windSpeed']={'unitCode':'wmoUnit:m_s','value':True}
        self.assertIsNone(self.get()['values']['windSpeedMph'])

    def test_forecast_hour_staleness_duplicates_bad_point_and_redirect_targets_fail_closed(self):
        for mutate,reason in [
            (lambda:self.data['properties'].update(updateTime=iso(NOW-21601)),'weather_forecast_stale'),
            (lambda:self.data['properties']['periods'].append(deepcopy(self.data['properties']['periods'][0])),'kickoff_hour_unavailable'),
            (lambda:self.point['geometry'].update(coordinates=[0,0]),'weather_provider_unavailable'),
            (lambda:self.point['properties'].update(forecastHourly='https://api.weather.gov.evil.test/private'),'weather_provider_unavailable'),
            (lambda:self.data['properties']['periods'][0].update(endTime='2026-11-08T23:00:00Z'),'weather_provider_unavailable'),
        ]:
            self.setUp();mutate();r=self.get();self.assertEqual(r['status'],'unavailable');self.assertEqual(r['reason'],reason)

    def test_url_and_read_bounds_no_credentials_no_redirects(self):
        for u in ['http://api.weather.gov/gridpoints/SEW/125,67/forecast/hourly',HOURLY+'?url=private',
                  HOURLY+'#x',HOURLY.replace('api.weather.gov','u:p@api.weather.gov'),
                  HOURLY.replace('api.weather.gov','api.weather.gov:444')]:
            with self.assertRaises(ValueError):nws_url(u,'hourly')
        with patch('server.venue_weather.read_json_response',return_value={}) as read:
            NwsWeather()._fetch(HOURLY,10)
            req,timeout,limit=read.call_args.args
            self.assertIn('SlipSavvy',req.get_header('User-agent'))
            self.assertIsNone(req.get_header('Authorization'))
            self.assertEqual(timeout,5);self.assertEqual(limit,524288)

    def test_disabled_and_outside_window_skip_network_and_provider_errors_are_sanitized(self):
        self.weather.mode='disabled';self.assertEqual(self.get()['reason'],'weather_disabled');self.assertEqual(self.calls,[])
        self.weather.mode='nws';ev=dict(event(),startAt=iso(NOW+8*86400))
        self.assertEqual(self.weather.get(ev,self.venue,NOW,20)['reason'],'outside_forecast_window');self.assertEqual(self.calls,[])
        def bad(*a):raise RuntimeError('private-request-not-for-output')
        self.weather.fetch=bad
        self.assertNotIn('private-request',json.dumps(self.get()))

    def test_same_event_weather_cache_reuses_request_and_rechecks_validity(self):
        ev=event();ev['venue']=VenueCatalog().lookup(ev,research(),NOW)
        service=ReportService(None,weather=self.weather,clock=lambda:NOW,research=False)
        for _ in range(2):service._weather(ev,{'venue':None},NOW,service.monotonic()+20)
        self.assertEqual(len(self.calls),2)
        service._weather(ev,{'venue':None},NOW+301,service.monotonic()+20)
        self.assertEqual(len(self.calls),4)


if __name__=='__main__':unittest.main()
