"""Personal loopback UI; no hosted accounts or wagering."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import secrets
import threading
import webbrowser
from .assistant import simulate
from .weather import forecast


def create_ui_server(port=8766):
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Invalid port')
    token=secrets.token_urlsafe(32)
    nonce=secrets.token_urlsafe(24)
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,value,html=False):
            body=value.encode('utf8') if html else json.dumps(value).encode('utf8')
            self.send_response(status)
            for k,v in {'Content-Type':'text/html; charset=utf-8' if html else 'application/json',
                'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                'X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
                'Content-Security-Policy':f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}.items():self.send_header(k,v)
            self.end_headers();self.wfile.write(body)
        def host_ok(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            if not self.host_ok():return self.send(403,{'error':'Unexpected host'})
            if self.path!='/':return self.send(404,{'error':'Not found'})
            self.send(200,Path(__file__).with_name('ui.html').read_text(encoding='utf8').replace('__TOKEN__',token).replace('__NONCE__',nonce),True)
        def do_POST(self):
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if not self.host_ok() or self.headers.get('X-SlipSavvy-Token')!=token or self.headers.get('Origin',origin)!=origin or self.headers.get('Sec-Fetch-Site')=='cross-site':return self.send(403,{'error':'Local session authorization required'})
            if self.headers.get_content_type()!='application/json':return self.send(415,{'error':'JSON required'})
            if not lock.acquire(blocking=False):return self.send(429,{'error':'A task is already running'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1024*1024:raise ValueError('Request exceeds size limit')
                self.connection.settimeout(15)
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):raise ValueError('Object required')
                if self.path=='/api/simulate': result=simulate(data.get('ticket'),trials=100000,seed=42)
                elif self.path=='/api/weather':result=forecast(data.get('latitude'),data.get('longitude'))
                else:return self.send(404,{'error':'Not found'})
                self.send(200,result)
            except (ValueError,TypeError,KeyError,OverflowError):self.send(400,{'error':'Invalid data. Check probabilities, odds, scenario weights and assumptions.'})
            except (OSError,TimeoutError):self.send(502,{'error':'Weather service unavailable. No substitute weather data was invented.'})
            finally:lock.release()
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def run_ui(port=8766,open_browser=True):
    server=create_ui_server(port)
    url=f'http://127.0.0.1:{server.server_port}'
    print(f'SlipSavvy: {url}',flush=True)
    if open_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
