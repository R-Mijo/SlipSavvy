"""Bounded, source-attributed per-leg reports. No inferred forecasts or wagers."""
from collections import OrderedDict, deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import os
import re
import threading
import time

from .report_sources import ContextCatalog, OpenMeteoWeather, finite, iso, text, timestamp

SEATS = ('Jeeves', 'Luna', 'Pax', 'Winston', 'Lisa', 'Diego', 'Gus')
MAX_BODY = 32768


class ReportBusy(RuntimeError):
    pass


def cash(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{1,8}(?:\.\d{1,2})?', value):
        raise ValueError('Use monetary strings with up to two decimals')
    result = Decimal(value)
    if not 0 < result <= 10000000:
        raise ValueError('Invalid amount')
    return format(result, '.2f')


def parse_request(data):
    from .odds import SPORTS, MARKETS, BOOKS, PROP_MARKETS, PROP_SPORT
    if not isinstance(data, dict) or set(data) - {'legs', 'totalStake', 'minimumTotalReturn'}:
        raise ValueError('Invalid report request')
    stake = cash(data.get('totalStake'))
    if Decimal(stake) > 10000:
        raise ValueError('Stake exceeds limit')
    floor = cash(data['minimumTotalReturn']) if 'minimumTotalReturn' in data else None
    legs = data.get('legs')
    if not isinstance(legs, list) or not 1 <= len(legs) <= 8:
        raise ValueError('Supply one to eight legs')
    result, ids, selections = [], set(), set()
    for leg in legs:
        if not isinstance(leg, dict) or set(leg) - {
                'id', 'eventId', 'sport', 'bookmaker', 'market', 'outcome', 'point', 'americanOdds', 'playerName'}:
            raise ValueError('Invalid leg fields')
        identity, event = text(leg.get('id'), 100), text(leg.get('eventId'), 100)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', event):
            raise ValueError('Invalid provider event ID')
        sport, book, market = leg.get('sport'), leg.get('bookmaker'), leg.get('market')
        if not all(isinstance(v, str) for v in (sport, book, market)) or sport not in SPORTS or book not in BOOKS or market not in MARKETS | set(PROP_MARKETS):
            raise ValueError('Unsupported sport, bookmaker or market')
        player = None
        if market in PROP_MARKETS:
            player = text(leg.get('playerName'), 120)
            if sport != PROP_SPORT or player != leg.get('playerName') or any(ord(c) < 32 for c in player):
                raise ValueError('Invalid provider player description')
        elif 'playerName' in leg:
            raise ValueError('Player identity only applies to props')
        outcome = text(leg.get('outcome'), 200)
        point = leg.get('point')
        if market == 'h2h':
            if point is not None:
                raise ValueError('Moneyline has no point')
        else:
            point = finite(point, -1000, 1000)
            point = 0 if point == 0 else point
            if market in {'totals', *PROP_MARKETS} and (point <= 0 or outcome not in {'Over', 'Under'}):
                raise ValueError('Invalid total')
        expected = leg.get('americanOdds')
        if expected is not None:
            if not isinstance(expected, str) or not re.fullmatch(r'[+-]?\d{3,6}', expected) or not 100 <= abs(int(expected)) <= 100000:
                raise ValueError('Invalid expected price')
            expected = str(int(expected))
        key = (sport, event, book, market, outcome, point, player)
        if identity in ids or key in selections:
            raise ValueError('Duplicate leg or selection')
        ids.add(identity); selections.add(key)
        result.append({'id': identity, 'eventId': event, 'sport': sport, 'bookmaker': book,
                       'market': market, 'outcome': outcome, 'point': point, 'americanOdds': expected,
                       **({'playerName': player} if player is not None else {})})
    if len({(l['sport'], l['eventId']) for l in result}) > 4 or len({(l['sport'], l['market']) for l in result}) > 4:
        raise ValueError('Keep to four events and four sport/market lookups per report')
    return {'legs': result, 'totalStake': stake, 'minimumTotalReturn': floor}


def selection_key(value):
    return value['market'], value['outcome'], value.get('point'), value.get('playerName')


def forecast_snapshot(context, event, now):
    """Validate an operator-owned model snapshot; never turn prices into a script."""
    unavailable = {'status': 'unavailable', 'reason': 'forecast_not_configured',
                   'mostLikelyScenarioId': None, 'scenarios': [], 'selections': []}
    raw = context.get('forecast')
    if raw is None:
        return unavailable
    try:
        generated, until = timestamp(raw['generatedAt']), timestamp(raw['validUntil'])
        if not -60 <= now - generated <= 3600 or not now < until <= timestamp(event['startAt']):
            raise ValueError('Stale forecast')
        evidence = {e['id']: e for e in context['evidence']}
        evaluation = raw['evaluationEvidenceId']
        if evidence[evaluation]['kind'] != 'model_evaluation':
            raise ValueError('Model evaluation reference required')
        scenarios = raw['scenarios']
        if not isinstance(scenarios, list) or not 2 <= len(scenarios) <= 6:
            raise ValueError('At least two model scenarios required')
        parsed, identities, weight = [], set(), Decimal(0)
        for scenario in scenarios:
            identity = text(scenario['id'], 80)
            probability = finite(scenario['probability'], 0, 1)
            refs = scenario['evidenceIds']
            if identity in identities or not isinstance(refs, list) or not refs or not set(refs) <= evidence.keys():
                raise ValueError('Invalid scenario provenance')
            identities.add(identity); weight += Decimal(str(probability))
            parsed.append({'id': identity, 'summary': text(scenario['summary']),
                           'probability': probability, 'evidenceIds': refs})
        if abs(weight - 1) > Decimal('0.000001'):
            raise ValueError('Scenario probabilities must sum to one')
        probabilities, keys = [], set()
        selections = raw.get('selections', [])
        if not isinstance(selections, list) or len(selections) > 16:
            raise ValueError('Too many model selections')
        for selection in selections:
            market, outcome, point = selection['market'], text(selection['outcome'], 200), selection.get('point')
            if market not in {'h2h', 'spreads', 'totals'}:
                raise ValueError('Unsupported model selection')
            if market == 'h2h' and point is not None:
                raise ValueError('Invalid model point')
            if market != 'h2h':
                point = finite(point, -1000, 1000)
                if market == 'totals' and (point <= 0 or outcome not in {'Over', 'Under'}):
                    raise ValueError('Invalid model total')
            item = {'market': market, 'outcome': outcome, 'point': point,
                    'winProbability': finite(selection['winProbability'], 0, 1)}
            key = selection_key(item)
            if key in keys:
                raise ValueError('Ambiguous model selection')
            keys.add(key); probabilities.append(item)
        top = max(s['probability'] for s in parsed)
        leaders = [s for s in parsed if abs(s['probability'] - top) < 1e-9]
        return {'status': 'model_supplied', 'modelId': text(raw['modelId'], 100),
                'modelVersion': text(raw['modelVersion'], 80), 'generatedAt': iso(generated), 'validUntil': iso(until),
                'evaluationEvidenceId': evaluation, 'rankingScope': 'provided_model_scenarios',
                'mostLikelyScenarioId': leaders[0]['id'] if len(leaders) == 1 else None,
                'scenarios': parsed, 'selections': probabilities,
                'note': 'Operator-supplied model output; evaluation reference is not independently validated here.'}
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return dict(unavailable, reason='invalid_or_stale_forecast')


class ReportService:
    def __init__(self, odds, context=None, weather=None, clock=time.time, monotonic=time.monotonic, research=None, venues=None):
        from .nfl_research import NflResearch
        from .venue_weather import NwsWeather, VenueCatalog
        self.odds = odds
        self.context = context if context is not None else ContextCatalog()
        mode=os.environ.get('REPORT_WEATHER_MODE','nws')
        self.weather = weather if weather is not None else NwsWeather(clock=clock,monotonic=monotonic,mode=mode) if mode in {'nws','disabled'} else OpenMeteoWeather()
        self.venues=venues if venues is not None else VenueCatalog()
        self.research = NflResearch(clock=clock,monotonic=monotonic) if research is None else research
        self.clock, self.monotonic = clock, monotonic
        self.gate = threading.BoundedSemaphore(1)
        self.requests = deque()
        self.weather_cache = OrderedDict()

    def _remaining(self, deadline):
        left = deadline - self.monotonic()
        if left <= 0:
            raise TimeoutError('Report budget exhausted')
        return left

    def _weather(self, event, context, now, deadline):
        venue = context.get('venue') or (event.get('venue') if event.get('venue',{}).get('status')=='matched_catalog' else None)
        if not venue:
            return {'status': 'unavailable', 'reason': 'verified_venue_required'}
        if venue['roof'] == 'indoor' or (venue['roof'] == 'retractable' and venue['roofState'] == 'closed'):
            return {'status': 'not_applicable', 'reason': 'indoor_or_confirmed_closed_roof',
                    'evidenceIds': venue.get('evidenceIds',[]) + venue.get('roofEvidenceIds', []),
                    **({'validUntil':venue['validUntil']} if venue.get('validUntil') else {})}
        if venue['roof'] != 'outdoor' and not (venue['roof'] == 'retractable' and venue['roofState'] == 'open'):
            return {'status': 'unavailable', 'reason': 'roof_state_unknown'}
        key = (event['sport'], event['eventId'], event['startAt'], venue['latitude'], venue['longitude'],venue['roof'],venue.get('roofState'))
        cached = self.weather_cache.get(key)
        if cached and 0 <= now - cached[0] < 300 and (not cached[1].get('validUntil') or timestamp(cached[1]['validUntil'])>now):
            self.weather_cache.move_to_end(key)
            return cached[1]
        try:
            result = self.weather.get(event, venue, now, timeout=self._remaining(deadline))
            self._remaining(deadline)
        except Exception:
            return {'status': 'unavailable', 'reason': 'weather_provider_unavailable'}
        self.weather_cache[key] = now, result
        while len(self.weather_cache) > 32:
            self.weather_cache.popitem(last=False)
        return result

    def build(self, data):
        request = parse_request(data)
        if not self.gate.acquire(blocking=False):
            raise ReportBusy('A game report is already running. Try again shortly.')
        try:
            moment = self.monotonic()
            while self.requests and moment - self.requests[0] >= 60:
                self.requests.popleft()
            if len(self.requests) >= 20:
                raise ReportBusy('The preview report rate limit is reached. Try again shortly.')
            self.requests.append(moment)
            return self._build(request, moment + 20)
        finally:
            self.gate.release()

    def _build(self, request, deadline):
        from .odds import PROP_MARKETS
        # One event request per selected prop market group; never scan every browsed game.
        prop_groups = {}
        for leg in request['legs']:
            if leg['market'] in PROP_MARKETS:
                family = 'alternate' if leg['market'].endswith('_alternate') else 'main'
                key = leg['sport'], leg['eventId'], family
                prop_groups.setdefault(key, set()).add(leg['market'])
        def batch_key(leg):
            if leg['market'] in PROP_MARKETS:
                return leg['sport'], leg['eventId'], 'alternate' if leg['market'].endswith('_alternate') else 'main'
            return leg['sport'], leg['market']
        batches = {}
        for leg in request['legs']:
            key = batch_key(leg)
            if key not in batches:
                try:
                    if leg['market'] in PROP_MARKETS:
                        batches[key] = self.odds.get_props(leg['sport'], leg['eventId'],
                            sorted(prop_groups[key]), timeout=self._remaining(deadline))['quotes']
                    else:
                        batches[key] = self.odds.get(*key, timeout=self._remaining(deadline))['quotes']
                    self._remaining(deadline)
                except Exception:
                    batches[key] = None
        now, matches = self.clock(), []
        for leg in request['legs']:
            quotes = batches[batch_key(leg)]
            if quotes is None:
                matches.append(('provider_unavailable', None)); continue
            candidates = []
            for q in quotes:
                try:
                    if (q['eventId'] == leg['eventId'] and q['sport'] == leg['sport']
                            and q['bookmakerKey'] == leg['bookmaker'] and selection_key(q) == selection_key(leg)
                            and -60 <= now - timestamp(q['updatedAt']) <= 900
                            and timestamp(q['startAt']) > now):
                        # Validate quoted prices and event metadata before reporting any facts.
                        if not isinstance(q['americanOdds'], str) or not re.fullmatch(r'[+-]?\d{3,6}', q['americanOdds']) or not 100 <= abs(int(q['americanOdds'])) <= 100000:
                            continue
                        text(q['homeTeam'], 200); text(q['awayTeam'], 200); timestamp(q['fetchedAt'])
                        candidates.append(q)
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue
            if len(candidates) != 1:
                matches.append(('ambiguous_match' if candidates else 'quote_unavailable', None))
            else:
                q = candidates[0]
                changed = leg['americanOdds'] is not None and int(leg['americanOdds']) != int(q['americanOdds'])
                matches.append(('price_changed' if changed else 'matched', q))
        # An event must have one consistent identity across books/markets.
        identities = {}
        for leg, (_, q) in zip(request['legs'], matches):
            if q:
                identities.setdefault((leg['sport'], leg['eventId']), set()).add(
                    (q['homeTeam'], q['awayTeam'], timestamp(q['startAt'])))
        for i, leg in enumerate(request['legs']):
            if len(identities.get((leg['sport'], leg['eventId']), set())) > 1:
                matches[i] = 'event_identity_conflict', None
        events, reports = {}, []
        for leg, (status, q) in zip(request['legs'], matches):
            event_key = leg['sport'] + ':' + leg['eventId']
            if q and event_key not in events:
                event = {k: q[k] for k in ('eventId', 'sport', 'homeTeam', 'awayTeam', 'startAt')}
                event['startAtPhoenix'] = datetime.fromtimestamp(timestamp(q['startAt']),
                    timezone(timedelta(hours=-7), 'MST')).isoformat()
                try:
                    self._remaining(deadline)
                    context = self.context.lookup(event, now)
                except Exception:
                    context = {'status': 'unavailable', 'reason': 'context_provider_unavailable',
                               'evidence': [], 'facts': [], 'venue': None, 'forecast': None}
                from .nfl_research import unavailable
                try:
                    names = list(dict.fromkeys(l['playerName'] for l in request['legs']
                        if l.get('playerName') and (l['sport'],l['eventId']) == (leg['sport'],leg['eventId'])))
                    research = self.research.lookup(event,names,now,timeout=self._remaining(deadline)) if self.research else unavailable('research_disabled')
                except Exception:
                    research = unavailable('research_provider_unavailable')
                try:
                    venue = self.venues.lookup(event,research,now) if not context.get('venue') else {'status':'operator_supplied','reason':'curated_context_venue'}
                except Exception:
                    venue = {'status':'unavailable','reason':'venue_catalog_unavailable'}
                event.update(context={k: context[k] for k in ('status', 'reason', 'evidence', 'facts', 'venue')},
                             gameScript=forecast_snapshot(context, event, now),
                             research=research,
                             venue=venue)
                event.update(
                             weather=self._weather(event, context, now, deadline))
                events[event_key] = event
        for leg, (status, q) in zip(request['legs'], matches):
            event_key = leg['sport'] + ':' + leg['eventId']
            reports.append(self._leg(leg, status, q, event_key, events.get(event_key)))
        # A network operation may straddle the start/staleness boundary.
        finished = self.clock()
        for event in events.values():
            venue=event['venue']
            if venue.get('status')=='matched_catalog' and timestamp(venue['validUntil'])<=finished:
                event['venue']={'status':'unavailable','reason':'venue_evidence_expired'}
                event['weather'].clear();event['weather'].update(status='unavailable',reason='venue_evidence_expired')
            weather=event['weather']
            if weather.get('status')=='available' and weather.get('validUntil') and timestamp(weather['validUntil'])<=finished:
                weather.clear();weather.update(status='unavailable',reason='weather_expired_during_report')
            research = event['research']
            if any(timestamp(s['validUntil']) <= finished for s in research.get('sources',[])):
                from .nfl_research import unavailable
                event['research'] = unavailable('research_expired_during_report')
            context = event['context']
            context['evidence'] = [e for e in context['evidence'] if timestamp(e['validUntil']) > finished]
            if not context['evidence'] and context['status'] == 'available':
                context.update(status='unavailable', reason='no_fresh_evidence')
            active_ids = {e['id'] for e in context['evidence']}
            context['facts'] = [f for f in context['facts'] if set(f['evidenceIds']) <= active_ids]
            venue = context['venue']
            if venue and not set(venue['evidenceIds'] + venue.get('roofEvidenceIds', [])) <= active_ids:
                context['venue'] = None
                event['weather'].clear()
                event['weather'].update(status='unavailable', reason='venue_evidence_expired')
            script = event['gameScript']
            if script['status'] == 'model_supplied' and (
                    timestamp(script['validUntil']) <= finished or finished-timestamp(script['generatedAt']) > 3600
                    or script['evaluationEvidenceId'] not in active_ids
                    or any(not set(s['evidenceIds']) <= active_ids for s in script['scenarios'])):
                script.clear()
                script.update(status='unavailable', reason='evidence_expired_during_report',
                              mostLikelyScenarioId=None, scenarios=[], selections=[])
        for report in reports:
            event = events.get(report['eventRef'])
            if event and event['research'].get('reason') == 'research_expired_during_report':
                report['seven'][0].update(status='needs_data',bullets=['Research expired while this report was being prepared. Refresh before relying on it.'])
                if report['selection'].get('playerName'):
                    report['seven'][4].update(status='needs_data',bullets=[report['legImplication']+' The NFL research snapshot expired; refresh before relying on it.'])
            if report['gameScript'] and report['gameScript']['status'] != 'model_supplied':
                had_probability = report['modelWinProbability'] is not None
                report['modelWinProbability'] = None
                report['probabilityBasis'] = 'unavailable'
                if had_probability:
                    report['seven'][4].update(status='needs_data', bullets=[report['legImplication'] + ' No supported win estimate is available.'])
            if report['eventRef']:
                valid_ids = {e['id'] for e in events[report['eventRef']]['context']['evidence']}
                valid_ids.add('quote:' + report['id'])
                for seat in report['seven']:
                    seat['evidenceIds'] = [i for i in seat['evidenceIds'] if i in valid_ids]
            q = report['quote']
            if q and (timestamp(q['startAt']) <= finished or not -60 <= finished - timestamp(q['updatedAt']) <= 900):
                report['matchStatus'] = 'expired_during_report'
                report['modelWinProbability'] = None
                report['probabilityBasis'] = 'unavailable'
                report['seven'][0].update(status='blocked', bullets=['The quote expired or the game started during research; refresh the selection.'])
                report['seven'][4].update(status='needs_data', bullets=[report['legImplication'] + ' Refresh the quote before using an estimate.'])
                report['seven'][-1].update(status='blocked', bullets=['The game started or its quote expired during research. Refresh before analysis.'])
        return {'schemaVersion': 1, 'generatedAt': iso(finished), 'generationMethod': 'deterministic_evidence_findings',
                'events': list(events.values()), 'legs': reports,
                'assessment': {'status': 'insufficient_data', 'estimatedWinProbability': None,
                    'offeredParlayDecimalPrice': None, 'alternatives': [],
                    'reasons': ['A calibrated joint ticket forecast and actual combined sportsbook quote are not configured.',
                                'Individual win probabilities are not multiplied into a same-game forecast.',
                                           'Push and void settlement rules are required before comparing alternate lines or split tickets.'],
                    'comparisonContext': {'totalStake': request['totalStake'],
                                          'minimumTotalReturn': request['minimumTotalReturn'],
                                          'stakeBasis': 'fixed_total_capital'}}}

    def _leg(self, leg, status, quote, event_key, event):
        script = event['gameScript'] if event else None
        probability = None
        if status == 'matched' and script and script['status'] == 'model_supplied':
            probability = next((s['winProbability'] for s in script['selections']
                                if selection_key(s) == selection_key(leg)), None)
        price = None
        if quote:
            odds = int(quote['americanOdds'])
            decimal = 1 + (Fraction(odds, 100) if odds > 0 else Fraction(100, -odds))
            price = {'americanOdds': str(odds), 'decimalOdds': format(float(decimal), '.12g'),
                     'decimalFraction': {'numerator': decimal.numerator, 'denominator': decimal.denominator},
                     'breakEvenPercent': float(100 / decimal), 'basis': 'bookmaker_price_not_win_forecast'}
        if leg.get('playerName'):
            from .prop_settlement import threshold_unverified, threshold_notice
            category = 'passing' if 'pass_yds' in leg['market'] else 'rushing'
            if threshold_unverified(leg['market'], leg['point']):
                probability = None
                implication = f"{leg['playerName']} · {category} yards. " + threshold_notice(leg['market'], leg['outcome'], leg['point'])
            else:
                implication = f"Requires {leg['playerName']} to record {leg['outcome'].lower()} {leg['point']:g} {category} yards."
            implication += (' Participation, overtime, push and void rules need verification. '
                            'The provider player name is not a verified roster/player ID.')
        else:
            implication = {'h2h': f"Requires {leg['outcome']} to win, subject to sportsbook draw/settlement rules.",
                       'spreads': 'Selected team score plus the stated handicap must exceed the opponent score.',
                       'totals': f"Requires the combined score to be {'above' if leg['outcome']=='Over' else 'below'} {leg['point']}; check overtime and push rules."}[leg['market']]
        good = status == 'matched'
        finding = [
            ('ok' if good else 'blocked', 'Event and selection match fresh provider data; roster/injury research requires cited context.' if good else f'Selection could not be approved: {status}.'),
            ('needs_data', 'Priced alternate lines and the customer payout floor are needed before ranking alternatives.'),
            ('needs_data', 'Same-game legs require joint outcomes; no bankroll sizing or independence is assumed.'),
            ('ok' if quote else 'needs_data', f"Quoted decimal price {price['decimalOdds']}; break-even {price['breakEvenPercent']:.2f}% is a price threshold." if price else 'A unique current quote is required for payout arithmetic.'),
            ('ok' if probability is not None else 'needs_data', implication + (' Model estimate supplied with evaluation reference.' if probability is not None else ' No supported win estimate is available.')),
            ('not_applicable', 'No promotion is applied; sportsbook settlement and any future token terms require verification.'),
            ('needs_data' if good else 'blocked', 'Whole-ticket value remains unestablished without joint model support and a combined quote.' if good else 'Resolve selection identity, price or freshness before using this leg.')]
        if status == 'price_changed':
            finding[0] = 'blocked', 'The current quote differs from the requested price; customer reconfirmation is required.'
        research = event.get('research') if event else None
        if good and research and research['mapping']:
            mapping = research['mapping']
            finding[0] = ('needs_data', f"Schedule matched NFL week {mapping['week']}. Injury/roster data are file snapshots, not confirmed participation.")
            if leg.get('playerName'):
                player = next((p for p in research['players'] if p['requestedName']==leg['playerName']),None)
                if player:
                    finding[4] = ('needs_data', implication + f" Player mapping: {player['status']}; injury snapshot: {player['injury']['status']}. No supported probability adjustment.")
        evidence_ids = [e['id'] for e in event['context']['evidence']] if event else []
        quote_refs = ['quote:' + leg['id']] if quote else []
        seat_refs = [quote_refs + evidence_ids, [], [], quote_refs, quote_refs + evidence_ids, [], quote_refs + evidence_ids]
        quote_fields = ('id', 'eventId', 'event', 'startAt', 'sport', 'market', 'label', 'americanOdds',
                        'bookmaker', 'bookmakerKey', 'homeTeam', 'awayTeam', 'outcome', 'point', 'updatedAt', 'fetchedAt',
                        'playerName', 'playerIdentityBasis', 'settlement')
        return {'id': leg['id'], 'selection': leg, 'matchStatus': status, 'eventRef': event_key if event else None,
                'quote': {k: quote[k] for k in quote_fields if k in quote} if quote else None,
                'quoteSource': {'id': 'quote:' + leg['id'], 'provider': 'The Odds API', 'sourceUrl': 'https://the-odds-api.com/',
                    'updatedAt': quote['updatedAt'], 'retrievedAt': quote['fetchedAt']} if quote else None,
                'price': price, 'gameScript': script, 'legImplication': implication,
                'weather': event['weather'] if event else {'status': 'unavailable', 'reason': 'event_not_matched'},
                'modelWinProbability': probability, 'probabilityBasis': 'operator_supplied_model' if probability is not None else 'unavailable',
                'seven': [{'seat': i, 'name': name, 'status': state, 'bullets': [bullet], 'evidenceIds': seat_refs[i-1]}
                          for i, (name, (state, bullet)) in enumerate(zip(SEATS, finding), 1)]}
