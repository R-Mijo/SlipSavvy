"""Deterministic scenario analysis using exact rational arithmetic.

Each game_id denotes ONE mutually exclusive outcome group, not every market in
a sporting event. Multiple groups require an explicit independence assumption
or a supplied joint distribution. Odds are observations, not true probabilities.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product
from collections import defaultdict, Counter
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import time


def number(value, label='number'):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Fraction, Decimal)):
        raise ValueError(f'{label} must be a finite number')
    try:
        return value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, ZeroDivisionError, OverflowError):
        raise ValueError(f'{label} must be finite') from None


def positive(value, label):
    result = number(value, label)
    if result <= 0:
        raise ValueError(f'{label} must be positive')
    return result


def odds(value):
    if type(value) is not int or abs(value) < 100:
        raise ValueError('American odds must be an integer <= -100 or >= +100')
    return value


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text')
    return value


@dataclass(frozen=True)
class BinaryEvent:
    event_id: str
    game_id: str
    name: str
    american_odds: int
    opposing_american_odds: int | None = None
    fair_prob_override: Fraction | None = None
    evidence_tier: int = 3
    evidence_ref: str = ''

    def __post_init__(self):
        for name in ('event_id', 'game_id', 'name'):
            text(getattr(self, name), name)
        odds(self.american_odds)
        if self.opposing_american_odds is not None:
            odds(self.opposing_american_odds)
        if self.fair_prob_override is not None:
            p = number(self.fair_prob_override, 'probability')
            if not 0 <= p <= 1:
                raise ValueError('Probability must be between zero and one')
            object.__setattr__(self, 'fair_prob_override', p)
        if type(self.evidence_tier) is not int or self.evidence_tier not in (1, 2, 3):
            raise ValueError('Evidence tier must be 1, 2 or 3')
        if not isinstance(self.evidence_ref, str):
            raise ValueError('Evidence reference must be text')


@dataclass(frozen=True)
class PromoBoost:
    boost_id: str
    boost_pct: Fraction
    max_stake: Fraction
    min_american_odds: int = -200
    expired: bool = False
    allow_split_stake: bool = False
    max_uses: int = 1

    def __post_init__(self):
        text(self.boost_id, 'boost_id')
        boost = number(self.boost_pct, 'boost_pct')
        if boost < 0:
            raise ValueError('Profit boost cannot be negative')
        object.__setattr__(self, 'boost_pct', boost)
        object.__setattr__(self, 'max_stake', positive(self.max_stake, 'max_stake'))
        odds(self.min_american_odds)
        if type(self.expired) is not bool or type(self.allow_split_stake) is not bool:
            raise ValueError('Promotion flags must be booleans')
        if type(self.max_uses) is not int or self.max_uses < 1:
            raise ValueError('max_uses must be a positive integer')


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    leg_ids: tuple[str, ...]
    stake: Fraction
    boost: PromoBoost | None = None
    correlation_cov: Fraction = Fraction(0)
    quoted_decimal_odds: Fraction | None = None

    def __post_init__(self):
        text(self.ticket_id, 'ticket_id')
        if not isinstance(self.leg_ids, (tuple, list)) or not self.leg_ids:
            raise ValueError('A ticket needs at least one leg')
        legs = tuple(text(x, 'leg_id') for x in self.leg_ids)
        if len(legs) != len(set(legs)):
            raise ValueError('Repeated legs are not allowed')
        object.__setattr__(self, 'leg_ids', legs)
        object.__setattr__(self, 'stake', positive(self.stake, 'stake'))
        if self.boost is not None and not isinstance(self.boost, PromoBoost):
            raise ValueError('Invalid promotion')
        if number(self.correlation_cov) != 0:
            raise ValueError('Pairwise covariance does not specify a joint distribution; supply joint_distribution')
        if self.quoted_decimal_odds is not None:
            quote = number(self.quoted_decimal_odds)
            if quote <= 1:
                raise ValueError('Quoted decimal odds must exceed one')
            object.__setattr__(self, 'quoted_decimal_odds', quote)


class PayoutModeler:
    @staticmethod
    def american_to_decimal(value):
        value = odds(value)
        return 1 + (Fraction(value, 100) if value > 0 else Fraction(100, -value))

    @classmethod
    def american_to_implied_prob(cls, value):
        return 1 / cls.american_to_decimal(value)

    @classmethod
    def parlay_multiplier(cls, leg_odds):
        if not leg_odds:
            raise ValueError('At least one quoted price is required')
        result = Fraction(1)
        for value in leg_odds:
            result *= cls.american_to_decimal(value)
        return result

    @classmethod
    def calculate_ticket_payout(cls, ticket, events):
        if any(lid not in events for lid in ticket.leg_ids):
            raise ValueError('Ticket references an unknown event')
        groups = [events[lid].game_id for lid in ticket.leg_ids]
        if len(groups) != len(set(groups)):
            raise ValueError('A ticket cannot combine mutually exclusive outcomes')
        d = ticket.quoted_decimal_odds or cls.parlay_multiplier([events[lid].american_odds for lid in ticket.leg_ids])
        boosted = Fraction(0)
        extra_profit = Fraction(0)
        if ticket.boost:
            promo = ticket.boost
            if promo.expired:
                raise ValueError('Promotion has expired')
            if d < cls.american_to_decimal(promo.min_american_odds):
                raise ValueError('Ticket does not meet promotion minimum odds')
            if ticket.stake > promo.max_stake and not promo.allow_split_stake:
                raise ValueError('Stake exceeds promotion cap; split treatment requires explicit permission')
            boosted = min(ticket.stake, promo.max_stake)
            extra_profit = boosted * (d - 1) * promo.boost_pct
        gross = ticket.stake * d + extra_profit
        return {'ticket_id': ticket.ticket_id, 'stake': ticket.stake, 'decimal_multiplier': d,
                'boosted_stake_portion': boosted, 'unboosted_stake_portion': ticket.stake - boosted,
                'gross_return': gross, 'net_profit': gross - ticket.stake}

    @staticmethod
    def expected_net_return(win_prob, gross_return, stake):
        p = number(win_prob)
        if not 0 <= p <= 1:
            raise ValueError('Probability out of range')
        return p * positive(gross_return, 'gross_return') - positive(stake, 'stake')

    @staticmethod
    def fractional_kelly(win_prob, decimal_odds, fraction=Fraction(1, 4)):
        p, d, f = number(win_prob), number(decimal_odds), number(fraction)
        if not 0 <= p <= 1 or d <= 1 or not 0 < f <= 1:
            raise ValueError('Invalid probability, odds or Kelly fraction')
        return max(Fraction(0), ((d - 1) * p - (1 - p)) / (d - 1) * f)


class ProbabilityModeler:
    @staticmethod
    def devig_multi_way(prices):
        if len(prices) < 2:
            raise ValueError('De-vigging needs all outcomes of a market')
        raw = [PayoutModeler.american_to_implied_prob(p) for p in prices]
        return tuple(p / sum(raw) for p in raw)

    @classmethod
    def devig_two_way(cls, side1, side2):
        return cls.devig_multi_way([side1, side2])

    @classmethod
    def event_fair_prob(cls, event):
        if event.fair_prob_override is not None:
            return event.fair_prob_override
        if event.opposing_american_odds is not None:
            return cls.devig_two_way(event.american_odds, event.opposing_american_odds)[0]
        raise ValueError('An explicit scenario probability or both market prices are required; raw implied odds are not fair probabilities')


class StateEngine:
    @staticmethod
    def build_state_ledger(events, tickets, *, assume_independent_groups=False, joint_distribution=None):
        if type(assume_independent_groups) is not bool:
            raise ValueError('Independence must be an explicit boolean')
        if not events or len(events) > 16 or any(not isinstance(e, BinaryEvent) for e in events):
            raise ValueError('Supply between 1 and 16 BinaryEvent outcomes')
        if not isinstance(tickets, (list, tuple)) or not tickets or any(not isinstance(t, Ticket) for t in tickets):
            raise ValueError('A nonempty ticket list is required')
        event_map = {e.event_id: e for e in events}
        if len(event_map) != len(events) or len({t.ticket_id for t in tickets}) != len(tickets):
            raise ValueError('Event and ticket IDs must be unique')
        groups = defaultdict(list)
        probs = {e.event_id: ProbabilityModeler.event_fair_prob(e) for e in events}
        for event in events:
            groups[event.game_id].append(event.event_id)
        if any(sum(probs[eid] for eid in members) > 1 for members in groups.values()):
            raise ValueError('Exclusive outcome probabilities exceed one; supply consistent probabilities')
        if len(groups) > 1 and joint_distribution is None and not assume_independent_groups:
            raise ValueError('Declare independence between outcome groups or supply a joint distribution')
        uses = Counter(t.boost.boost_id for t in tickets if t.boost)
        promotions = {}
        for t in tickets:
            if t.boost:
                if t.boost.boost_id in promotions and promotions[t.boost.boost_id] != t.boost:
                    raise ValueError('Inconsistent rules for the same promotion ID')
                promotions[t.boost.boost_id] = t.boost
                if uses[t.boost.boost_id] > t.boost.max_uses:
                    raise ValueError('Promotion use limit exceeded')
        payouts = {t.ticket_id: PayoutModeler.calculate_ticket_payout(t, event_map) for t in tickets}
        n = len(events)
        keys = list(product((0, 1), repeat=n))
        joint = None
        if joint_distribution is not None:
            if not isinstance(joint_distribution, dict) or not joint_distribution:
                raise ValueError('Joint distribution must map state tuples to probabilities')
            joint = {}
            for key, value in joint_distribution.items():
                if not isinstance(key, tuple) or len(key) != n or any(type(b) is not int or b not in (0, 1) for b in key):
                    raise ValueError('Invalid joint-distribution state')
                p = number(value, 'joint probability')
                if not 0 <= p <= 1:
                    raise ValueError('Invalid joint probability')
                joint[key] = p
            if sum(joint.values()) != 1:
                raise ValueError('Joint distribution must sum exactly to one')
            for i, event in enumerate(events):
                if sum(p for bits, p in joint.items() if bits[i]) != probs[event.event_id]:
                    raise ValueError('Joint distribution does not match supplied marginal probabilities')
        states = []
        capital = sum(t.stake for t in tickets)
        for index, bits in enumerate(keys):
            outcome = dict(zip(event_map, bits))
            possible = True
            p = Fraction(1)
            for members in groups.values():
                winners = [eid for eid in members if outcome[eid]]
                if len(winners) > 1:
                    possible = False
                    break
                group_p = probs[winners[0]] if winners else 1 - sum(probs[eid] for eid in members)
                if group_p == 0:
                    possible = False
                p *= group_p
            if joint is not None:
                p = joint.get(bits, Fraction(0))
                if not possible and p:
                    raise ValueError('Joint distribution assigns probability to an impossible state')
            if not possible:
                p = Fraction(0)
            winners = [t.ticket_id for t in tickets if possible and all(outcome[lid] for lid in t.leg_ids)]
            gross = sum((payouts[tid]['gross_return'] for tid in winners), Fraction(0))
            states.append({'state_index': index, 'bits': bits, 'outcomes': outcome,
                           'legally_possible': possible, 'probability': p,
                           'winning_tickets': winners, 'gross_return': gross, 'net_profit': gross - capital})
        if sum(s['probability'] for s in states) != 1:
            raise ValueError('State probability mass is not one')
        return {'n_variables': n, 'theoretical_states': 2 ** n,
                'legally_possible_states': sum(s['legally_possible'] for s in states),
                'impossible_states': sum(not s['legally_possible'] for s in states),
                'total_capital': capital, 'ticket_payouts': payouts, 'states': states,
                'assume_independent_groups': assume_independent_groups,
                'joint_distribution': joint_distribution}


class RiskAnalyzer:
    @staticmethod
    def evaluate_risk(ledger, target_gross, secondary_target=None):
        target = positive(target_gross, 'target_gross')
        secondary = positive(secondary_target, 'secondary_target') if secondary_target is not None else None
        states = ledger['states']
        if any(not 0 <= s['probability'] <= 1 for s in states) or sum(s['probability'] for s in states) != 1:
            raise ValueError('Invalid probability distribution')
        c = positive(ledger['total_capital'], 'capital')
        expected = sum(s['probability'] * s['gross_return'] for s in states)
        probability = lambda predicate: sum((s['probability'] for s in states if predicate(s['gross_return'])), Fraction(0))
        return {'total_capital': c, 'expected_gross': expected, 'expected_net': expected - c,
                'expected_roi_pct': (expected - c) / c * 100,
                'p_wipeout': probability(lambda r: r == 0), 'p_loss': probability(lambda r: r < c),
                'p_net_positive': probability(lambda r: r > c), 'p_target': probability(lambda r: r >= target),
                'p_secondary_target': probability(lambda r: r >= secondary) if secondary is not None else None}


class ScenarioAuditor:
    @staticmethod
    def audit_portfolio(events, tickets, ledger, risk_metrics, target_gross):
        findings = []
        warnings = []
        try:
            rebuilt = StateEngine.build_state_ledger(events, tickets,
                assume_independent_groups=ledger.get('assume_independent_groups', False),
                joint_distribution=ledger.get('joint_distribution'))
            if rebuilt != ledger:
                findings.append('Ledger does not match recomputed inputs')
            risk = RiskAnalyzer.evaluate_risk(rebuilt, target_gross)
            comparable = {k: v for k, v in risk_metrics.items() if k != 'p_secondary_target'}
            if comparable != {k: v for k, v in risk.items() if k != 'p_secondary_target'}:
                findings.append('Risk metrics do not match recomputed inputs')
            for event in events:
                if event.evidence_tier != 1 or not event.evidence_ref.strip():
                    findings.append(f'{event.event_id}: Tier-1 evidence reference is missing')
            if ledger['assume_independent_groups']:
                warnings.append('Independence between distinct outcome groups is an explicit modeling assumption')
        except (ValueError, TypeError, KeyError) as error:
            findings.append(str(error))
        return {'verdict': 'ANALYSIS_READY' if not findings else 'REVIEW_REQUIRED',
                'findings': findings, 'warnings': warnings,
                'limitations': ['Evidence references are supplied by the caller; authenticity is not verified.',
                                'Analysis does not authorize or place a wager. Prices, probabilities and promotion rules must be supplied.']}


class StakeOptimizer:
    @staticmethod
    def search(events, templates, stake_options, *, capital_limit, target_gross,
               max_candidates=1000, seconds=5, assume_independent_groups=False,
               joint_distribution=None):
        """Search an explicit finite stake grid; stop by count or time budget.

        Optimality is only within the declared templates/stake grid, and only if
        every candidate was visited. Invalid promotion allocations are skipped.
        """
        if not templates or len(templates) > 10 or len(events) > 10:
            raise ValueError('Search is limited to 10 templates and 10 events')
        if len({t.ticket_id for t in templates}) != len(templates):
            raise ValueError('Template IDs must be unique')
        # Reject invalid global modeling assumptions rather than quietly
        # reporting an empty optimum after skipping every candidate.
        StateEngine.build_state_ledger(events,
            [replace(t, stake=1, boost=None) for t in templates],
            assume_independent_groups=assume_independent_groups,
            joint_distribution=joint_distribution)
        choices = tuple(sorted(set(number(s, 'stake option') for s in stake_options)))
        if not choices or len(choices) > 30 or any(s < 0 for s in choices):
            raise ValueError('Supply 1 to 30 nonnegative stake options')
        if type(max_candidates) is not int or not 1 <= max_candidates <= 100000:
            raise ValueError('max_candidates must be between 1 and 100000')
        duration = positive(seconds, 'seconds')
        capital = positive(capital_limit, 'capital_limit')
        positive(target_gross, 'target_gross')
        started = time.monotonic()
        total = len(choices) ** len(templates)
        visited, evaluated, best, best_score = 0, 0, None, None
        for stakes in product(choices, repeat=len(templates)):
            if visited >= max_candidates or time.monotonic() - started >= float(duration):
                break
            visited += 1
            if not 0 < sum(stakes) <= capital:
                continue
            tickets = [replace(t, stake=s) for t, s in zip(templates, stakes) if s]
            try:
                ledger = StateEngine.build_state_ledger(events, tickets,
                    assume_independent_groups=assume_independent_groups, joint_distribution=joint_distribution)
                risk = RiskAnalyzer.evaluate_risk(ledger, target_gross)
            except ValueError:
                continue
            evaluated += 1
            score = (risk['p_target'], -risk['p_wipeout'], risk['expected_net'])
            if best_score is None or score > best_score:
                best_score = score
                best = {'stakes': {t.ticket_id: t.stake for t in tickets}, 'risk': risk}
        return {'best': best, 'visited': visited, 'evaluated': evaluated, 'declared_grid_size': total,
                'optimality': 'OPTIMAL_WITHIN_DECLARED_GRID' if visited == total else 'BEST_FOUND_LIMIT_REACHED',
                'objective': 'max target probability, then min wipeout probability, then max expected net'}


def display(value):
    if isinstance(value, Fraction):
        with localcontext() as context:
            context.prec = 18
            return str(Decimal(value.numerator) / Decimal(value.denominator))
    raise TypeError(type(value).__name__)
