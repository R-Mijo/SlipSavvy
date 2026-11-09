"""Numeric threshold evidence only; sportsbook settlement remains unverified."""
import math


def prop_settlement(market, point):
    # Alternate market keys include X+ milestones as well as strict Over/Under.
    # An opposing quote alone does not establish the bookmaker's original label.
    valid = type(point) in (int, float) and math.isfinite(point) and 0 < point <= 1000
    semantics, push = 'unsupported_threshold', None
    if valid:
        if float(point).is_integer():
            semantics, push = ('alternate_integer_unverified', None) if market.endswith('_alternate') else ('over_under_integer', True)
        elif (point * 2).is_integer():
            semantics, push = 'over_under_half_point', False
    return {'status': 'rules_required', 'thresholdSemantics': semantics, 'pushPossible': push,
            'nonParticipation': 'unknown', 'overtime': 'unknown'}


def threshold_unverified(market, point):
    return prop_settlement(market, point)['pushPossible'] is None


def threshold_notice(market, outcome, point):
    if prop_settlement(market, point)['thresholdSemantics'] == 'alternate_integer_unverified':
        return (f'The feed lists {outcome} {point:g}. At exactly {point:g} yards, the result is unverified: '
                'alternate markets can contain milestones or Over/Under lines. '
                'No win, loss or refund at that boundary is assumed.')
    return 'The yardage threshold is unsupported; its win, loss and refund boundary is unverified.'
