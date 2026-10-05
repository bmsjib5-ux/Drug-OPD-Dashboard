#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Local dev server + CORS proxy for the BMS-Session HOSxP API.
#
# Why this exists:
#   The HOSxP tunnel (*.tunnel.hosxp.net) does NOT send CORS headers on /api/sql,
#   so a page served from http://localhost:PORT cannot fetch it directly (the
#   browser blocks it), and opening the file with file:// sends Origin: null
#   which the tunnel rejects too. This server forwards
#       /proxy?url=<https://...hosxp.net/...>
#   server-side and adds the CORS headers back.
#
#   index.html only routes through the proxy when opened on localhost
#   (see proxied() in index.html).

#   Usage: python serve.py [PORT] [--open] [--host=IP]
#   --open    = open the browser once the port is bound (start.bat passes it).
#   --host=IP = address to use as the main URL (default: this PC's own LAN IP,
#               the one Windows uses to reach the network). Other PCs open
#               http://<main IP>:PORT/index.html
#   start.bat falls back to serve.ps1 (same job, PowerShell) when Python is missing.

import functools, os, socket, sys, webbrowser
import urllib.request, urllib.parse, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

_args = [a for a in sys.argv[1:] if not a.startswith('--')]
PORT = int(_args[0]) if _args else 8797
OPEN = '--open' in sys.argv[1:]
HOST = next((a.split('=', 1)[1].strip() for a in sys.argv[1:] if a.startswith('--host=')), '')
ROOT = os.path.dirname(os.path.abspath(__file__))   # serve this folder, whatever the current directory is
ALLOW_HOSTS = ('hosxp.net',)        # only proxy to HOSxP hosts (not an open proxy)
                                   # bare hosxp.net (PasteJSON) + any *.hosxp.net tunnel
USER_AGENT = 'BMS-DrugMachine/1.0'  # hosxp.net answers 403 HTML when no User-Agent is sent


# Hospital networks often reach the internet only through a proxy: use the one set
# in Windows (urllib reads it from the registry / HTTPS_PROXY), with no extra setup.
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler(urllib.request.getproxies())))


def describe(e):
    """Readable cause: DNS / TLS certificate / proxy / timeout."""
    r = getattr(e, 'reason', None)
    msg = '%s: %s' % (type(r or e).__name__, r or e)
    low = msg.lower()
    if 'certificate' in low:
        msg += ' (HTTPS is inspected by a firewall/proxy whose certificate this PC does not trust)'
    elif 'getaddrinfo' in low or 'name or service' in low:
        msg += ' (DNS cannot resolve hosxp.net - no internet or DNS blocked)'
    elif 'timed out' in low:
        msg += ' (timeout - internet blocked or very slow)'
    elif 'proxy' in low or '407' in low:
        msg += ' (proxy needs a login)'
    return msg


def check_hosxp():
    """Startup check: can this PC reach hosxp.net?"""
    req = urllib.request.Request('https://hosxp.net/phapi/PasteJSON?Action=GET&code=test',
                                 headers={'User-Agent': USER_AGENT})
    try:
        urllib.request.urlopen(req, timeout=15).close()
    except urllib.error.HTTPError:
        pass   # an HTTP answer still means the network path works
    except Exception as e:
        print('  hosxp.net:  CANNOT CONNECT - ' + describe(e))
        print('              Check internet / proxy / firewall of THIS PC. The page will show HTTP 502.')
        proxies = urllib.request.getproxies()
        print('              Proxy in use: ' + (proxies.get('https') or 'none'))
        return
    print('  hosxp.net:  OK (this PC can reach HOSxP)')


class Handler(SimpleHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Accept, Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/proxy?') or self.path.startswith('/proxy/'):
            return self._proxy()
        return super().do_GET()

    def _proxy(self):
        qs = urllib.parse.urlparse(self.path).query
        target = urllib.parse.parse_qs(qs).get('url', [''])[0]
        if not target:
            self.send_error(400, 'missing url')
            return
        host = urllib.parse.urlparse(target).hostname or ''
        ok = any(host == h or host.endswith('.' + h) for h in ALLOW_HOSTS)
        if not (target.startswith('https://') and ok):
            self.send_error(403, 'target host not allowed')
            return

        req = urllib.request.Request(target, method='GET')
        auth = self.headers.get('Authorization')
        if auth:
            req.add_header('Authorization', auth)
        req.add_header('Accept', 'application/json')
        req.add_header('User-Agent', USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                ctype = r.headers.get('Content-Type', 'application/json')
                code = r.getcode()
        except urllib.error.HTTPError as e:
            # pass the real body back so the page can show the SQL error text (400/409)
            body = e.read()
            ctype = e.headers.get('Content-Type', 'text/plain')
            code = e.code
        except Exception as e:
            body = ('proxy error: ' + describe(e)).encode('utf-8')
            ctype = 'text/plain; charset=utf-8'
            code = 502

        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the console quiet


class Server(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second copy bind the same port silently;
    # without it a second start.bat gets a clear "port in use" error instead.
    allow_reuse_address = os.name != 'nt'


def lan_addresses():
    """IPv4 addresses other PCs can use to reach this one."""
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith(('127.', '169.254.')):
                ips.add(ip)
    except OSError:
        pass
    return sorted(ips)


def main_ip():
    """The LAN IP Windows uses for outgoing traffic. A UDP connect sends nothing."""
    for target in ('hosxp.net', '8.8.8.8', '10.255.255.255'):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((target, 443))
            ip = s.getsockname()[0]
            if not ip.startswith(('127.', '0.', '169.254.')):
                return ip
        except OSError:
            pass
        finally:
            s.close()
    ips = lan_addresses()
    return ips[0] if ips else 'localhost'


if __name__ == '__main__':
    main = HOST or main_ip()
    url = 'http://%s:%d/index.html' % (main, PORT)
    try:
        # '' = all addresses, so other PCs on the network can open http://<this-PC-IP>:PORT/
        httpd = Server(('', PORT), functools.partial(Handler, directory=ROOT))
    except OSError as e:
        print('\nCould not start the server on port %d : %s' % (PORT, e))
        print('Is this tool already running in another window? Close it, or change PORT in start.bat.')
        sys.exit(1)
    print('=' * 62)
    print('  BMS Drug Machine - local server + HOSxP API proxy (Python)')
    print('  MAIN URL:   ' + url)
    print('              (give this address to the other PCs)')
    print('  This PC:    http://localhost:%d/index.html' % PORT)
    for ip in lan_addresses():
        if ip != main:
            print('  Other IP:   http://%s:%d/index.html' % (ip, PORT))
    print('  (other PCs cannot connect? run Enable-LAN.bat once to open the firewall)')
    check_hosxp()
    print('  Press Ctrl+C to stop.')
    print('=' * 62)
    sys.stdout.flush()
    if OPEN:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
