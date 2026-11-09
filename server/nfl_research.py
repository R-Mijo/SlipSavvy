"""Bounded free nflverse file snapshots; no forecasts or inferred availability."""
from collections import OrderedDict
import csv
import hashlib
from datetime import datetime, timezone
import io
import os
import re
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request
from zoneinfo import ZoneInfo

from .report_sources import iso, open_request, strict_json, timestamp

REPO = 'https://github.com/nflverse/nflverse-data'
API = 'https://api.github.com/repos/nflverse/nflverse-data/releases/tags/'
LICENSE = REPO + '/blob/main/LICENSE.md'
MAX_BYTES = 4 * 1024 * 1024
GSIS = re.compile(r'00-\d{7}')
TEAMS = dict(zip([
    'Arizona Cardinals', 'Atlanta Falcons', 'Baltimore Ravens', 'Buffalo Bills',
    'Carolina Panthers', 'Chicago Bears', 'Cincinnati Bengals', 'Cleveland Browns',
    'Dallas Cowboys', 'Denver Broncos', 'Detroit Lions', 'Green Bay Packers',
    'Houston Texans', 'Indianapolis Colts', 'Jacksonville Jaguars', 'Kansas City Chiefs',
    'Los Angeles Rams', 'Los Angeles Chargers', 'Las Vegas Raiders', 'Miami Dolphins',
    'Minnesota Vikings', 'New England Patriots', 'New Orleans Saints', 'New York Giants',
    'New York Jets', 'Philadelphia Eagles', 'Pittsburgh Steelers', 'Seattle Seahawks',
    'San Francisco 49ers', 'Tampa Bay Buccaneers', 'Tennessee Titans', 'Washington Commanders',
], ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC',
    'LA','LAC','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS']))


def unavailable(reason, status='unavailable'):
    return {'status': status, 'reason': reason, 'mapping': None, 'sources': [],
            'coverage': {'schedule':'unavailable','injuries':'unavailable','roster':'not_requested'},
            'players': [], 'teamInjuries': [], 'listedInjuryCount': 0, 'injuriesTruncated': False,
            'warnings': ['No supported probability adjustment is derived from these snapshots.']}


class SourceUnavailable(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__('NFL source unavailable')


def clean(value, maximum=120):
    if not isinstance(value, str) or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid source field')
    return None if value in {'', 'NA', 'N/A'} else value


def integer(value, low, high):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or len(value) > 4:
        raise ValueError('Invalid source number')
    number = int(value)
    if not low <= number <= high:
        raise ValueError('Invalid source range')
    return number


def csv_rows(raw, required=()):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('Source exceeds limit')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if (not reader.fieldnames or len(reader.fieldnames) > 80 or len(set(reader.fieldnames)) != len(reader.fieldnames)
            or not set(required) <= set(reader.fieldnames)):
        raise ValueError('Invalid source columns')
    result = []
    for row in reader:
        if len(result) >= 20000 or None in row or any(v is None or len(v) > 2000 for v in row.values()):
            raise ValueError('Source exceeds row/field limits')
        result.append(row)
    return result


def _read(url, timeout, limit, asset=False):
    """Follow at most one public GitHub asset redirect to the exact CDN host.

    Signed CDN URLs are never persisted or returned. No caller-controlled hosts.
    """
    deadline = time.monotonic() + timeout
    for hop in range(2):
        request = Request(url, headers={'User-Agent': 'SlipSavvy-NFL-research',
                                      'Accept': 'application/octet-stream' if asset else 'application/vnd.github+json'})
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Source budget exhausted')
        try:
            response = open_request(request, timeout=min(5, remaining))
        except HTTPError as error:
            try:
                location = error.headers.get('Location', '')
                if not asset or hop or error.code not in {301,302,303,307,308}:
                    raise ValueError('Source unavailable') from None
                target = urlsplit(location)
                if (target.scheme != 'https' or target.hostname != 'release-assets.githubusercontent.com'
                        or target.username or target.password or target.port not in {None,443} or target.fragment
                        or not target.path.startswith('/github-production-release-asset/')):
                    raise ValueError('Source redirect rejected') from None
                url = location
                continue
            finally:
                error.close()
        with response:
            parts, size = [], 0
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Source budget exhausted')
                chunk = response.read1(min(65536, limit+1-size))
                if not chunk:
                    return b''.join(parts)
                size += len(chunk)
                if size > limit:
                    raise ValueError('Source exceeds limit')
                parts.append(chunk)
    raise ValueError('Source unavailable')


class NflverseFiles:
    """One process-wide cache per report service; anonymous GitHub, no API key."""
    def __init__(self, fetch=None, clock=time.time, monotonic=time.monotonic):
        self.fetch = fetch or _read
        self.clock, self.monotonic = clock, monotonic
        self.lock = threading.Lock()
        self.metadata, self.cache, self.failures = {}, OrderedDict(), {}

    def get(self, dataset, season, timeout):
        spec = {'schedule': ('schedules','games.csv',7200),
                'roster': ('rosters',f'roster_{season}.csv',172800),
                'injuries': ('injuries',f'injuries_{season}.csv',129600)}
        if dataset not in spec or type(season) is not int or not 2020 <= season <= 2100:
            raise ValueError('Unsupported source')
        tag, name, age_limit = spec[dataset]
        deadline = self.monotonic()+min(20,max(0,timeout))
        if not self.lock.acquire(timeout=max(0,deadline-self.monotonic())):
            raise TimeoutError('Research is busy')
        def fetch(url, limit, asset=False):
            left = deadline-self.monotonic()
            if left <= 0:
                raise TimeoutError('Source budget exhausted')
            return self.fetch(url, min(10,left), limit, asset=asset)
        try:
            now = self.clock()
            failure_key = dataset, season
            failure = self.failures.get(failure_key)
            if failure and 0 <= now-failure[0] < 60:
                raise SourceUnavailable(failure[1])
            meta = self.metadata.get(tag)
            if meta is None or not 0 <= now-meta[0] < 900:
                data = strict_json(fetch(API+tag, 2*1024*1024))
                if data.get('tag_name') != tag or not isinstance(data.get('assets'), list) or len(data['assets']) > 1000:
                    raise ValueError('Invalid release metadata')
                meta = self.metadata[tag] = (self.clock(), data['assets'])
            matches = [a for a in meta[1] if isinstance(a,dict) and a.get('name') == name]
            if len(matches) != 1:
                raise SourceUnavailable('missing' if not matches else 'ambiguous')
            asset = matches[0]
            updated = timestamp(asset['updated_at'])
            now = self.clock()
            if not -60 <= now-updated <= age_limit:
                raise SourceUnavailable('stale')
            if type(asset.get('size')) is not int or not 0 < asset['size'] <= MAX_BYTES:
                raise SourceUnavailable('invalid')
            url = REPO+'/releases/download/'+tag+'/'+name
            if asset.get('browser_download_url') != url or type(asset.get('id')) is not int:
                raise ValueError('Conflicting source asset identity')
            digest = asset.get('digest')
            if not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',digest):
                raise ValueError('Source digest required')
            key = dataset, season, asset['id'], asset['updated_at'], asset['size'], digest
            cached = self.cache.get(key)
            if cached is None:
                raw = fetch(url, MAX_BYTES, asset=True)
                if len(raw) != asset['size'] or hashlib.sha256(raw).hexdigest() != digest[7:]:
                    raise ValueError('Source changed during retrieval')
                required = {
                    'schedule': {'game_id','season','week','game_type','gameday','gametime','home_team','away_team','home_score','away_score'},
                    'roster': {'season','team','week','game_type','full_name','gsis_id','status'},
                    'injuries': {'season','season_type','team','week','gsis_id','full_name','report_status','practice_status'},
                }[dataset]
                cached = (self.clock(), csv_rows(raw, required))
                self.cache[key] = cached
                while len(self.cache) > 6:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(key)
            # File version metadata is checked every 15 minutes; this is not row confirmation.
            until = min(updated+age_limit, meta[0]+900)
            if until <= self.clock() or self.monotonic() >= deadline:
                raise ValueError('Source expired during retrieval')
            source = {'id':'nflverse-'+dataset+'-'+str(season), 'dataset':dataset,
                      'sourceUrl':url, 'licenseUrl':LICENSE,
                      'attribution':'nflverse (schedule maintained by Lee Sharpe); CC BY 4.0',
                      'providerUpdatedAt':iso(updated), 'retrievedAt':iso(cached[0]),
                      'metadataCheckedAt':iso(meta[0]), 'validUntil':iso(until),
                      'recordUpdatedAt':None, 'timeBasis':'file_snapshot_not_record_confirmation'}
            source['sha256'] = digest[7:]
            return cached[1], source
        except Exception as error:
            reason = error.reason if isinstance(error,SourceUnavailable) else 'invalid' if isinstance(error,ValueError) else 'unavailable'
            previous = self.failures.get((dataset,season))
            if previous is None or not 0 <= self.clock()-previous[0] < 60:
                self.failures[(dataset,season)] = self.clock(),reason
            raise SourceUnavailable(reason) from None
        finally:
            self.lock.release()


def match_game(rows, event, now):
    home, away = TEAMS.get(event.get('homeTeam')), TEAMS.get(event.get('awayTeam'))
    if not home or not away or home == away:
        raise ValueError('unmapped_team')
    start = timestamp(event['startAt'])
    if not now < start <= now+8*86400:
        raise ValueError('outside_research_window')
    candidates = []
    eastern = ZoneInfo('America/New_York')
    for row in rows:
        if row.get('home_team') != home or row.get('away_team') != away:
            continue
        try:
            local = datetime.strptime(row['gameday']+' '+row['gametime'], '%Y-%m-%d %H:%M')
            if local.year < 2020:
                continue
            # Reject nonexistent or ambiguous local times rather than guess DST.
            starts = {local.replace(tzinfo=eastern,fold=f).timestamp() for f in (0,1)
                      if datetime.fromtimestamp(local.replace(tzinfo=eastern,fold=f).timestamp(),eastern).replace(tzinfo=None) == local}
            if len(starts) != 1 or abs(next(iter(starts))-start) > 1:
                continue
            if row.get('game_type') != 'REG':
                raise ValueError('unsupported_season_type')
            season = integer(row['season'],2020,2100)
            week = integer(row['week'],1,18)
            identity = f'{season}_{week:02}_{away}_{home}'
            if row.get('game_id') != identity or any(clean(row.get(k,'')) is not None for k in ('home_score','away_score')):
                continue
            candidates.append({'status':'matched', 'gameId':identity,'season':season,'week':week,
                               'seasonType':'REG','homeTeamCode':home,'awayTeamCode':away,'startAt':iso(start),
                               'reportedVenue':{'id':clean(row.get('stadium_id',''),40),
                                                'name':clean(row.get('stadium',''),150)}})
        except (KeyError,TypeError,ValueError):
            continue
    if len(candidates) != 1:
        raise ValueError('schedule_not_matched' if not candidates else 'ambiguous_schedule')
    return candidates[0]


def injury_record(row):
    gsis = row.get('gsis_id','')
    if not GSIS.fullmatch(gsis):
        raise ValueError('Invalid injury identity')
    return {'gsisId':gsis,'team':clean(row['team']), 'playerName':clean(row['full_name']),
            'position':clean(row.get('position','')), 'gameStatus':clean(row.get('report_status','')),
            'practiceStatus':clean(row.get('practice_status','')),
            'primaryInjury':clean(row.get('report_primary_injury','')),
            'practiceInjury':clean(row.get('practice_primary_injury','')),
            'recordUpdatedAt':None}


def event_injuries(rows, mapping):
    grouped = {}
    for row in rows:
        if (row.get('season') == str(mapping['season']) and row.get('week') == str(mapping['week'])
                and row.get('team') in {mapping['homeTeamCode'],mapping['awayTeamCode']}
                and row.get('season_type',row.get('game_type')) == 'REG'
                and row.get('game_type','REG') == 'REG'):
            try:
                item = injury_record(row)
                grouped.setdefault((item['team'],item['gsisId']),[]).append(item)
            except (KeyError,ValueError,TypeError):
                continue
    return grouped


def match_player(name, rosters, mapping, injuries):
    result = {'requestedName':name,'status':'unmapped','gsisId':None,'team':None,
              'rosterWeek':None,'rosterStatus':None,'injury':{'status':'unavailable','record':None}}
    matching = []
    for row in rosters:
        if (row.get('full_name') != name or row.get('season') != str(mapping['season'])
                or row.get('team') not in {mapping['homeTeamCode'],mapping['awayTeamCode']}
                or row.get('game_type') != 'REG'):
            continue
        try:
            week = integer(row['week'],1,18)
            if week <= mapping['week'] and GSIS.fullmatch(row.get('gsis_id','')):
                matching.append((week,row))
        except (KeyError,ValueError,TypeError):
            continue
    if not matching:
        return result
    if len({row['gsis_id'] for _,row in matching}) != 1:
        result['status'] = 'ambiguous'
        return result
    latest = max(week for week,_ in matching)
    current = [row for week,row in matching if week == latest]
    if len(current) != 1:
        result['status'] = 'ambiguous'
        return result
    row = current[0]
    result.update(status='roster_snapshot',gsisId=row['gsis_id'],team=row['team'],rosterWeek=latest,
                  rosterStatus=clean(row.get('status','')))
    if injuries is not None:
        records = injuries.get((row['team'],row['gsis_id']),[])
        conflict = len(records)==1 and records[0]['playerName'] != name
        team_covered = any(team == row['team'] for team,_ in injuries)
        result['injury'] = {'status':'identity_conflict' if conflict else 'reported' if len(records)==1 else 'ambiguous' if records else 'not_listed' if team_covered else 'coverage_unknown',
                            'record':records[0] if len(records)==1 and not conflict else None}
    return result


class NflResearch:
    def __init__(self, files=None, mode=None, clock=time.time, monotonic=time.monotonic):
        self.files = files or NflverseFiles(clock=clock,monotonic=monotonic)
        self.mode = mode if mode is not None else os.environ.get('NFL_RESEARCH_MODE','nflverse')
        self.clock, self.monotonic = clock, monotonic

    def lookup(self, event, names, now, timeout):
        if event.get('sport') != 'americanfootball_nfl':
            return unavailable('unsupported_sport','not_applicable')
        if self.mode != 'nflverse':
            return unavailable('research_disabled')
        if (not isinstance(names,list) or len(names)>8 or len(set(names))!=len(names)
                or any(clean(n) is None for n in names)):
            raise ValueError('Invalid requested players')
        start = datetime.fromtimestamp(timestamp(event['startAt']),timezone.utc)
        season = start.year-1 if start.month < 3 else start.year
        deadline = self.monotonic()+max(0,timeout)
        sources = []
        coverage = {'schedule':'unavailable','injuries':'unavailable','roster':'not_requested'}
        def get(dataset):
            rows, source = self.files.get(dataset,season,max(0,deadline-self.monotonic()))
            sources.append(source)
            coverage[dataset] = 'file_snapshot'
            return rows
        try:
            mapping = match_game(get('schedule'),event,now)
            if mapping['season'] != season:
                raise ValueError('season_conflict')
        except Exception as error:
            result = unavailable('schedule_identity_or_source_unavailable')
            result['coverage']['schedule'] = error.reason if isinstance(error,SourceUnavailable) else 'identity_unmatched'
            return result
        result = unavailable(None,'partial')
        coverage['schedule'] = 'matched'
        result.update(mapping=mapping,sources=sources,coverage=coverage)
        warnings = result['warnings']
        warnings.extend(['File snapshots do not confirm current participation, starters or game-time availability.',
                         'Not listed in an injury file does not establish that a player is healthy.',
                         'Venue, actual roof state, weather, usage and recent performance are not supplied by this adapter.'])
        injuries = None
        try:
            injuries = event_injuries(get('injuries'),mapping)
            if not injuries:
                coverage['injuries'] = 'coverage_unknown'
                warnings.append('No usable injury rows match these teams and week; coverage is unknown.')
            records = [items[0] for items in injuries.values() if len(items)==1]
            records.sort(key=lambda r:(r['team'],r['playerName'] or '',r['gsisId']))
            result.update(teamInjuries=records[:32],listedInjuryCount=len(records),injuriesTruncated=len(records)>32)
            if any(len(items)>1 for items in injuries.values()):
                warnings.append('Ambiguous injury rows were withheld.')
        except Exception as error:
            coverage['injuries'] = error.reason if isinstance(error,SourceUnavailable) else 'unavailable'
            warnings.append('The injury source is unavailable or stale; no healthy-player inference is made.')
        if names:
            try:
                rosters = get('roster')
                result['players'] = [match_player(n,rosters,mapping,injuries) for n in names]
            except Exception as error:
                coverage['roster'] = error.reason if isinstance(error,SourceUnavailable) else 'unavailable'
                result['players'] = [dict(requestedName=n,status='unavailable',gsisId=None,team=None,
                                          rosterWeek=None,rosterStatus=None,injury={'status':'unavailable','record':None}) for n in names]
                warnings.append('Roster identity mapping is unavailable; no name guess was applied.')
        if self.monotonic() >= deadline or any(timestamp(s['validUntil']) <= self.clock() for s in sources):
            return unavailable('research_expired_during_report')
        return result
