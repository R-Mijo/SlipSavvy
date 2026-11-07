"""Server-owned evidence and opt-in weather adapters; never fetch client URLs."""
from datetime import datetime, timezone
import json
import math
import os
import re
import time
from urllib.parse import urlencode, urlsplit, parse_qsl
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


open_request = build_opener(NoRedirect()).open


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp required')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timezone required')
    return dt.timestamp()


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = item
        return result
    def constant(_):
        raise ValueError('Nonfinite JSON number')
    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)


def read_json_response(request, timeout, limit):
    """Cap bytes and elapsed reads; one in-progress socket read can take <=5s."""
    deadline = time.monotonic() + timeout
    with open_request(request, timeout=min(5, timeout)) as response:
        chunks, size = [], 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError('Provider read budget exhausted')
            chunk = response.read1(min(65536, limit + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError('Provider response too large')
            chunks.append(chunk)
    return strict_json(b''.join(chunks))


def text(value, maximum=280):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('Invalid text')
    return value.strip()


def finite(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid number')
    return value


def public_url(value):
    value = text(value, 1000)
    url = urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or any(re.search(r'key|token|secret|password|authorization', k, re.I)
                   for k, _ in parse_qsl(url.query))):
        raise ValueError('Public HTTPS evidence URL required')
    return value


class ContextCatalog:
    """Optional curated input, installed by the operator, never supplied in POSTs.

    References are provenance, not automated verification of semantic truth.
    No URLs in this catalog are fetched by the service.
    """
    def __init__(self, path=None):
        self.path = path if path is not None else os.environ.get('GAME_CONTEXT_FILE')

    def lookup(self, event, now):
        if not self.path:
            return {'status': 'unavailable', 'reason': 'context_not_configured',
                    'evidence': [], 'facts': [], 'venue': None, 'forecast': None}
        with open(self.path, 'rb') as source:
            raw = source.read(262145)
        if len(raw) > 262144:
            raise ValueError('Catalog too large')
        data = strict_json(raw)
        if data.get('schemaVersion') != 1 or not isinstance(data.get('events'), dict) or len(data['events']) > 128:
            raise ValueError('Invalid catalog')
        entry = data['events'].get(event['sport'] + ':' + event['eventId'])
        if entry is None:
            return {'status': 'unavailable', 'reason': 'context_not_found',
                    'evidence': [], 'facts': [], 'venue': None, 'forecast': None}
        if (not isinstance(entry, dict) or entry.get('homeTeam') != event['homeTeam']
                or entry.get('awayTeam') != event['awayTeam']
                or timestamp(entry.get('startAt')) != timestamp(event['startAt'])):
            raise ValueError('Context identity conflict')
        evidence = []
        records = entry.get('evidence', [])
        if not isinstance(records, list) or len(records) > 24:
            raise ValueError('Invalid evidence')
        seen = set()
        for item in records:
            try:
                kind = item['kind']
                age_limit = {'context': 21600, 'venue': 2592000, 'model_evaluation': 31536000}[kind]
                observed, until = timestamp(item['observedAt']), timestamp(item['validUntil'])
                identity = text(item['id'], 100)
                if not re.fullmatch(r'[A-Za-z0-9_-]+', identity):
                    raise ValueError('Invalid evidence ID')
                if identity in seen:
                    raise ValueError('Duplicate evidence')
                seen.add(identity)
                if not -60 <= now - observed <= age_limit or not now < until <= observed + age_limit:
                    continue
                evidence.append({'id': identity, 'kind': kind, 'url': public_url(item['url']),
                                 'publisher': text(item['publisher'], 100),
                                 'observedAt': iso(observed), 'validUntil': iso(until),
                                 'verification': 'operator_supplied_reference'})
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        ids = {e['id'] for e in evidence}
        facts = []
        raw_facts = entry.get('facts', [])
        if not isinstance(raw_facts, list) or len(raw_facts) > 8:
            raise ValueError('Invalid facts')
        for fact in raw_facts:
            try:
                refs = fact['evidenceIds']
                if not isinstance(refs, list) or not 1 <= len(refs) <= 24 or not set(refs) <= ids:
                    continue
                facts.append({'text': text(fact['text']), 'evidenceIds': refs})
            except (KeyError, TypeError, ValueError):
                continue
        venue = None
        raw_venue = entry.get('venue')
        if isinstance(raw_venue, dict):
            try:
                refs = raw_venue['evidenceIds']
                venue_ids = {e['id'] for e in evidence if e['kind'] == 'venue'}
                if not isinstance(refs, list) or not refs or not set(refs) <= venue_ids:
                    raise ValueError('Venue evidence required')
                roof = raw_venue['roof']
                if roof not in {'indoor', 'outdoor', 'retractable', 'unknown'}:
                    raise ValueError('Unknown roof')
                state, roof_refs = 'unknown', []
                if roof == 'retractable':
                    roof_refs = raw_venue.get('roofEvidenceIds', [])
                    context_ids = {e['id'] for e in evidence if e['kind'] == 'context'}
                    if (isinstance(roof_refs, list) and roof_refs and set(roof_refs) <= context_ids
                            and raw_venue.get('roofState') in {'open', 'closed'}):
                        state = raw_venue['roofState']
                    else:
                        roof_refs = []
                venue = {'name': text(raw_venue['name'], 150), 'roof': roof, 'roofState': state,
                         'latitude': finite(raw_venue['latitude'], -90, 90),
                         'longitude': finite(raw_venue['longitude'], -180, 180),
                         'evidenceIds': refs, 'roofEvidenceIds': roof_refs}
            except (KeyError, TypeError, ValueError):
                venue = None
        return {'status': 'available' if evidence else 'unavailable',
                'reason': None if evidence else 'no_fresh_evidence', 'evidence': evidence,
                'facts': facts, 'venue': venue, 'forecast': entry.get('forecast')}


class OpenMeteoWeather:
    """Disabled until an operator chooses an appropriate service/usage mode."""
    def __init__(self, mode=None, api_key=None, fetch=None):
        self.mode = mode if mode is not None else os.environ.get('REPORT_WEATHER_MODE', 'disabled')
        self.key = api_key if api_key is not None else os.environ.get('OPEN_METEO_API_KEY', '')
        self.fetch = fetch or self._fetch

    def _fetch(self, url, timeout):
        try:
            return read_json_response(Request(url, headers={'Accept': 'application/json'}), timeout, 262144)
        except Exception:
            # The commercial request URL contains a credential; never echo it.
            raise RuntimeError('Weather provider unavailable') from None

    def get(self, event, venue, now, timeout):
        if self.mode not in {'evaluation', 'commercial'} or (self.mode == 'commercial' and not self.key):
            return {'status': 'unavailable', 'reason': 'weather_not_configured'}
        if not now < timestamp(event['startAt']) < now + 6 * 86400:
            return {'status': 'unavailable', 'reason': 'outside_forecast_window'}
        host = 'customer-api.open-meteo.com' if self.mode == 'commercial' else 'api.open-meteo.com'
        params = {'latitude': venue['latitude'], 'longitude': venue['longitude'], 'timezone': 'UTC',
                  'hourly': 'temperature_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m',
                  'temperature_unit': 'fahrenheit', 'wind_speed_unit': 'mph', 'forecast_days': 7}
        public = 'https://' + host + '/v1/forecast?' + urlencode(params)
        url = public + ('&' + urlencode({'apikey': self.key}) if self.mode == 'commercial' else '')
        data = self.fetch(url, min(5, timeout))
        if data.get('utc_offset_seconds') != 0:
            raise ValueError('UTC weather required')
        hourly, units = data['hourly'], data['hourly_units']
        expected = {'temperature_2m': ('°F', -150, 160), 'precipitation_probability': ('%', 0, 100),
                    'wind_speed_10m': ('mp/h', 0, 250), 'wind_gusts_10m': ('mp/h', 0, 300)}
        times = hourly['time']
        if not isinstance(times, list) or len(times) > 200:
            raise ValueError('Invalid weather hours')
        start = timestamp(event['startAt'])
        matches = [i for i, t in enumerate(times)
                   if timestamp(t + '+00:00' if isinstance(t, str) and len(t) == 16 else t) <= start
                   < timestamp(t + '+00:00' if isinstance(t, str) and len(t) == 16 else t) + 3600]
        if len(matches) != 1:
            raise ValueError('Kickoff hour unavailable')
        index = matches[0]
        values = {}
        for key, (unit, low, high) in expected.items():
            if units.get(key) != unit or not isinstance(hourly.get(key), list) or len(hourly[key]) != len(times):
                raise ValueError('Invalid weather units or series')
            values[key] = finite(hourly[key][index], low, high)
        return {'status': 'available', 'kind': 'forecast', 'provider': 'Open-Meteo',
                'attribution': 'Weather data by Open-Meteo.com', 'sourceUrl': public,
                'licenseUrl': 'https://creativecommons.org/licenses/by/4.0/',
                'retrievedAt': iso(now), 'hourAt': times[index], 'timezone': 'UTC',
                'values': values, 'units': {k: v[0] for k, v in expected.items()},
                'note': 'Forecast, not observation; no automatic probability adjustment.'}
