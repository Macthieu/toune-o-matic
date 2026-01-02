#!/usr/bin/env python3
import json, os, re, subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.expanduser("~/toune-o-matic")
SETTINGS_YAML = os.path.join(BASE_DIR, "config", "settings.yaml")

def load_api_key():
    if not os.path.exists(SETTINGS_YAML):
        return ""
    txt = open(SETTINGS_YAML, "r", encoding="utf-8", errors="ignore").read()
    m = re.search(r'^\s*key:\s*"(.*?)"\s*$', txt, flags=re.M) or \
        re.search(r"^\s*key:\s*'(.*?)'\s*$", txt, flags=re.M) or \
        re.search(r"^\s*key:\s*(\S+)\s*$", txt, flags=re.M)
    return (m.group(1).strip() if m else "")

API_KEY = load_api_key()

ALLOWED_UNITS = {
  "toune-api": "toune-o-matic.service",
  "toune-pl": "toune-pl.service",
  "toune-bt": "toune-bt.service",
  "nginx": "nginx.service",
  "mpd": "mpd.service",
}

def run(cmd, timeout=10):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()

def jreply(h, payload, code=200):
    b = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.end_headers()
    h.wfile.write(b)

def qparam(qs, name, default=""):
    v = qs.get(name, [""])
    return (v[0] if v else default).strip()

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _auth(self):
        if not API_KEY:
            return True
        return self.headers.get("X-API-Key","") == API_KEY

    def do_GET(self):
        if not self._auth():
            return jreply(self, {"ok": False, "error": "unauthorized"}, 401)

        u = urlparse(self.path)
        qs = parse_qs(u.query)

        if u.path in ("/", "/health"):
            return jreply(self, {"ok": True})

        if u.path == "/units":
            return jreply(self, {"ok": True, "units": list(ALLOWED_UNITS.keys())})

        if u.path == "/logs":
            unit_key = qparam(qs, "unit", "toune-api")
            n = int(qparam(qs, "n", "200") or "200")
            n = max(20, min(2000, n))

            unit = ALLOWED_UNITS.get(unit_key)
            if not unit:
                return jreply(self, {"ok": False, "error": "bad unit"}, 400)

            rc, out = run(["journalctl", "-u", unit, "-n", str(n), "--no-pager", "-o", "short-iso"], timeout=10)
            return jreply(self, {"ok": rc == 0, "unit": unit_key, "lines": out.splitlines() if out else []},
                          200 if rc == 0 else 500)

        return jreply(self, {"ok": False, "error": "not found"}, 404)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=11003)
    args = ap.parse_args()
    httpd = HTTPServer((args.host, args.port), H)
    print(f"toune-logs API on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
