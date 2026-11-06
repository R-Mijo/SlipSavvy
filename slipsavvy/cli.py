import argparse
import json
from pathlib import Path
from .engine import (BinaryEvent, PromoBoost, Ticket, StateEngine,
                     RiskAnalyzer, ScenarioAuditor, display)

def analyze(data):
    events = [BinaryEvent(**event) for event in data['events']]
    tickets = []
    for original in data['tickets']:
        values = dict(original)
        if values.get('boost'):
            values['boost'] = PromoBoost(**values['boost'])
        tickets.append(Ticket(**values))
    joint = None
    if data.get('joint_distribution') is not None:
        joint = {}
        for row in data['joint_distribution']:
            key = tuple(row['bits'])
            if key in joint:
                raise ValueError('Duplicate joint state')
            joint[key] = row['probability']
    ledger = StateEngine.build_state_ledger(events, tickets,
        assume_independent_groups=data.get('assume_independent_groups', False), joint_distribution=joint)
    risk = RiskAnalyzer.evaluate_risk(ledger, data['target_gross'])
    audit = ScenarioAuditor.audit_portfolio(events, tickets, ledger, risk, data['target_gross'])
    return {'risk': risk, 'audit': audit, 'states': ledger['states']}

def main(argv=None):
    parser = argparse.ArgumentParser(description='SlipSavvy: deterministic scenario analysis')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    sub.add_parser('education')
    ui = sub.add_parser('ui')
    ui.add_argument('--port', type=int, default=8766)
    ui.add_argument('--no-browser', action='store_true')
    sim = sub.add_parser('simulate')
    sim.add_argument('file', type=Path)
    sim.add_argument('--trials', type=int, default=100000)
    sim.add_argument('--seed', type=int, default=42)
    cmd = sub.add_parser('analyze')
    cmd.add_argument('file', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'ui':
            from .web import run_ui
            run_ui(args.port, not args.no_browser)
            return 0
        if args.command == 'education':
            from .assistant import education
            print(json.dumps(education(), indent=2))
            return 0
        if args.command == 'simulate':
            from .assistant import simulate
            if args.file.stat().st_size > 1024*1024:
                raise ValueError('Input exceeds 1 MiB')
            print(json.dumps(simulate(json.loads(args.file.read_text(encoding='utf8')),args.trials,args.seed),indent=2))
            return 0
        if args.command == 'demo':
            data = {'events': [dict(event_id='A', game_id='G1', name='Synthetic outcome A', american_odds=100,
                                   fair_prob_override='0.5', evidence_tier=3)],
                    'tickets': [dict(ticket_id='T1', leg_ids=['A'], stake='10')], 'target_gross': '20'}
        else:
            if args.file.stat().st_size > 1024 * 1024:
                raise ValueError('Input exceeds 1 MiB')
            data = json.loads(args.file.read_text(encoding='utf8'))
        print(json.dumps(analyze(data), indent=2, default=display))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(2, f'SlipSavvy: {error}\n')
