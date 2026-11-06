"""Apache-2.0. Copyright 2026 Marco Armijo (R-Mijo).

Transparent ticket scenarios, not a trained sports prediction model.
"""
from datetime import datetime, timezone
from fractions import Fraction
import math
import random


def fraction(value, name, minimum=0, maximum=1):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)) or len(str(value)) > 40:
        raise ValueError(f'Invalid {name}')
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError, OverflowError):
        raise ValueError(f'Invalid {name}') from None
    if not minimum <= result <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}')
    return result


def odds_price(odds):
    q = fraction(odds, 'American odds', -100000, 100000)
    if q.denominator != 1 or -100 < q < 100:
        raise ValueError('American odds must be integers <= -100 or >= +100')
    return 1 + (q / 100 if q > 0 else 100 / -q)


def wilson(hits, trials):
    p = hits / trials
    z = 1.959963984540054
    denom = 1 + z*z/trials
    center = (p + z*z/(2*trials))/denom
    margin = z*math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials))/denom
    return [max(0, center-margin), min(1, center+margin)]


def education():
    ladder = [-1000,-500,-300,-200,-150,-110,100,150,200,300,500,1000,9900]
    return {
        'odds_ladder': [{'american_odds': o, 'decimal_price': float(odds_price(o)),
                         'break_even_percent': float(100 / odds_price(o))} for o in ladder],
        'independent_legs': [{'legs': n, 'each_win_percent': 60,
                              'ticket_win_percent': float(100 * Fraction(3,5)**n)} for n in range(1,7)],
        'five_to_five_hundred': {'stake': 5, 'gross_return': 500, 'decimal_price': 100,
                                'american_odds': 9900, 'break_even_percent': 1},
        'explanation': 'Multiply decimal prices, not American odds. Multiply win probabilities only under an independence assumption. Break-even probability includes bookmaker margin and is not a forecast. A $500 total return includes the $5 stake.',
    }


def simulate(data, trials=100000, seed=42):
    if type(trials) is not int or not 1000 <= trials <= 1000000:
        raise ValueError('Trials must be an integer from 1,000 to 1,000,000')
    if type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError('Seed must be an integer from 0 to 4294967295')
    if not isinstance(data, dict):
        raise ValueError('Ticket must be an object')
    legs = data.get('legs')
    if not isinstance(legs, list) or not 1 <= len(legs) <= 12 or not all(isinstance(l,dict) for l in legs):
        raise ValueError('Supply 1 to 12 legs')
    if len(legs) > 1 and data.get('assume_conditional_independence') is not True:
        raise ValueError('Explicit conditional-independence assumption required; same-game correlations are not inferred')
    stake = fraction(data.get('stake', '5'), 'stake', Fraction(1,100), 10000)
    ids = [l.get('id') for l in legs]
    if any(not isinstance(i,str) or not i.strip() or len(i)>100 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Leg IDs must be unique nonempty strings')
    prices = [odds_price(l.get('american_odds')) for l in legs]
    base_probs = [fraction(l.get('win_probability'), 'leg probability') for l in legs]
    scenarios = data.get('game_scripts')
    if scenarios is None:
        scenarios = [{'name':'Base assumptions', 'weight':'1', 'probabilities':dict(zip(ids,base_probs))}]
        # Fractions were already validated, serialize for the same validation path.
        scenarios[0]['probabilities'] = {k:str(v) for k,v in scenarios[0]['probabilities'].items()}
    if not isinstance(scenarios,list) or not 1 <= len(scenarios) <= 20:
        raise ValueError('Supply 1 to 20 game-script scenarios')
    weights, conditional, names = [], [], []
    for scenario in scenarios:
        if not isinstance(scenario,dict) or not isinstance(scenario.get('name'),str) or not scenario['name'].strip() or len(scenario['name'])>200:
            raise ValueError('Every game script needs a short name')
        probs = scenario.get('probabilities')
        if not isinstance(probs,dict) or set(probs) != set(ids):
            raise ValueError('Every game script must specify exactly the ticket leg IDs')
        weights.append(fraction(scenario.get('weight'), 'scenario weight'))
        conditional.append([fraction(probs[i], 'conditional probability') for i in ids])
        names.append(scenario['name'])
    if sum(weights) != 1 or len(set(names)) != len(names):
        raise ValueError('Scenario weights must sum exactly to one; names must be unique')
    price = math.prod(prices)
    quoted_price = data.get('quoted_decimal_price')
    if quoted_price is not None:
        price = fraction(quoted_price, 'quoted decimal price', 1, 1000000)
    analytic = sum(w*math.prod(ps) for w,ps in zip(weights,conditional))
    marginals = [sum(w*ps[i] for w,ps in zip(weights,conditional)) for i in range(len(legs))]
    rng = random.Random(seed)
    cumulative, running = [], 0.0
    for w in weights:
        running += float(w); cumulative.append(running)
    cumulative[-1] = 1.0
    probs_float = [[float(p) for p in ps] for ps in conditional]
    leg_hits, hits, scenario_counts = [0]*len(legs), 0, [0]*len(scenarios)
    for _ in range(trials):
        selector = rng.random()
        si = next(i for i,c in enumerate(cumulative) if selector < c)
        scenario_counts[si] += 1
        wins = [rng.random() < p for p in probs_float[si]]
        for i, win in enumerate(wins):
            leg_hits[i] += int(win)
        hits += int(all(wins))
    leg_reports = []
    for i, leg in enumerate(legs):
        context = {k:leg.get(k) for k in ('source','captured_at','weather','game_script','rationale','event')}
        leg_reports.append({'id':ids[i], 'name':str(leg.get('name',ids[i]))[:300],
            'american_odds':float(fraction(leg['american_odds'],'odds',-100000,100000)),
            'model_estimated_win_percent':float(100*marginals[i]),
            'estimated_hit_score_out_of_100':round(float(100*marginals[i]),1),
            'price_break_even_percent':float(100/prices[i]),
            'simulation_hit_percent':100*leg_hits[i]/trials,
            'context':context, 'source_status':'User supplied; authenticity and freshness not verified'})
    return {'method':'Seeded Monte Carlo with shared game-script scenarios and conditionally independent leg draws',
        'trials':trials,'seed':seed,'ticket_hits':hits,'ticket_losses':trials-hits,
        'simulation_win_percent':100*hits/trials,
        'simulation_sampling_interval_95_percent':[100*x for x in wilson(hits,trials)],
        'analytic_model_win_percent':float(100*analytic),
        'estimated_hit_score_out_of_100':round(float(100*analytic),1),
        'score_label':'Model-estimated hit probability /100. Uncalibrated; not confidence in the model or data.',
        'gross_if_win':float(stake*price),'net_if_win':float(stake*(price-1)),
        'loss_if_lose':float(stake),'break_even_percent':float(100/price),
        'expected_net_under_model':float(stake*(analytic*price-1)),
        'price_basis':'User-quoted ticket price' if quoted_price is not None else 'Product of leg prices; hypothetical, not a sportsbook quote',
        'legs':leg_reports,'game_scripts':[{'name':n,'weight':float(w),'simulated_trials':c} for n,w,c in zip(names,weights,scenario_counts)],
        'limitations':['100,000 simulations reduce sampling noise, not model error.',
            'The 95% interval measures simulation sampling error only, not uncertainty in the true win probability.',
            'Game scripts and weather notes are user inputs. No sports prediction model or automatic weather adjustment is trained here.',
            'Within-script correlations are not modeled. Same-game bets need a validated joint model.',
            'Pushes, voids, boosts, settlement rounding and taxes are not included. No wager is placed.'],
        'generated_at':datetime.now(timezone.utc).isoformat()}
