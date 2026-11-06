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
        self.assertIsNone(r['expected_net_under_model'])
        self.assertIn('Unavailable', r['expected_net_status'])
    def test_two_way_devig_and_expected_loss_under_balanced_market_assumption(self):
        d = {'stake':'10', 'assume_conditional_independence':True, 'legs':[
            {'id':str(i), 'american_odds':-110, 'opposing_american_odds':-110}
            for i in range(2)]}
        r = simulate(d, 1000, 42)
        self.assertEqual(r['analytic_model_win_percent'], 25)
        self.assertAlmostEqual(r['expected_net_under_model'], -0.8884297520661157)
        self.assertIn('two-way', r['legs'][0]['probability_basis'])
        self.assertAlmostEqual(r['legs'][0]['market_overround_percent'], 4.761904761904762)
    def test_asymmetric_opposing_prices_accept_strings(self):
        r = simulate({'stake':'10', 'legs':[
            {'id':'a', 'american_odds':'-110', 'opposing_american_odds':'+100'}]}, 1000)
        self.assertAlmostEqual(r['analytic_model_win_percent'], 100 * 22 / 43)
        self.assertAlmostEqual(r['expected_net_under_model'], -10 / 43)
    def test_explicit_estimate_takes_precedence_over_two_way_price_estimate(self):
        d=ticket(); d['legs'][0].update(american_odds=-110, opposing_american_odds=-110)
        r=simulate(d,1000)
        self.assertEqual(r['legs'][0]['model_estimated_win_percent'],60)
        self.assertIn('User-supplied estimate',r['legs'][0]['probability_basis'])
        self.assertIsNotNone(r['expected_net_under_model'])
    def test_mixed_price_only_and_two_way_legs_withhold_expected_net(self):
        d={'use_price_implied_probabilities':True,'assume_conditional_independence':True,'legs':[
            {'id':'a','american_odds':-110,'opposing_american_odds':-110},
            {'id':'b','american_odds':-110}]}
        r=simulate(d,1000)
        self.assertIsNone(r['expected_net_under_model'])
        self.assertEqual(r['legs'][0]['model_estimated_win_percent'],50)
        self.assertIsNone(r['legs'][1]['market_overround_percent'])
    def test_game_scripts_supply_probabilities_even_if_base_is_price_only(self):
        d=ticket();d['use_price_implied_probabilities']=True
        for leg in d['legs']:del leg['win_probability']
        d['game_scripts']=[{'name':'Own assumptions','weight':'1','probabilities':{'0':'0.6','1':'0.6'}}]
        r=simulate(d,1000)
        self.assertEqual(r['analytic_model_win_percent'],36)
        self.assertAlmostEqual(r['expected_net_under_model'],2.2)
        self.assertIn('game-script',r['legs'][0]['probability_basis'])
    def test_quoted_price_does_not_make_single_sided_probabilities_known(self):
        d={'use_price_implied_probabilities':True,'quoted_decimal_price':'3','legs':[
            {'id':'a','american_odds':-110}]}
        r=simulate(d,1000)
        self.assertEqual(r['gross_if_win'],15)
        self.assertIsNone(r['expected_net_under_model'])
    def test_invalid_opposing_odds_rejected(self):
        for value in [True,-50,0,'NaN',-110.5,'',100001]:
            with self.subTest(value=value),self.assertRaises(ValueError):
                simulate({'legs':[{'id':'a','american_odds':-110,'opposing_american_odds':value}]},1000)
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
