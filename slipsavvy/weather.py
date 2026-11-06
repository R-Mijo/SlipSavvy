"""Optional weather retrieval. No automatic betting-probability adjustments."""
from datetime import datetime, timezone
import json
import math
from urllib.parse import urlencode
from urllib.request import urlopen


def forecast(latitude, longitude):
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (latitude,longitude)) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError('Valid stadium latitude and longitude required')
    params = {'latitude':latitude,'longitude':longitude,'hourly':'temperature_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m',
              'temperature_unit':'fahrenheit','wind_speed_unit':'mph','timezone':'UTC','forecast_days':7}
    url='https://api.open-meteo.com/v1/forecast?'+urlencode(params)
    with urlopen(url, timeout=12) as response:
        raw=response.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('Weather response too large')
    data=json.loads(raw)
    if not isinstance(data,dict) or not isinstance(data.get('hourly'),dict) or not isinstance(data.get('hourly_units'),dict):
        raise ValueError('Weather response is incomplete')
    return {'provider':'Open-Meteo','source_url':url,'attribution':'Weather data by Open-Meteo.com',
            'attribution_url':'https://open-meteo.com/','data_license':'https://creativecommons.org/licenses/by/4.0/',
            'fetched_at':datetime.now(timezone.utc).isoformat(),'timezone':'UTC','forecast':data,
            'note':'Forecast, not an observation. Match kickoff UTC time, stadium coordinates and roof status yourself. Free endpoint is for noncommercial evaluation; commercial deployment needs provider terms reviewed.'}
