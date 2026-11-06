import json
import re
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from slipsavvy.web import create_ui_server
from slipsavvy.weather import forecast


class AssistantWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_ui_server(0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        cls.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with cls.opener.open(cls.base) as response:
            cls.page=response.read().decode()
            cls.token=re.search("X-SlipSavvy-Token':'([^']+)'",cls.page).group(1)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(3)
    def request(self,path,payload,**headers):
        h={'Content-Type':'application/json','X-SlipSavvy-Token':self.token,'Origin':self.base};h.update(headers)
        return self.opener.open(urllib.request.Request(self.base+path,json.dumps(payload).encode(),h),timeout=10)
    def test_page_and_simulation(self):
        self.assertIn('Learn the odds',self.page)
        d={'ticket':{'legs':[{'id':'a','american_odds':100,'win_probability':'0.5'}]}}
        with self.request('/api/simulate',d) as response:
            r=json.load(response)
        self.assertEqual(r['trials'],100000)
        self.assertEqual(r['analytic_model_win_percent'],50)
    def test_unauthorized_rejected(self):
        for h in [{'X-SlipSavvy-Token':''},{'Host':'evil.invalid'},{'Origin':'https://evil.invalid'}]:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/simulate',{},**h)
            self.assertEqual(caught.exception.code,403)
    def test_bad_payload_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/simulate',[])
        self.assertEqual(caught.exception.code,400)
    def test_weather_input_validation(self):
        for coords in [(True,1),(91,0),(0,float('nan'))]:
            with self.assertRaises(ValueError):forecast(*coords)
    def test_weather_failure_not_fabricated(self):
        with patch('slipsavvy.web.forecast',side_effect=OSError('offline')):
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/weather',{'latitude':40,'longitude':-74})
        self.assertEqual(caught.exception.code,502)
