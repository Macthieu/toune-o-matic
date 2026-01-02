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

def run(cmd, timeout=30):
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

        # ---- playlists ----
        if u.path == "/playlists":
            rc, out = run(["mpc", "lsplaylists"])
            pls = [x.strip() for x in out.splitlines() if x.strip()] if rc == 0 else []
            return jreply(self, {"ok": rc == 0, "playlists": pls, "raw": "" if rc == 0 else out}, 200 if rc == 0 else 500)

        # ---- queue ----
        if u.path == "/queue/clear":
            rc, out = run(["mpc", "clear"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/queue/load":
            name = qparam(qs, "name")
            mode = qparam(qs, "mode", "replace")  # replace|append
            if not name:
                return jreply(self, {"ok": False, "error": "missing name"}, 400)

            if mode == "replace":
                run(["mpc", "clear"])

            rc, out = run(["mpc", "load", name])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/queue/list":
            limit = int(qparam(qs, "limit", "30") or "30")
            rc1, status = run(["mpc", "status"])
            rc2, plist = run(["mpc", "playlist"])
            lines = [l for l in plist.splitlines() if l.strip()]
            return jreply(self, {
                "ok": (rc2 == 0),
                "status": status if rc1 == 0 else "",
                "queue": lines[:max(0, limit)]
            }, 200 if rc2 == 0 else 500)

        # ---- player ----
        if u.path == "/player/play":
            rc, out = run(["mpc", "play"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/player/pause":
            rc, out = run(["mpc", "pause"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/player/toggle":
            rc, out = run(["mpc", "toggle"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/player/stop":
            rc, out = run(["mpc", "stop"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/player/next":
            rc, out = run(["mpc", "next"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/player/prev":
            rc, out = run(["mpc", "prev"])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        # ---- playlist management ----
        if u.path == "/playlist/save":
            name = qparam(qs, "name")
            if not name:
                return jreply(self, {"ok": False, "error": "missing name"}, 400)
            run(["mpc", "rm", name])
            rc, out = run(["mpc", "save", name])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        if u.path == "/playlist/delete":
            name = qparam(qs, "name")
            if not name:
                return jreply(self, {"ok": False, "error": "missing name"}, 400)
            rc, out = run(["mpc", "rm", name])
            return jreply(self, {"ok": rc == 0, "raw": out}, 200 if rc == 0 else 500)

        return jreply(self, {"ok": False, "error": "not found"}, 404)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=11002)
    args = ap.parse_args()
    httpd = HTTPServer((args.host, args.port), H)
    print(f"toune-pl API on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
