from copy import deepcopy
from datetime import datetime, timezone
import io
import hashlib
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from server.nfl_research import (API, LICENSE, REPO, NflResearch, NflverseFiles,
                                _read, csv_rows, event_injuries, match_game, match_player)
from server.report_sources import iso, timestamp, ContextCatalog
from server.game_reports import ReportService
from server.odds import OddsService

NOW = timestamp('2026-11-07T20:00:00Z')
START = '2026-11-08T18:00:00Z'
SPORT = 'americanfootball_nfl'


def game():
    return {'eventId':'synthetic-event','sport':SPORT,'homeTeam':'Buffalo Bills','awayTeam':'Miami Dolphins','startAt':START}


def schedule():
    return {'game_id':'2026_10_MIA_BUF','season':'2026','game_type':'REG','week':'10',
            'gameday':'2026-11-08','gametime':'13:00','home_team':'BUF','away_team':'MIA',
            'home_score':'NA','away_score':'NA','roof':'dome','stadium':'Unverified test venue'}


def roster():
    return {'season':'2026','game_type':'REG','team':'BUF','week':'10','gsis_id':'00-0000001',
            'full_name':'Synthetic Runner','status':'ACT'}


def injury():
    return {'season':'2026','season_type':'REG','game_type':'REG','team':'BUF','week':'10',
            'gsis_id':'00-0000001','full_name':'Synthetic Runner','position':'RB',
            'report_status':'Questionable','practice_status':'Limited Participation in Practice',
            'report_primary_injury':'Synthetic test injury','practice_primary_injury':'Synthetic test injury'}


def source(dataset):
    name = {'schedule':'schedules/games.csv','roster':'rosters/roster_2026.csv','injuries':'injuries/injuries_2026.csv'}[dataset]
    return {'id':'nflverse-'+dataset+'-2026','dataset':dataset,'sourceUrl':REPO+'/releases/download/'+name,
            'licenseUrl':LICENSE,'attribution':'Synthetic fixture; nflverse CC BY 4.0 shape',
            'providerUpdatedAt':iso(NOW-3600),'retrievedAt':iso(NOW-20),'metadataCheckedAt':iso(NOW-20),
            'validUntil':iso(NOW+880),'recordUpdatedAt':None,'timeBasis':'file_snapshot_not_record_confirmation','sha256':'0'*64}


class Files:
    def __init__(self):
        self.data={'schedule':[schedule()],'roster':[roster()],'injuries':[injury()]}
        self.calls=[]
        self.fail=set()
    def get(self, dataset, season, timeout):
        self.calls.append((dataset,season))
        if dataset in self.fail: raise RuntimeError('private-signed-download-not-for-output')
        return deepcopy(self.data[dataset]),source(dataset)


def research_fixture():
    return NflResearch(Files(),clock=lambda:NOW).lookup(game(),['Synthetic Runner'],NOW,20)


class ResearchTests(unittest.TestCase):
    def test_python_mobile_snapshot_contract_matches_fixture(self):
        path=Path(__file__).parents[1]/'mobile/tests/fixtures/nfl-research-v1.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf8')),research_fixture())

    def test_exact_schedule_mapping_uses_eastern_zone_and_accepts_neutral_venue_without_roof_claims(self):
        mapping=match_game([schedule()],game(),NOW)
        self.assertEqual(mapping['gameId'],'2026_10_MIA_BUF')
        self.assertEqual(mapping['startAt'],iso(timestamp(START)))
        self.assertNotIn('roof',mapping)
        summer=dict(schedule(),gameday='2026-09-13',gametime='13:00',week='1',game_id='2026_01_MIA_BUF')
        ev=dict(game(),startAt='2026-09-13T17:00:00Z')
        self.assertEqual(match_game([summer],ev,timestamp('2026-09-12T20:00:00Z'))['week'],1)

    def test_ambiguous_rescheduled_completed_unmapped_and_dst_conflicts_fail_closed(self):
        for rows,ev in [([schedule(),schedule()],game()),([dict(schedule(),gametime='13:05')],game()),
                        ([dict(schedule(),home_score='0')],game()),([schedule()],dict(game(),homeTeam='Bills')),
                        ([dict(schedule(),game_id='wrong')],game()),
                        ([dict(schedule(),gameday='2026-11-01',gametime='01:30')],dict(game(),startAt='2026-11-01T05:30:00Z'))]:
            with self.assertRaises(ValueError):match_game(rows,ev,timestamp(ev['startAt'])-3600)

    def test_snapshot_maps_gsis_and_week_but_never_calls_player_confirmed_or_probability_known(self):
        r=research_fixture()
        self.assertEqual(r['status'],'partial')
        p=r['players'][0]
        self.assertEqual(p['status'],'roster_snapshot')
        self.assertEqual(p['gsisId'],'00-0000001')
        self.assertEqual(p['injury']['status'],'reported')
        self.assertEqual(p['injury']['record']['gameStatus'],'Questionable')
        self.assertIsNone(p['injury']['record']['recordUpdatedAt'])
        self.assertEqual(len(r['sources']),3)
        self.assertNotEqual(r['sources'][0]['providerUpdatedAt'],r['sources'][0]['retrievedAt'])
        self.assertTrue(all(s['recordUpdatedAt'] is None for s in r['sources']))
        self.assertNotIn('winProbability',json.dumps(r))

    def test_player_names_are_exact_and_ambiguous_or_future_roster_rows_are_not_guessed(self):
        m=match_game([schedule()],game(),NOW)
        for name in ('S. Runner','synthetic runner','Synthetic Runner Jr.'):
            self.assertEqual(match_player(name,[roster()],m,{})['status'],'unmapped')
        for rows in ([roster(),roster()],[roster(),dict(roster(),gsis_id='00-0000002',week='9')]):
            self.assertEqual(match_player('Synthetic Runner',rows,m,{})['status'],'ambiguous')
        self.assertEqual(match_player('Synthetic Runner',[dict(roster(),week='11')],m,{})['status'],'unmapped')
        p=match_player('Synthetic Runner',[dict(roster(),week='9')],m,{})
        self.assertEqual(p['rosterWeek'],9)
        self.assertEqual(p['injury']['status'],'coverage_unknown')

    def test_injuries_require_same_season_week_team_gsis_and_nonconflicting_name(self):
        m=match_game([schedule()],game(),NOW)
        for changes in ({'week':'9'},{'season':'2025'},{'team':'NYJ'},{'season_type':'POST'},{'gsis_id':'wrong'}):
            groups=event_injuries([dict(injury(),**changes)],m)
            self.assertEqual(match_player('Synthetic Runner',[roster()],m,groups)['injury']['status'],'coverage_unknown')
        groups=event_injuries([injury(),injury()],m)
        self.assertEqual(match_player('Synthetic Runner',[roster()],m,groups)['injury']['status'],'ambiguous')
        groups=event_injuries([dict(injury(),full_name='Conflicting Name')],m)
        self.assertEqual(match_player('Synthetic Runner',[roster()],m,groups)['injury']['status'],'identity_conflict')

    def test_missing_sources_and_empty_injury_rows_stay_unknown_and_sanitized(self):
        f=Files();f.data['injuries']=[]
        r=NflResearch(f,clock=lambda:NOW).lookup(game(),['Synthetic Runner'],NOW,20)
        self.assertEqual(r['players'][0]['injury']['status'],'coverage_unknown')
        self.assertEqual(r['coverage']['injuries'],'coverage_unknown')
        self.assertTrue(any('healthy' in w for w in r['warnings']))
        f.fail={'injuries','roster'}
        r=NflResearch(f,clock=lambda:NOW).lookup(game(),['Synthetic Runner'],NOW,20)
        self.assertEqual(r['players'][0]['status'],'unavailable')
        self.assertNotIn('private-signed',json.dumps(r))
        f.fail={'schedule'}
        self.assertIsNone(NflResearch(f,clock=lambda:NOW).lookup(game(),[],NOW,20)['mapping'])

    def test_mode_sport_and_deadline_bounds_do_not_start_unneeded_io(self):
        f=Files()
        for mode,ev in [('disabled',game()),('nflverse',dict(game(),sport='basketball_nba'))]:
            r=NflResearch(f,mode=mode,clock=lambda:NOW).lookup(ev,[],NOW,20)
            self.assertIsNone(r['mapping'])
        self.assertEqual(f.calls,[])
        r=NflResearch(f,clock=lambda:NOW).lookup(game(),[],NOW,0)
        self.assertEqual(r['reason'],'research_expired_during_report')

    def test_team_injury_list_is_bounded_and_does_not_fetch_rosters_without_selected_players(self):
        f=Files();f.data['injuries']=[dict(injury(),gsis_id=f'00-{i:07}',full_name=f'Synthetic {i}') for i in range(40)]
        r=NflResearch(f,clock=lambda:NOW).lookup(game(),[],NOW,20)
        self.assertEqual(len(r['teamInjuries']),32)
        self.assertEqual(r['listedInjuryCount'],40)
        self.assertTrue(r['injuriesTruncated'])
        self.assertNotIn(('roster',2026),f.calls)

    def test_shared_game_research_and_seven_findings_in_report(self):
        ev=game()
        provider={'id':ev['eventId'],'sport_key':SPORT,'commence_time':START,'home_team':ev['homeTeam'],
                  'away_team':ev['awayTeam'],'bookmakers':[{'key':'fanduel','title':'FanDuel','last_update':iso(NOW-10),
                    'markets':[{'key':'player_rush_yds','outcomes':[{'name':side,'description':'Synthetic Runner','point':50.5,'price':-110} for side in ('Over','Under')]}]}]}
        odds=OddsService('synthetic',fetch=lambda *args:provider,clock=lambda:NOW)
        f=Files();service=ReportService(odds,context=ContextCatalog(''),research=NflResearch(f,clock=lambda:NOW),clock=lambda:NOW)
        req={'totalStake':'10','legs':[{'id':str(i),'eventId':ev['eventId'],'sport':SPORT,'bookmaker':'fanduel',
            'market':'player_rush_yds','playerName':'Synthetic Runner','outcome':side,'point':50.5,'americanOdds':'-110'} for i,side in enumerate(('Over','Under'))]}
        r=service.build(req)
        self.assertEqual(len(r['events']),1)
        self.assertEqual(len(f.calls),3)
        self.assertEqual(r['events'][0]['research']['players'][0]['injury']['status'],'reported')
        self.assertTrue(all(l['modelWinProbability'] is None for l in r['legs']))
        self.assertIn('roster_snapshot',r['legs'][0]['seven'][4]['bullets'][0])
        self.assertIsNone(r['assessment']['estimatedWinProbability'])

    def test_research_expiry_during_report_removes_snapshot_and_old_seat_claims(self):
        ticks=[NOW]
        class Expiring:
            def lookup(self,*args,**kwargs):
                r=research_fixture()
                for s in r['sources']:s['validUntil']=iso(NOW+1)
                ticks[0]=NOW+2
                return r
        ev=game()
        provider={'id':ev['eventId'],'sport_key':SPORT,'commence_time':START,'home_team':ev['homeTeam'],
                  'away_team':ev['awayTeam'],'bookmakers':[{'key':'fanduel','last_update':iso(NOW-10),
                    'markets':[{'key':'player_rush_yds','outcomes':[{'name':'Over','description':'Synthetic Runner','point':50.5,'price':-110}]}]}]}
        odds=OddsService('synthetic',fetch=lambda *args:provider,clock=lambda:ticks[0])
        service=ReportService(odds,context=ContextCatalog(''),research=Expiring(),clock=lambda:ticks[0])
        req={'totalStake':'10','legs':[{'id':'L','eventId':ev['eventId'],'sport':SPORT,'bookmaker':'fanduel',
            'market':'player_rush_yds','playerName':'Synthetic Runner','outcome':'Over','point':50.5,'americanOdds':'-110'}]}
        r=service.build(req)
        self.assertEqual(r['events'][0]['research']['status'],'unavailable')
        self.assertEqual(r['events'][0]['research']['sources'],[])
        self.assertIn('expired',r['legs'][0]['seven'][0]['bullets'][0])
        self.assertNotIn('roster_snapshot',r['legs'][0]['seven'][4]['bullets'][0])


class FilesTests(unittest.TestCase):
    def setUp(self):
        self.now=NOW;self.calls=[]
        self.raw=b'season,season_type,team,week,gsis_id,full_name,report_status,practice_status\n2026,REG,BUF,10,00-0000001,Synthetic Runner,Questionable,Limited\n'
        self.asset={'id':7,'name':'injuries_2026.csv','size':len(self.raw),'updated_at':iso(NOW-100),
                    'digest':'sha256:'+hashlib.sha256(self.raw).hexdigest(),
                    'browser_download_url':REPO+'/releases/download/injuries/injuries_2026.csv'}
        self.meta={'tag_name':'injuries','assets':[self.asset]}
        def fetch(url,timeout,limit,asset=False):
            self.calls.append((url,timeout,limit,asset))
            return self.raw if asset else json.dumps(self.meta).encode()
        self.files=NflverseFiles(fetch=fetch,clock=lambda:self.now)

    def test_versions_and_file_times_are_preserved_and_cached_across_events(self):
        rows,s=self.files.get('injuries',2026,20)
        self.assertEqual(len(rows),1)
        self.assertEqual(s['providerUpdatedAt'],iso(NOW-100))
        self.assertEqual(s['retrievedAt'],iso(NOW))
        self.assertEqual(s['metadataCheckedAt'],iso(NOW))
        self.assertEqual(s['validUntil'],iso(NOW+900))
        self.files.get('injuries',2026,20);self.assertEqual(len(self.calls),2)
        self.now+=901
        _,again=self.files.get('injuries',2026,20)
        self.assertEqual(len(self.calls),3)
        self.assertEqual(again['retrievedAt'],s['retrievedAt'])
        self.assertNotEqual(again['metadataCheckedAt'],s['metadataCheckedAt'])

    def test_stale_or_conflicting_metadata_missing_columns_and_size_changes_fail_closed_with_cooldown(self):
        for mutate in [lambda:self.asset.update(updated_at=iso(NOW-129601)),
                       lambda:self.asset.update(browser_download_url='https://evil.test/private'),
                       lambda:self.meta['assets'].append(dict(self.asset)),lambda:self.asset.update(size=5000000)]:
            self.setUp();mutate()
            with self.assertRaises(RuntimeError):self.files.get('injuries',2026,20)
            count=len(self.calls)
            with self.assertRaises(RuntimeError):self.files.get('injuries',2026,20)
            self.assertEqual(len(self.calls),count)
        self.setUp();self.raw=b'invalid\nrow\n';self.asset['size']=len(self.raw)
        with self.assertRaises(RuntimeError):self.files.get('injuries',2026,20)
        self.setUp();self.raw+=b'extra'
        with self.assertRaises(RuntimeError):self.files.get('injuries',2026,20)

    def test_unsupported_inputs_and_locked_service_are_bounded(self):
        with self.assertRaises(ValueError):self.files.get('../private',2026,20)
        with self.assertRaises(ValueError):self.files.get('injuries','2026',20)
        self.files.lock.acquire()
        try:
            with self.assertRaises(TimeoutError):self.files.get('injuries',2026,.001)
        finally:self.files.lock.release()
        self.assertEqual(self.calls,[])

    def test_same_size_changed_download_fails_digest_and_concurrent_reads_share_cache(self):
        self.raw=self.raw.replace(b'Questionable',b'Qxxxxxxxxxxx')
        self.assertEqual(len(self.raw),self.asset['size'])
        with self.assertRaises(RuntimeError):self.files.get('injuries',2026,20)
        self.setUp();errors=[]
        def get():
            try:self.files.get('injuries',2026,20)
            except Exception as error:errors.append(error)
        threads=[threading.Thread(target=get) for _ in range(4)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(errors,[])
        self.assertEqual(len(self.calls),2)

    def test_missing_and_stale_sources_retain_distinct_statuses(self):
        from server.nfl_research import SourceUnavailable
        self.asset['updated_at']=iso(NOW-129601)
        with self.assertRaises(SourceUnavailable) as caught:self.files.get('injuries',2026,20)
        self.assertEqual(caught.exception.reason,'stale')
        self.setUp();self.meta['assets']=[]
        with self.assertRaises(SourceUnavailable) as caught:self.files.get('injuries',2026,20)
        self.assertEqual(caught.exception.reason,'missing')

    def test_csv_rejects_duplicate_headers_oversized_fields_and_extra_values(self):
        for raw in [b'a,a\n1,2\n',b'a\n1,2\n',b'a\n'+b'x'*2001+b'\n',b'a\nb\n']:
            with self.assertRaises(ValueError):csv_rows(raw,{'required'})

    def test_public_download_redirect_allows_only_the_expected_cdn_without_disclosing_signed_url(self):
        class Response(io.BytesIO):
            read1=io.BytesIO.read
        url=REPO+'/releases/download/injuries/injuries_2026.csv'
        for target in ['http://release-assets.githubusercontent.com/github-production-release-asset/a',
                       'https://evil.test/github-production-release-asset/a',
                       'https://release-assets.githubusercontent.com.evil.test/github-production-release-asset/a',
                       'https://u:p@release-assets.githubusercontent.com/github-production-release-asset/a',
                       'https://release-assets.githubusercontent.com:444/github-production-release-asset/a']:
            error=HTTPError(url,302,'redirect',{'Location':target},Response())
            with patch('server.nfl_research.open_request',side_effect=error) as op:
                with self.assertRaises(ValueError):_read(url,2,100,asset=True)
                self.assertEqual(op.call_count,1)
        target='https://release-assets.githubusercontent.com/github-production-release-asset/a?sig=private'
        with patch('server.nfl_research.open_request',side_effect=[HTTPError(url,302,'redirect',{'Location':target},Response()),Response(b'csv')]) as op:
            self.assertEqual(_read(url,2,100,asset=True),b'csv')
            self.assertEqual(op.call_count,2)
        with patch('server.nfl_research.open_request',return_value=Response(b'12345')):
            with self.assertRaises(ValueError):_read(url,2,4,asset=True)


if __name__=='__main__':unittest.main()
