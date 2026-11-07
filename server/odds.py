"""Curated pregame lines for the app; provider credentials stay on the server."""
from datetime import datetime, timezone
import json
import math
import os
import re
import secrets
import threading
import time
from urllib.parse import urlencode, parse_qs
from urllib.request import Request
from urllib.error import HTTPError, URLError
from .report_sources import read_json_response

SPORTS = {'americanfootball_nfl', 'americanfootball_ncaaf', 'basketball_nba',
          'basketball_ncaab', 'icehockey_nhl', 'baseball_mlb'}
MARKETS = {'h2h', 'spreads', 'totals'}
ALTERNATE_MARKETS = ('alternate_spreads', 'alternate_totals')
ALTERNATE_ROUTES = {'/api/odds/alternates'}
BOOKS = {'fanduel', 'draftkings'}
MAX_AGE = 900
MAX_CLOCK_SKEW = 60
MAIN_LOOKUP_CREDITS = 1
ALTERNATE_LOOKUP_CREDITS = 2
MAX_ALTERNATE_OUTCOMES = 128
MAX_ALTERNATE_QUOTES = 256
EVENT_ID_RE = re.compile(r'[A-Za-z0-9_-]{1,100}')


def stamp(value):
    if not isinstance(value, str): raise ValueError('Timestamp required')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None: raise ValueError('Timezone required')
    return dt.timestamp()


def valid_event_id(value):
    if not isinstance(value, str) or not EVENT_ID_RE.fullmatch(value):
        raise ValueError('Invalid provider event ID')
    return value


def pair_opposing_quotes(quotes):
    """Pair de-vig inputs only for complete opposing outcomes of the same book/event/market/threshold."""
    if not isinstance(quotes, list):
        raise ValueError('Quotes list required')
    buckets = {}
    for q in quotes:
        try:
            key = (q['eventId'], q['sport'], q['bookmakerKey'], q['market'],
                   q['updatedAt'], q['outcome'], q['point'])
            buckets.setdefault(key, []).append(q)
        except (KeyError, TypeError):
            continue
    paired = []
    for q in quotes:
        item = dict(q)
        market = item.get('market')
        outcome = item.get('outcome')
        point = item.get('point')
        home = item.get('homeTeam')
        away = item.get('awayTeam')
        opp_outcome = None
        opp_point = None
        if market in {'spreads', 'alternate_spreads'}:
            if type(point) in (int, float) and math.isfinite(point):
                opp_point = 0 if -point == 0 else -point
                if outcome == home:
                    opp_outcome = away
                elif outcome == away:
                    opp_outcome = home
        elif market in {'totals', 'alternate_totals'}:
            if type(point) in (int, float) and math.isfinite(point) and point > 0:
                opp_point = point
                if outcome == 'Over':
                    opp_outcome = 'Under'
                elif outcome == 'Under':
                    opp_outcome = 'Over'
        elif market == 'h2h' and point is None:
            if outcome == home:
                opp_outcome = away
            elif outcome == away:
                opp_outcome = home
        matches = buckets.get((item.get('eventId'), item.get('sport'), item.get('bookmakerKey'),
                               market, item.get('updatedAt'), opp_outcome, opp_point), []) if opp_outcome else []
        item['opposingAmericanOdds'] = matches[0]['americanOdds'] if len(matches) == 1 else None
        if point is not None and type(point) in (int, float) and math.isfinite(point):
            item['pushPossible'] = float(point).is_integer()
        paired.append(item)
    return paired


def normalize(events, sport, market, now):
    if not isinstance(events, list): raise ValueError('Invalid provider response')
    quotes=[]; upcoming=0
    for event in events:
        try:
            event_id=event['id']; start=event['commence_time']
            home=event['home_team']; away=event['away_team']
            if not all(isinstance(x,str) and 0<len(x)<=200 for x in (event_id,home,away)): continue
            if event.get('sport_key')!=sport or stamp(start)<=now: continue
            if upcoming>=100: break
            upcoming+=1
            for book in event.get('bookmakers',[]):
                if book.get('key') not in BOOKS: continue
                for m in book.get('markets',[]):
                    if m.get('key')!=market: continue
                    updated=m.get('last_update',book.get('last_update'))
                    age=now-stamp(updated)
                    if not -MAX_CLOCK_SKEW<=age<=MAX_AGE: continue
                    for outcome in m.get('outcomes',[]):
                        price=outcome.get('price'); label=outcome.get('name'); point=outcome.get('point')
                        outcome_name=label
                        if type(price) is not int or not 100<=abs(price)<=100000: continue
                        if not isinstance(label,str) or not 0<len(label)<=200: continue
                        if market in {'spreads','totals'}:
                            if type(point) not in (int,float) or not math.isfinite(point) or not -1000<=point<=1000: continue
                            if market=='totals' and (point<=0 or label not in {'Over','Under'}): continue
                            point=0 if point==0 else point
                            label=f'{label} {point:+g}' if market=='spreads' else f'{label} {point:g}'
                        quotes.append({'id':f'{event_id}:{book["key"]}:{market}:{label}',
                            'eventId':event_id,'event':f'{away} at {home}', 'startAt':start,
                            'sport':sport,'market':market,'label':label,'americanOdds':str(price),
                            'bookmaker':str(book.get('title',book['key']))[:100],
                            'bookmakerKey':book['key'], 'homeTeam':home, 'awayTeam':away,
                            'outcome':outcome_name, 'point':point if market in {'spreads','totals'} else None,
                            'updatedAt':updated,'fetchedAt':datetime.fromtimestamp(now,timezone.utc).isoformat()})
        except (KeyError,TypeError,ValueError,AttributeError):
            continue
    return quotes


def normalize_alternates(data, sport, event_id, now):
    if sport not in SPORTS:
        raise ValueError('Unsupported sport')
    valid_event_id(event_id)
    if isinstance(data, list):
        if len(data) != 1 or not isinstance(data[0], dict):
            raise ValueError('Invalid or ambiguous provider event response')
        event = data[0]
    elif isinstance(data, dict):
        event = data
    else:
        raise ValueError('Invalid provider event response')
    actual_id = event.get('id')
    actual_sport = event.get('sport_key')
    start = event.get('commence_time')
    home = event.get('home_team')
    away = event.get('away_team')
    bookmakers = event.get('bookmakers', [])
    if (actual_id != event_id or actual_sport != sport
            or not all(isinstance(x, str) and 0 < len(x.strip()) <= 200 for x in (actual_id, home, away))
            or home.strip() == away.strip() or not isinstance(bookmakers, list)):
        raise ValueError('Conflicting or invalid provider event identity')
    start_ts = stamp(start)
    if start_ts <= now:
        return []
    book_counts = {}
    for book in bookmakers:
        if not isinstance(book, dict):
            raise ValueError('Invalid bookmaker entry')
        bkey = book.get('key')
        if isinstance(bkey, str):
            book_counts[bkey] = book_counts.get(bkey, 0) + 1
    quotes = []
    fetched_iso = datetime.fromtimestamp(now, timezone.utc).isoformat()
    for book in bookmakers:
        book_key = book.get('key')
        if book_key not in BOOKS or book_counts.get(book_key, 0) != 1:
            continue
        markets = book.get('markets', [])
        if not isinstance(markets, list):
            continue
        market_counts = {}
        for m in markets:
            if isinstance(m, dict) and isinstance(m.get('key'), str):
                market_counts[m['key']] = market_counts.get(m['key'], 0) + 1
        for m in markets:
            if not isinstance(m, dict):
                continue
            market_key = m.get('key')
            if market_key not in ALTERNATE_MARKETS or market_counts.get(market_key, 0) != 1:
                continue
            try:
                updated = m.get('last_update', book.get('last_update'))
                age = now - stamp(updated)
            except (KeyError, TypeError, ValueError):
                continue
            if not -MAX_CLOCK_SKEW <= age <= MAX_AGE:
                continue
            outcomes = m.get('outcomes', [])
            if not isinstance(outcomes, list) or len(outcomes) > MAX_ALTERNATE_OUTCOMES:
                continue
            outcome_counts = {}
            for raw in outcomes:
                if not isinstance(raw, dict):
                    continue
                r_name = raw.get('name')
                r_pt = raw.get('point')
                if isinstance(r_name, str) and type(r_pt) in (int, float) and math.isfinite(r_pt):
                    norm_pt = 0 if r_pt == 0 else r_pt
                    outcome_counts[(r_name, norm_pt)] = outcome_counts.get((r_name, norm_pt), 0) + 1
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    continue
                price = outcome.get('price')
                outcome_name = outcome.get('name')
                point = outcome.get('point')
                if type(price) is not int or not 100 <= abs(price) <= 100000:
                    continue
                if not isinstance(outcome_name, str) or not 0 < len(outcome_name) <= 200:
                    continue
                if type(point) not in (int, float) or not math.isfinite(point) or not -1000 <= point <= 1000:
                    continue
                point = 0 if point == 0 else point
                if outcome_counts.get((outcome_name, point), 0) != 1:
                    continue
                if market_key == 'alternate_spreads':
                    if outcome_name not in {home, away}:
                        continue
                    point_text=str(int(point)) if float(point).is_integer() else str(point)
                    label=f'{outcome_name} {"+" if point>=0 else ""}{point_text}'
                else:
                    if point <= 0 or outcome_name not in {'Over', 'Under'}:
                        continue
                    point_text=str(int(point)) if float(point).is_integer() else str(point)
                    label=f'{outcome_name} {point_text}'
                if len(quotes) >= MAX_ALTERNATE_QUOTES:
                    break
                quotes.append({
                    'id': f'{event_id}:{book_key}:{market_key}:{label}',
                    'eventId': event_id,
                    'event': f'{away} at {home}',
                    'startAt': start,
                    'sport': sport,
                    'market': market_key,
                    'label': label,
                    'americanOdds': str(price),
                    'bookmaker': str(book.get('title', book_key))[:100],
                    'bookmakerKey': book_key,
                    'homeTeam': home,
                    'awayTeam': away,
                    'outcome': outcome_name,
                    'point': point,
                    'updatedAt': updated,
                    'fetchedAt': fetched_iso,
                })
    return pair_opposing_quotes(quotes)


def _comparison_boundary():
    return {
        'status': 'insufficient_data',
        'recommendation': 'no_supported_edge',
        'estimatedWinProbability': None,
        'offeredParlayDecimalPrice': None,
        'supportedEdge': None,
        'dependencies': [
            'push_void_settlement_rules',
            'calibrated_joint_forecast',
            'offered_combined_parlay_price',
        ],
    }


class OddsService:
    def __init__(self, key, fetch=None, clock=time.time, daily_limit=10):
        self.key=key; self.fetch=fetch or self._fetch; self.clock=clock
        self.daily_limit=daily_limit; self.cache={}; self.day=None; self.calls=0; self.credits=0
        self.lock=threading.Lock()

    def _fetch(self, route, params, timeout=15, limit=4*1024*1024):
        if not self.key: raise RuntimeError('Game data is not connected yet.')
        query=urlencode(dict(params,apiKey=self.key))
        try:
            request=Request('https://api.the-odds-api.com/v4/'+route+'?'+query,
                            headers={'Accept':'application/json'})
            return read_json_response(request, timeout, limit)
        except HTTPError as error:
            raise RuntimeError(f'Odds provider returned HTTP {error.code}.') from None
        except URLError as error:
            raise RuntimeError('Odds provider connection failed ('+type(error.reason).__name__+').') from None
        except Exception:
            # Never expose upstream request URLs (which contain the secret key).
            raise RuntimeError('Game data is temporarily unavailable. Try again later.') from None

    def _reserve_credits(self, now, cost):
        day = int(now // 86400)
        if self.day != day:
            self.day = day
            self.credits = 0
            self.calls = 0
        if self.credits + cost > self.daily_limit:
            raise RuntimeError('The testing data allowance is reached. Try again tomorrow.')
        self.credits += cost
        self.calls = self.credits

    def _check_identity_consistency(self, sport, event_id, home, away, start_ts):
        for cache_key, (cached_at, cached_val) in self.cache.items():
            if not 0 <= self.clock() - cached_at < 300:
                continue
            if not isinstance(cached_val, dict):
                continue
            for q in cached_val.get('quotes', []):
                if q.get('sport') == sport and q.get('eventId') == event_id and -MAX_CLOCK_SKEW <= self.clock()-stamp(q['updatedAt']) <= MAX_AGE and stamp(q['startAt'])>self.clock():
                    if (q.get('homeTeam') != home or q.get('awayTeam') != away
                            or stamp(q.get('startAt')) != start_ts):
                        raise RuntimeError('Conflicting provider event data.')

    def get(self, sport=None, market='h2h', timeout=None):
        if sport is not None and (sport not in SPORTS or market not in MARKETS):
            raise ValueError('Unsupported sport or market')
        deadline=None if timeout is None else time.monotonic()+max(0,timeout)
        acquired=self.lock.acquire() if timeout is None else self.lock.acquire(timeout=max(0,timeout))
        if not acquired:raise RuntimeError('Game data is busy. Try again shortly.')
        def fetch(route, params):
            remaining=15 if deadline is None else min(15,deadline-time.monotonic())
            if remaining<=0:raise RuntimeError('Game data request budget exhausted.')
            # Injected fetchers are trusted adapters and must honor their own I/O bounds.
            return self._fetch(route,params,timeout=remaining) if self.fetch==self._fetch else self.fetch(route,params)
        try:
            now=self.clock(); key=(sport,market)
            cached=self.cache.get(key)
            ttl=10800 if sport is None else 300
            if cached and 0<=now-cached[0]<ttl:
                result=cached[1]
                if sport is None:return result
                # Filter again as quotes age or a game starts while cached.
                return dict(result,quotes=[q for q in result['quotes']
                    if -MAX_CLOCK_SKEW<=now-stamp(q['updatedAt'])<=MAX_AGE and stamp(q['startAt'])>now])
            if sport is None:
                data=fetch('sports',{})
                if not isinstance(data,list):raise RuntimeError('Invalid sport list')
                result={'sports':[{'key':s['key'],'title':s['title']} for s in data
                    if isinstance(s,dict) and s.get('key') in SPORTS and s.get('active') is True
                    and isinstance(s.get('title'),str)]}
            else:
                self._reserve_credits(now, MAIN_LOOKUP_CREDITS)
                data=fetch(f'sports/{sport}/odds',{'regions':'us','markets':market,
                    'bookmakers':','.join(sorted(BOOKS)),'oddsFormat':'american','dateFormat':'iso'})
                result={'provider':'The Odds API','quotes':normalize(data,sport,market,now),
                    'fetchedAt':datetime.fromtimestamp(now,timezone.utc).isoformat(),
                    'refreshSeconds':300,'maxQuoteAgeSeconds':MAX_AGE}
            self.cache[key]=(now,result)
            return result
        finally:
            self.lock.release()

    def get_alternates(self, sport, event_id, timeout=None):
        if sport not in SPORTS:
            raise ValueError('Unsupported sport')
        if isinstance(event_id, str):
            valid_event_id(event_id)
            event_ids = [event_id]
            single = True
        elif isinstance(event_id, (list, tuple)) and 1 <= len(event_id) <= 8:
            event_ids = []
            for item in event_id:
                valid_event_id(item)
                if item not in event_ids:
                    event_ids.append(item)
            if len(event_ids) > 4:
                raise ValueError('Keep to four distinct events per request')
            single = len(event_ids) == 1
        else:
            raise ValueError('Invalid provider event ID')
        deadline = None if timeout is None else time.monotonic() + max(0, timeout)
        acquired = self.lock.acquire() if timeout is None else self.lock.acquire(timeout=max(0, timeout))
        if not acquired:
            raise RuntimeError('Game data is busy. Try again shortly.')
        def fetch(route, params):
            remaining = 15 if deadline is None else min(15, deadline - time.monotonic())
            if remaining <= 0:
                raise RuntimeError('Game data request budget exhausted.')
            return self._fetch(route, params, timeout=remaining, limit=1024*1024) if self.fetch == self._fetch else self.fetch(route, params)
        try:
            now = self.clock()
            per_event = []
            # Expired event caches cannot block reschedules indefinitely; keep memory bounded.
            for old_key, (created, _) in list(self.cache.items()):
                if old_key[0] == 'alternates' and not 0 <= now-created < 300:
                    del self.cache[old_key]
            for eid in event_ids:
                now = self.clock()
                cache_key = ('alternates', sport, eid)
                cached = self.cache.get(cache_key)
                if cached and 0 <= now - cached[0] < 300:
                    base = cached[1]
                    fresh = [q for q in base['quotes']
                             if -MAX_CLOCK_SKEW <= now - stamp(q['updatedAt']) <= MAX_AGE and stamp(q['startAt']) > now]
                    if fresh:
                        q=fresh[0]
                        self._check_identity_consistency(sport,eid,q['homeTeam'],q['awayTeam'],stamp(q['startAt']))
                    per_event.append(dict(base, quotes=pair_opposing_quotes(fresh)))
                    continue
                self._reserve_credits(now, ALTERNATE_LOOKUP_CREDITS)
                data = fetch(f'sports/{sport}/events/{eid}/odds', {
                    'regions': 'us',
                    'markets': ','.join(ALTERNATE_MARKETS),
                    'bookmakers': ','.join(sorted(BOOKS)),
                    'oddsFormat': 'american',
                    'dateFormat': 'iso',
                })
                if deadline is not None and time.monotonic() >= deadline:
                    raise RuntimeError('Game data request budget exhausted.')
                now = self.clock()
                try:
                    raw_event = data[0] if isinstance(data, list) and len(data) == 1 else data
                    if isinstance(raw_event, dict) and all(k in raw_event for k in ('home_team', 'away_team', 'commence_time')):
                        self._check_identity_consistency(
                            sport, eid, raw_event['home_team'], raw_event['away_team'], stamp(raw_event['commence_time']))
                    quotes = normalize_alternates(data, sport, eid, now)
                except ValueError:
                    raise RuntimeError('Invalid provider event response.') from None
                item = {
                    'provider': 'The Odds API',
                    'sport': sport,
                    'eventId': eid,
                    'markets': list(ALTERNATE_MARKETS),
                    'quotes': quotes,
                    'fetchedAt': datetime.fromtimestamp(now, timezone.utc).isoformat(),
                    'refreshSeconds': 300,
                    'maxQuoteAgeSeconds': MAX_AGE,
                    'comparison': _comparison_boundary(),
                }
                if cache_key not in self.cache and len(self.cache)>=64:
                    victim=next((k for k in self.cache if k[0]=='alternates'),None)
                    if victim is not None:del self.cache[victim]
                self.cache[cache_key] = (now, item)
                per_event.append(item)
            completed = self.clock()
            per_event = [dict(item, quotes=pair_opposing_quotes([q for q in item['quotes']
                if -MAX_CLOCK_SKEW <= completed-stamp(q['updatedAt']) <= MAX_AGE and stamp(q['startAt'])>completed])) for item in per_event]
            if single:
                return per_event[0]
            combined_quotes = []
            for item in per_event:
                combined_quotes.extend(item['quotes'])
            return {
                'provider': 'The Odds API',
                'sport': sport,
                'eventIds': event_ids,
                'markets': list(ALTERNATE_MARKETS),
                'events': per_event,
                'quotes': combined_quotes,
                'fetchedAt': datetime.fromtimestamp(now, timezone.utc).isoformat(),
                'refreshSeconds': 300,
                'maxQuoteAgeSeconds': MAX_AGE,
                'comparison': _comparison_boundary(),
            }
        finally:
            self.lock.release()


service=OddsService(os.environ.get('ODDS_API_KEY',''))
report_service=None
report_init_lock=threading.Lock()

def game_reports():
    global report_service
    if report_service is None:
        with report_init_lock:
            if report_service is None:
                from .game_reports import ReportService
                report_service=ReportService(service)
    return report_service

def application(environ,start_response):
    status='200 OK'; result={}
    try:
        if environ.get('PATH_INFO')=='/health':result={'status':'ok'}
        else:
            expected=os.environ.get('ODDS_PREVIEW_TOKEN','')
            supplied=environ.get('HTTP_AUTHORIZATION','')
            if not expected or not secrets.compare_digest(supplied.encode('utf8'),('Bearer '+expected).encode('utf8')):
                start_response('401 Unauthorized',[('Content-Type','application/json'),('Cache-Control','no-store')])
                return [b'{"error":"Preview access required"}']
            if environ.get('PATH_INFO')=='/api/game-reports':
                return report_application(environ,start_response)
            if environ.get('REQUEST_METHOD')!='GET':raise ValueError('GET required')
            raw_query=environ.get('QUERY_STRING','')
            if len(raw_query)>1024:raise ValueError('Query exceeds limit')
            route=environ.get('PATH_INFO'); query=parse_qs(raw_query,keep_blank_values=True)
            if route=='/api/sports':result=service.get()
            elif route=='/api/odds':result=service.get(query.get('sport',[''])[0],query.get('market',['h2h'])[0])
            elif route in ALTERNATE_ROUTES:
                if set(query)-{'sport','eventId'}:raise ValueError('Unsupported query parameter')
                sports=query.get('sport',[]);ids=query.get('eventId',[])
                if len(sports)!=1 or not 1<=len(ids)<=8:raise ValueError('Sport and eventId required')
                result=service.get_alternates(sports[0],ids[0] if len(ids)==1 else ids,timeout=20)
            else:status='404 Not Found';result={'error':'Not found'}
    except ValueError:status='400 Bad Request';result={'error':'Choose a supported sport and market.'}
    except Exception as error:
        status='503 Service Unavailable'
        result={'error':str(error) if isinstance(error,RuntimeError) else 'Game data is temporarily unavailable.'}
    encoded=json.dumps(result,allow_nan=False).encode()
    if len(encoded)>262144:
        status='503 Service Unavailable';encoded=b'{"error":"Game data exceeds response limit."}'
    start_response(status,[('Content-Type','application/json'),('Cache-Control','no-store')])
    return [encoded]


def report_application(environ,start_response):
    from .game_reports import MAX_BODY, ReportBusy
    from .report_sources import strict_json
    status='200 OK'
    headers=[('Content-Type','application/json'),('Cache-Control','no-store')]
    try:
        if environ.get('REQUEST_METHOD')!='POST':
            status='405 Method Not Allowed';headers.append(('Allow','POST'))
            result={'error':'Use POST for game reports.'}
        elif environ.get('CONTENT_TYPE','').split(';')[0].strip().lower()!='application/json':
            status='415 Unsupported Media Type';result={'error':'JSON required.'}
        else:
            length=environ.get('CONTENT_LENGTH','')
            if not length.isascii() or not length.isdecimal() or len(length)>8:
                raise ValueError('Content length required')
            size=int(length)
            if not 0<size<=MAX_BODY:
                status='413 Payload Too Large';result={'error':'Report input exceeds size limit.'}
            else:
                raw=environ['wsgi.input'].read(size)
                if len(raw)!=size:raise ValueError('Incomplete body')
                result=game_reports().build(strict_json(raw))
    except ReportBusy:
        status='429 Too Many Requests';headers.append(('Retry-After','5'))
        result={'error':'The preview report service is busy. Try again shortly.'}
    except (ValueError,TypeError,KeyError,RecursionError,UnicodeError,OverflowError):
        status='400 Bad Request';result={'error':'Check the structured legs, stake and report input limits.'}
    except Exception:
        status='503 Service Unavailable';result={'error':'Game reports are temporarily unavailable.'}
    encoded=json.dumps(result,allow_nan=False).encode()
    if len(encoded)>262144:
        status='503 Service Unavailable';encoded=b'{"error":"Report exceeds response limit."}'
    headers.append(('Content-Length',str(len(encoded))))
    start_response(status,headers)
    return [encoded]
