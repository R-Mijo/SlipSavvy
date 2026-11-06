import unittest
from slipsavvy.assistant import simulate, education, odds_price

def ticket(p='0.6', n=2):
    return {'stake':'5','assume_conditional_independence':True,'legs':[
        {'id':str(i),'american_odds':100,'win_probability':p} for i in range(n)]}

class AssistantTests(unittest.TestCase):
    def test_odds_only_starting_point_is_opt_in_and_labeled(self):
        d=ticket();d['use_price_implied_probabilities']=True
        for leg in d['legs']:del leg['win_probability']
        r=simulate(d,1000)
        self.assertEqual(r['analytic_model_win_percent'],25)
        self.assertIn('not a prediction',r['score_label'])
        self.assertIn('Price-implied',r['legs'][0]['probability_basis'])
        self.assertEqual(r['expected_net_under_model'],0)
    def test_100000_runs_match_exact_probability(self):
        r=simulate(ticket(),100000,42)
        self.assertEqual(r['trials'],100000)
        self.assertEqual(r['analytic_model_win_percent'],36)
        self.assertLess(abs(r['simulation_win_percent']-36),0.7)
        self.assertEqual(r['ticket_hits']+r['ticket_losses'],100000)
    def test_reproducible(self):
        a=simulate(ticket(),1000,1); b=simulate(ticket(),1000,1)
        self.assertEqual(a['ticket_hits'],b['ticket_hits'])
    def test_scripts_share_one_scenario_per_trial(self):
        d=ticket(); d['game_scripts']=[{'name':'win','weight':'0.5','probabilities':{'0':'1','1':'1'}},{'name':'lose','weight':'0.5','probabilities':{'0':'0','1':'0'}}]
        r=simulate(d,10000)
        self.assertEqual(r['analytic_model_win_percent'],50)
        self.assertEqual(r['legs'][0]['simulation_hit_percent'],r['simulation_win_percent'])
    def test_six_sixty_percent_legs(self):
        r=simulate(ticket(n=6),1000)
        self.assertAlmostEqual(r['analytic_model_win_percent'],4.6656)
    def test_quoted_payout(self):
        d=ticket();d['quoted_decimal_price']='100';r=simulate(d,1000)
        self.assertEqual(r['gross_if_win'],500);self.assertEqual(r['net_if_win'],495)
    def test_invalid_inputs(self):
        for p in ['NaN','Infinity','-0.1','1.01',True,None]:
            with self.assertRaises(ValueError):simulate(ticket(p),1000)
        for n in [True,0,1000001]:
            with self.assertRaises(ValueError):simulate(ticket(),n)
    def test_independence_required(self):
        d=ticket();d['assume_conditional_independence']=False
        with self.assertRaises(ValueError):simulate(d,1000)
    def test_scenario_validation(self):
        d=ticket();d['game_scripts']=[{'name':'bad','weight':'0.9','probabilities':{'0':'0.5','1':'0.5'}}]
        with self.assertRaises(ValueError):simulate(d,1000)
    def test_education_odds(self):
        self.assertEqual(odds_price(-200),1.5)
        e=education();self.assertEqual(e['five_to_five_hundred']['break_even_percent'],1)
        self.assertAlmostEqual(e['independent_legs'][-1]['ticket_win_percent'],4.6656)
    def test_extreme_probabilities(self):
        self.assertEqual(simulate(ticket('0'),1000)['ticket_hits'],0)
        self.assertEqual(simulate(ticket('1'),1000)['ticket_hits'],1000)
