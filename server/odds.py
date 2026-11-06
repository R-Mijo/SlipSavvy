"""Curated pregame lines for the app; provider credentials stay on the server."""
from datetime import datetime, timezone
import json
import os
import secrets
import threading
import time
from urllib.parse import urlencode, parse_qs
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

SPORTS = {'americanfootball_nfl', 'americanfootball_ncaaf', 'basketball_nba',
          'basketball_ncaab', 'icehockey_nhl', 'baseball_mlb'}
MARKETS = {'h2h', 'spreads', 'totals'}
BOOKS = {'fanduel', 'draftkings'}
MAX_AGE = 900
MAX_CLOCK_SKEW = 60

def stamp(value):
    if not isinstance(value, str): raise ValueError('Timestamp required')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None: raise ValueError('Timezone required')
    return dt.timestamp()

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
                        if type(price) is not int or not 100<=abs(price)<=100000: continue
                        if not isinstance(label,str) or not 0<len(label)<=200: continue
                        if market in {'spreads','totals'}:
                            if type(point) not in (int,float) or not -1000<=point<=1000: continue
                            if market=='totals' and (point<=0 or label not in {'Over','Under'}): continue
                            point=0 if point==0 else point
                            label=f'{label} {point:+g}' if market=='spreads' else f'{label} {point:g}'
                        quotes.append({'id':f'{event_id}:{book["key"]}:{market}:{label}',
                            'eventId':event_id,'event':f'{away} at {home}', 'startAt':start,
                            'sport':sport,'market':market,'label':label,'americanOdds':str(price),
                            'bookmaker':str(book.get('title',book['key']))[:100],
                            'updatedAt':updated,'fetchedAt':datetime.fromtimestamp(now,timezone.utc).isoformat()})
        except (KeyError,TypeError,ValueError,AttributeError):
            continue
    return quotes

class OddsService:
    def __init__(self, key, fetch=None, clock=time.time, daily_limit=10):
        self.key=key; self.fetch=fetch or self._fetch; self.clock=clock
        self.daily_limit=daily_limit; self.cache={}; self.day=None; self.calls=0
        self.lock=threading.Lock()
    def _fetch(self, route, params):
        if not self.key: raise RuntimeError('Game data is not connected yet.')
        query=urlencode(dict(params,apiKey=self.key))
        try:
            request=Request('https://api.the-odds-api.com/v4/'+route+'?'+query,
                            headers={'Accept':'application/json'})
            with urlopen(request,timeout=15) as response:
                data=response.read(4*1024*1024+1)
                if len(data)>4*1024*1024: raise ValueError('Response too large')
                return json.loads(data)
        except HTTPError as error:
            raise RuntimeError(f'Odds provider returned HTTP {error.code}.') from None
        except URLError as error:
            raise RuntimeError('Odds provider connection failed ('+type(error.reason).__name__+').') from None
        except Exception:
            # Never expose upstream request URLs (which contain the secret key).
            raise RuntimeError('Game data is temporarily unavailable. Try again later.') from None
    def get(self, sport=None, market='h2h'):
        if sport is not None and (sport not in SPORTS or market not in MARKETS):
            raise ValueError('Unsupported sport or market')
        with self.lock:
            now=self.clock(); key=(sport,market)
            cached=self.cache.get(key)
            ttl=10800 if sport is None else 300
            if cached and now-cached[0]<ttl:
                result=cached[1]
                if sport is None:return result
                # Filter again as quotes age or a game starts while cached.
                return dict(result,quotes=[q for q in result['quotes']
                    if -MAX_CLOCK_SKEW<=now-stamp(q['updatedAt'])<=MAX_AGE and stamp(q['startAt'])>now])
            if sport is None:
                data=self.fetch('sports',{})
                if not isinstance(data,list):raise RuntimeError('Invalid sport list')
                result={'sports':[{'key':s['key'],'title':s['title']} for s in data
                    if isinstance(s,dict) and s.get('key') in SPORTS and s.get('active') is True
                    and isinstance(s.get('title'),str)]}
            else:
                day=int(now//86400)
                if self.day!=day:self.day=day;self.calls=0
                if self.calls>=self.daily_limit:
                    raise RuntimeError('The testing data allowance is reached. Try again tomorrow.')
                self.calls+=1  # Reserve attempts, including unsuccessful calls.
                data=self.fetch(f'sports/{sport}/odds',{'regions':'us','markets':market,
                    'bookmakers':','.join(sorted(BOOKS)),'oddsFormat':'american','dateFormat':'iso'})
                result={'provider':'The Odds API','quotes':normalize(data,sport,market,now),
                    'fetchedAt':datetime.fromtimestamp(now,timezone.utc).isoformat(),
                    'refreshSeconds':300,'maxQuoteAgeSeconds':MAX_AGE}
            self.cache[key]=(now,result)
            return result

service=OddsService(os.environ.get('ODDS_API_KEY',''))

def application(environ,start_response):
    status='200 OK'; result={}
    try:
        if environ.get('PATH_INFO')=='/health':result={'status':'ok'}
        else:
            expected=os.environ.get('ODDS_PREVIEW_TOKEN','')
            supplied=environ.get('HTTP_AUTHORIZATION','')
            if not expected or not secrets.compare_digest(supplied,'Bearer '+expected):
                start_response('401 Unauthorized',[('Content-Type','application/json')])
                return [b'{"error":"Preview access required"}']
            if environ.get('REQUEST_METHOD')!='GET':raise ValueError('GET required')
            route=environ.get('PATH_INFO'); query=parse_qs(environ.get('QUERY_STRING',''))
            if route=='/api/sports':result=service.get()
            elif route=='/api/odds':result=service.get(query.get('sport',[''])[0],query.get('market',['h2h'])[0])
            else:status='404 Not Found';result={'error':'Not found'}
    except ValueError:status='400 Bad Request';result={'error':'Choose a supported sport and market.'}
    except Exception as error:
        status='503 Service Unavailable'
        result={'error':str(error) if isinstance(error,RuntimeError) else 'Game data is temporarily unavailable.'}
    start_response(status,[('Content-Type','application/json'),('Cache-Control','no-store')])
    return [json.dumps(result).encode()]
