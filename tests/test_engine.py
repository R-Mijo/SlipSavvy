from fractions import Fraction as F
from dataclasses import replace
import unittest

from slipsavvy import (BinaryEvent, PromoBoost, Ticket, StateEngine as SOL,
    PayoutModeler as WINSTON, ProbabilityModeler as LISA,
    RiskAnalyzer as PAX, ScenarioAuditor as GUS, StakeOptimizer as LUNA)


def event(eid='A', group='G1', p='0.5', **kwargs):
    return BinaryEvent(eid, group, eid, 100, fair_prob_override=p, **kwargs)


class SlipSavvyTests(unittest.TestCase):
    def test_exclusive_50_50_group_conserves_mass(self):
        events = [event('A'), event('B')]
        ledger = SOL.build_state_ledger(events, [Ticket('T', ('A',), 10)])
        probabilities = {row['bits']: row['probability'] for row in ledger['states']}
        self.assertEqual(probabilities, {(0, 0): 0, (0, 1): F(1, 2), (1, 0): F(1, 2), (1, 1): 0})
        self.assertEqual(sum(probabilities.values()), 1)

    def test_partial_disjoint_outcomes_have_explicit_remainder(self):
        ledger = SOL.build_state_ledger([event('A', p='0.2'), event('B', p='0.3')], [Ticket('T', ('A',), 10)])
        self.assertEqual(ledger['states'][0]['probability'], F(1, 2))
        self.assertEqual(sum(s['probability'] for s in ledger['states']), 1)

    def test_invalid_probabilities_never_normalized_into_validity(self):
        for p in ['1.2', '-0.2', 'nan', 'inf', True]:
            with self.subTest(p=p), self.assertRaises(ValueError):
                event(p=p)
        with self.assertRaises(ValueError):
            SOL.build_state_ledger([event('A', p='0.9'), event('B', p='0.9')], [Ticket('T', ('A',), 10)])

    def test_impossible_ticket_and_duplicate_ids_rejected(self):
        for events, tickets in [
            ([event('A'), event('B')], [Ticket('T', ('A', 'B'), 10)]),
            ([event('A'), event('A')], [Ticket('T', ('A',), 10)]),
            ([event()], [Ticket('T', ('unknown',), 10)]),
            ([event()], [Ticket('T', ('A',), 10), Ticket('T', ('A',), 10)]),
        ]:
            with self.subTest(events=events), self.assertRaises(ValueError):
                SOL.build_state_ledger(events, tickets)
        with self.assertRaises(ValueError):
            Ticket('T', ('A', 'A'), 10)

    def test_independence_is_required_and_declared(self):
        events = [event(), event('B', 'G2')]
        tickets = [Ticket('T', ('A', 'B'), 10)]
        with self.assertRaises(ValueError):
            SOL.build_state_ledger(events, tickets)
        ledger = SOL.build_state_ledger(events, tickets, assume_independent_groups=True)
        self.assertEqual({s['probability'] for s in ledger['states']}, {F(1, 4)})

    def test_supplied_dependence_changes_actual_state_risk(self):
        events = [event(), event('B', 'G2')]
        tickets = [Ticket('T', ('A', 'B'), 10)]
        joint = {(0, 0): '0.5', (1, 1): '0.5'}
        ledger = SOL.build_state_ledger(events, tickets, joint_distribution=joint)
        self.assertEqual(PAX.evaluate_risk(ledger, 40)['p_target'], F(1, 2))
        independent = SOL.build_state_ledger(events, tickets, assume_independent_groups=True)
        self.assertEqual(PAX.evaluate_risk(independent, 40)['p_target'], F(1, 4))

    def test_bad_joint_distribution_rejected(self):
        events = [event(), event('B', 'G2')]
        tickets = [Ticket('T', ('A',), 10)]
        for joint in [{(0, 0): 1}, {(0, 0): '-0.2', (1, 1): '1.2'}, {(0, 0): '0.4', (1, 1): '0.4'}, {(True, 0): 1}]:
            with self.subTest(joint=joint), self.assertRaises(ValueError):
                SOL.build_state_ledger(events, tickets, joint_distribution=joint)
        with self.assertRaises(ValueError):
            Ticket('T', ('A',), 10, correlation_cov='0.1')

    def test_exact_american_prices_and_devig(self):
        self.assertEqual(WINSTON.american_to_decimal(-135), F(47, 27))
        self.assertEqual(LISA.devig_two_way(-110, -110), (F(1, 2), F(1, 2)))
        self.assertEqual(sum(LISA.devig_multi_way([200, 200, 200])), 1)
        with self.assertRaises(ValueError):
            LISA.event_fair_prob(BinaryEvent('A', 'G', 'A', 100))
        for price in [0, 50, -50, True, 100.0]:
            with self.assertRaises(ValueError):
                WINSTON.american_to_decimal(price)

    def test_boost_cap_only_split_when_rules_explicitly_allow(self):
        events = {'A': BinaryEvent('A', 'G', 'A', 200, fair_prob_override='0.3')}
        boost = PromoBoost('B', '0.5', '10', allow_split_stake=True)
        ticket = Ticket('T', ('A',), '12.50', boost)
        pay = WINSTON.calculate_ticket_payout(ticket, events)
        self.assertEqual(pay['gross_return'], F(95, 2))
        self.assertEqual(pay['boosted_stake_portion'], 10)
        self.assertEqual(pay['unboosted_stake_portion'], F(5, 2))
        self.assertEqual(WINSTON.expected_net_return('0.3', pay['gross_return'], ticket.stake), F(7, 4))
        with self.assertRaises(ValueError):
            WINSTON.calculate_ticket_payout(replace(ticket, boost=replace(boost, allow_split_stake=False)), events)

    def test_promotion_expiry_minimum_odds_and_use_limits(self):
        events = [event()]
        for boost in [PromoBoost('P', '.5', 10, expired=True), PromoBoost('P', '.5', 10, min_american_odds=200)]:
            with self.assertRaises(ValueError):
                SOL.build_state_ledger(events, [Ticket('T', ('A',), 5, boost)])
        promo = PromoBoost('P', '.5', 10)
        with self.assertRaises(ValueError):
            SOL.build_state_ledger(events, [Ticket('T1', ('A',), 5, promo), Ticket('T2', ('A',), 5, promo)])

    def test_no_rounding_a_near_miss_into_a_target(self):
        ticket = Ticket('T', ('A',), '149.995')
        ledger = SOL.build_state_ledger([event()], [ticket])
        self.assertEqual(ledger['ticket_payouts']['T']['gross_return'], F(29999, 100))
        self.assertEqual(PAX.evaluate_risk(ledger, 300)['p_target'], 0)
        self.assertEqual(PAX.evaluate_risk(ledger, '299.99')['p_target'], F(1, 2))

    def test_negative_stakes_and_nonfinite_inputs(self):
        for value in [0, -1, 'nan', 'inf', True]:
            with self.assertRaises(ValueError):
                Ticket('T', ('A',), value)
        with self.assertRaises(ValueError):
            WINSTON.fractional_kelly('1.2', 2)

    def test_auditor_recomputes_and_defaults_to_unverified(self):
        events = [event()]
        tickets = [Ticket('T', ('A',), 10)]
        ledger = SOL.build_state_ledger(events, tickets)
        risk = PAX.evaluate_risk(ledger, 20)
        self.assertEqual(GUS.audit_portfolio(events, tickets, ledger, risk, 20)['verdict'], 'REVIEW_REQUIRED')
        verified = [replace(events[0], evidence_tier=1, evidence_ref='synthetic-fixture:1')]
        self.assertEqual(GUS.audit_portfolio(verified, tickets, ledger, risk, 20)['verdict'], 'ANALYSIS_READY')
        ledger['states'][0]['probability'] = F(-1, 5)
        ledger['states'][1]['probability'] = F(6, 5)
        self.assertEqual(GUS.audit_portfolio(verified, tickets, ledger, risk, 20)['verdict'], 'REVIEW_REQUIRED')
        with self.assertRaises(ValueError):
            PAX.evaluate_risk(ledger, 20)

    def test_luna_search_reports_grid_optimality_honestly(self):
        result = LUNA.search([event()], [Ticket('T', ('A',), 1)], [0, 5, 10], capital_limit=10, target_gross=20)
        self.assertEqual(result['optimality'], 'OPTIMAL_WITHIN_DECLARED_GRID')
        self.assertEqual(result['best']['stakes'], {'T': 10})
        self.assertEqual(result['best']['risk']['p_target'], F(1, 2))
        limited = LUNA.search([event()], [Ticket('T', ('A',), 1)], [0, 5, 10], capital_limit=10, target_gross=20, max_candidates=2)
        self.assertEqual(limited['optimality'], 'BEST_FOUND_LIMIT_REACHED')

    def test_enumeration_is_bounded(self):
        with self.assertRaises(ValueError):
            SOL.build_state_ledger([event(str(i), str(i)) for i in range(17)], [Ticket('T', ('0',), 1)], assume_independent_groups=True)


if __name__ == '__main__':
    unittest.main()
