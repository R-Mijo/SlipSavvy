"""HTTP capability negotiation plus a real old-client contract fixture."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from server.odds import application, weather_response
from test_venue_weather import report_fixture


class WeatherCompatibilityTests(unittest.TestCase):
    def call(self, report, schema=None):
        data={'totalStake':'10','legs':[l['selection'] for l in report['legs']]}
        raw=json.dumps(data).encode()
        environ={'PATH_INFO':'/api/game-reports','REQUEST_METHOD':'POST','CONTENT_TYPE':'application/json',
                 'CONTENT_LENGTH':str(len(raw)),'HTTP_AUTHORIZATION':'Bearer synthetic-access','wsgi.input':BytesIO(raw)}
        if schema is not None:environ['HTTP_X_SLIPSAVVY_WEATHER_SCHEMA']=schema
        statuses=[]
        calls=[];self.last_build_calls=calls
        class Reports:
            def build(self,data):calls.append(data);return report
        with patch.dict(os.environ,{'ODDS_PREVIEW_TOKEN':'synthetic-access'}),patch('server.odds.report_service',Reports()):
            body=b''.join(application(environ,lambda s,h:statuses.append(s)))
        return statuses[0],json.loads(body)

    def test_missing_header_keeps_old_clients_readable_and_opt_in_preserves_complete_nws_data(self):
        original=report_fixture();unchanged=deepcopy(original)
        for schema in (None,'legacy-v1'):
            status,r=self.call(original,schema)
            self.assertEqual(status,'200 OK')
            self.assertEqual(r['weatherSchema'],'legacy-v1')
            self.assertEqual(r['events'][0]['weather'],{'status':'unavailable','reason':'client_update_required_for_nws_weather'})
            self.assertEqual(r['legs'][0]['weather'],r['events'][0]['weather'])
            self.assertEqual(r['legs'][0]['quote'],original['legs'][0]['quote'])
            self.assertEqual(r['events'][0]['research'],original['events'][0]['research'])
        status,r=self.call(original,'nws-v1')
        self.assertEqual(status,'200 OK')
        self.assertEqual(r['weatherSchema'],'nws-v1')
        self.assertEqual(r['events'][0]['weather'],original['events'][0]['weather'])
        self.assertEqual(r['legs'][0]['weather'],original['legs'][0]['weather'])
        self.assertEqual(original,unchanged,'Legacy projection must not modify cached/shared weather')

    def test_legacy_open_meteo_and_not_applicable_states_are_preserved(self):
        for weather in ({'status':'not_applicable','reason':'indoor_or_confirmed_closed_roof'},
                        {'status':'unavailable','reason':'weather_forecast_stale'},
                        {'status':'available','provider':'Open-Meteo','values':{'temperature_2m':40}}):
            r=report_fixture()
            r['events'][0]['weather']=r['legs'][0]['weather']=weather
            projected=weather_response(r)
            self.assertEqual(projected['events'][0]['weather'],weather)
            self.assertEqual(projected['legs'][0]['weather'],weather)

    def test_unknown_capability_is_rejected_before_research_and_fixture_is_real_python_output(self):
        original=report_fixture()
        status,r=self.call(original,'future-unsupported')
        self.assertEqual(status,'400 Bad Request')
        self.assertEqual(self.last_build_calls,[])
        path=Path(__file__).parents[1]/'mobile/tests/fixtures/venue-weather-legacy-v1.json'
        self.assertEqual(json.loads(path.read_text(encoding='utf8')),weather_response(original))


if __name__=='__main__':unittest.main()
