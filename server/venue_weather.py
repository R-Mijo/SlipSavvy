"""Event-specific venue matches and free NWS hourly forecasts; no probability changes."""
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from urllib.request import Request

from .report_sources import finite, iso, public_url, read_json_response, strict_json, text, timestamp


def missing(reason):
    return {'status':'unavailable','reason':reason}


class VenueCatalog:
    """Small reviewed directory, matched by BOTH source stadium ID and exact name.

    Never maps a team to its usual home stadium; source roof strings are ignored.
    """
    def __init__(self, path=None):
        self.path=Path(path) if path else Path(__file__).with_name('venue_catalog.json')

    def lookup(self,event,research,now):
        mapping=research.get('mapping') if isinstance(research,dict) else None
        if (not mapping or mapping.get('status')!='matched' or event.get('sport')!='americanfootball_nfl'
                or timestamp(mapping['startAt'])!=timestamp(event['startAt'])):
            return missing('event_venue_evidence_required')
        schedule=[s for s in research.get('sources',[]) if s.get('dataset')=='schedule' and timestamp(s['validUntil'])>now]
        if len(schedule)!=1:
            return missing('schedule_venue_evidence_unavailable')
        raw=mapping.get('reportedVenue')
        if not isinstance(raw,dict) or not raw.get('id') or not raw.get('name'):
            return missing('schedule_venue_missing')
        with self.path.open('rb') as stream:raw_catalog=stream.read(65537)
        if len(raw_catalog)>65536:raise ValueError('Venue catalog exceeds limit')
        data=strict_json(raw_catalog)
        if data.get('schemaVersion')!=1 or not isinstance(data.get('venues'),list) or len(data['venues'])>64:
            raise ValueError('Invalid venue catalog')
        matches=[v for v in data['venues'] if v.get('stadiumId')==raw['id'] and raw['name'] in v.get('names',[])]
        if len(matches)!=1:
            return missing('venue_not_in_verified_catalog' if not matches else 'ambiguous_venue_catalog')
        v=matches[0];checked=timestamp(v['checkedAt']);until=timestamp(v['validUntil'])
        start=timestamp(event['startAt'])
        if not -60<=now-checked<=30*86400 or not now<until<=checked+30*86400 or not checked<=start<until:
            return missing('venue_catalog_expired')
        roof=v['roof']
        if roof not in {'outdoor','indoor','retractable'}:
            raise ValueError('Invalid venue roof')
        sources=[]
        for s in v['sources']:
            if s['kind'] not in {'roof','coordinates'}:
                raise ValueError('Invalid venue evidence')
            sources.append({'kind':s['kind'],'url':public_url(s['url']),'publisher':text(s['publisher'],100)})
        if not 1<=len(sources)<=4 or not any(s['kind']=='roof' for s in sources):
            raise ValueError('Venue roof source required')
        lat,lon=v.get('latitude'),v.get('longitude')
        if roof=='outdoor':
            lat,lon=finite(lat,-90,90),finite(lon,-180,180)
            if not any(s['kind']=='coordinates' for s in sources):
                raise ValueError('Coordinate source required')
        else:
            lat=lon=None  # No weather lookup for unknown retractable state / fixed indoor roof.
        return {'status':'matched_catalog','name':text(v['name'],150),'stadiumId':text(v['stadiumId'],40),
                'roof':roof,'roofState':'unknown','latitude':lat,'longitude':lon,
                'checkedAt':iso(checked),'validUntil':iso(min(until,timestamp(schedule[0]['validUntil']))),
                'sources':sources,'scheduleSourceId':schedule[0]['id'],
                'basis':'exact_event_schedule_and_reviewed_venue_catalog'}


def nws_url(value,kind):
    if not isinstance(value,str):raise ValueError('Invalid NWS URL')
    u=urlsplit(value)
    patterns={'point':r'/points/-?\d{1,2}\.\d{1,4},-?\d{1,3}\.\d{1,4}',
              'hourly':r'/gridpoints/[A-Z]{3}/-?\d{1,4},-?\d{1,4}/forecast/hourly'}
    if (u.scheme!='https' or u.netloc!='api.weather.gov' or u.query or u.fragment
            or not re.fullmatch(patterns[kind],u.path)):
        raise ValueError('NWS URL rejected')
    return value


def quantitative(value,unit,low,high):
    if not isinstance(value,dict) or value.get('unitCode')!=unit or value.get('value') is None:
        return None
    try:return finite(value['value'],low,high)
    except ValueError:return None


def wind(value):
    if isinstance(value,dict):
        units={'wmoUnit:km_h':1/1.609344,'wmoUnit:m_s':2.2369362920544,'wmoUnit:mi_h':1}
        if value.get('unitCode') not in units or type(value.get('value')) not in (int,float):return None,None
        try:return finite(value['value']*units[value['unitCode']],0,250),None
        except (TypeError,ValueError):return None,None
    if not isinstance(value,str):return None,None
    m=re.fullmatch(r'(\d{1,3})(?: to (\d{1,3}))? mph',value)
    if not m:return None,None
    try:
        low=finite(int(m[1]),0,250);high=finite(int(m[2]),low,250) if m[2] else low
    except ValueError:return None,None
    return (low,None) if low==high else (None,{'low':low,'high':high})


class NwsWeather:
    def __init__(self,fetch=None,clock=time.time,monotonic=time.monotonic,mode='nws'):
        self.fetch=fetch or self._fetch;self.clock=clock;self.monotonic=monotonic;self.mode=mode

    def _fetch(self,url,timeout):
        request=Request(url,headers={'User-Agent':'SlipSavvy (https://github.com/R-Mijo/SlipSavvy)',
                                     'Accept':'application/geo+json'})
        return read_json_response(request,min(5,timeout),524288)

    def get(self,event,venue,now,timeout):
        if self.mode!='nws':return missing('weather_disabled')
        start=timestamp(event['startAt'])
        if not now<start<now+7*86400:return missing('outside_forecast_window')
        deadline=self.monotonic()+max(0,timeout)
        lat,lon=finite(venue['latitude'],-90,90),finite(venue['longitude'],-180,180)
        point=nws_url(f'https://api.weather.gov/points/{lat:.4f},{lon:.4f}','point')
        def get(url):
            left=deadline-self.monotonic()
            if left<=0:raise TimeoutError('Weather budget exhausted')
            return self.fetch(url,min(5,left))
        try:
            p=get(point)
            coords=p['geometry']['coordinates']
            if (p['geometry'].get('type')!='Point' or not isinstance(coords,list) or len(coords)!=2
                    or abs(finite(coords[0],-180,180)-lon)>.001 or abs(finite(coords[1],-90,90)-lat)>.001):
                raise ValueError('NWS point identity conflict')
            hourly=nws_url(p['properties']['forecastHourly'],'hourly')
            props=get(hourly)['properties']
            updated=timestamp(props['updateTime'])
            finished=self.clock()
            if not -60<=finished-updated<=21600:return missing('weather_forecast_stale')
            periods=props['periods']
            if not isinstance(periods,list) or not 1<=len(periods)<=200:
                raise ValueError('Invalid weather periods')
            matches=[]
            for period in periods:
                a,b=timestamp(period['startTime']),timestamp(period['endTime'])
                if a<=start<b:
                    if not 0<b-a<=3601:raise ValueError('Hourly period required')
                    matches.append(period)
            if len(matches)!=1:return missing('kickoff_hour_unavailable')
            hour=matches[0]
            temperature=hour.get('temperature')
            if isinstance(temperature,dict):
                if temperature.get('unitCode')=='wmoUnit:degF':temperature=quantitative(temperature,'wmoUnit:degF',-150,160)
                else:
                    temperature=quantitative(temperature,'wmoUnit:degC',-101,72)
                    temperature=None if temperature is None else temperature*9/5+32
            else:
                try:
                    temperature=finite(temperature,-150,160) if hour.get('temperatureUnit')=='F' else finite(temperature,-101,72)*9/5+32 if hour.get('temperatureUnit')=='C' else None
                except ValueError:temperature=None
            speed,interval=wind(hour.get('windSpeed'))
            if temperature is not None:
                try:temperature=finite(temperature,-150,160)
                except ValueError:temperature=None
            gust,_=wind(hour.get('windGust'))
            values={'temperatureF':temperature,'precipitationChance':quantitative(hour.get('probabilityOfPrecipitation'),'wmoUnit:percent',0,100),
                    'windSpeedMph':speed,'windGustMph':gust}
            missing_fields=[key for key,value in values.items() if value is None and not (key=='windSpeedMph' and interval)]
            if len(missing_fields)==4:return missing('weather_values_unavailable')
            if self.monotonic()>=deadline or start<=finished:return missing('weather_expired_during_report')
            return {'status':'available','provider':'NWS','kind':'forecast','coverage':'partial' if missing_fields else 'available',
                    'sourceUrl':hourly,'pointSourceUrl':point,'attribution':'National Weather Service / NOAA',
                    'licenseUrl':'https://www.weather.gov/disclaimer','providerUpdatedAt':iso(updated),'retrievedAt':iso(finished),
                    'validUntil':iso(min(updated+21600,finished+300)),'hourAt':iso(timestamp(hour['startTime'])),
                    'hourUntil':iso(timestamp(hour['endTime'])),'values':values,'windRangeMph':interval,
                    'missingFields':missing_fields,'units':{'temperatureF':'°F','precipitationChance':'%','windSpeedMph':'mph','windGustMph':'mph'},
                    'note':'Kickoff-hour grid forecast, not a stadium observation or probability adjustment.'}
        except Exception:
            return missing('weather_provider_unavailable')
