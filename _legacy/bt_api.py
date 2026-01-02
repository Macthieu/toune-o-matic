#!/usr/bin/env python3
import json, os, re, subprocess, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.expanduser("~/toune-o-matic")
SETTINGS_YAML = os.path.join(BASE_DIR, "config", "settings.yaml")
STATE_FILE = os.path.join(BASE_DIR, "config", "bt_selected.json")

def load_api_key():
    # parse minimal YAML: api: / key: "..."
    if not os.path.exists(SETTINGS_YAML):
        return ""
    txt = open(SETTINGS_YAML, "r", encoding="utf-8", errors="ignore").read()
    m = re.search(r'^\s*key:\s*"(.*?)"\s*$', txt, flags=re.M)
    if not m:
        m = re.search(r"^\s*key:\s*'(.*?)'\s*$", txt, flags=re.M)
    if not m:
        m = re.search(r"^\s*key:\s*(\S+)\s*$", txt, flags=re.M)
    return (m.group(1).strip() if m else "")

API_KEY = load_api_key()

def run(cmd, timeout=20):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr

def bt_scan(timeout_s=10):
    # scan on pendant timeout_s, et parse les lignes "Device XX:.. Name"
    # NOTE: bluetoothctl affiche souvent [NEW]/[CHG]/[DEL] — on capte les NEW/CHG.
    cmd = ["bluetoothctl", "--timeout", str(int(timeout_s)), "scan", "on"]
    rc, out = run(cmd, timeout=max(5, int(timeout_s) + 5))

    found = {}  # addr -> name
    for line in out.splitlines():
        # exemples:
        # [NEW] Device 37:39:9B:BC:D9:6F BT-5.0
        # [CHG] Device 37:... Name: BT-5.0
        m = re.search(r"\bDevice\s+([0-9A-F:]{17})\s+(.+)$", line, flags=re.I)
        if m:
            addr = m.group(1).upper()
            name = m.group(2).strip()
            # nettoyer certains formats "Name: xxx"
            name = re.sub(r"^Name:\s*", "", name, flags=re.I).strip()
            if name:
                found[addr] = name

    devices = [{"addr": a, "name": n} for a, n in sorted(found.items(), key=lambda x: x[1].lower())]
    return {"ok": True, "timeout": int(timeout_s), "count": len(devices), "devices": devices}

def load_selected():
    if not os.path.exists(STATE_FILE):
        return {"ok": True, "selected": None}
    try:
        data = json.load(open(STATE_FILE, "r", encoding="utf-8"))
        return {"ok": True, "selected": data}
    except Exception:
        return {"ok": True, "selected": None}

def save_selected(addr, name=""):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    data = {"addr": addr.upper(), "name": name, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(data, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"ok": True, "selected": data}

class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n <= 0:
            return {}
        raw = self.rfile.read(n).decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _auth_ok(self):
        # pas d’auth sur /api/health
        if self.path.startswith("/health"):
            return True
        # même modèle que ton API: header X-API-Key
        k = self.headers.get("X-API-Key", "") or ""
        return (API_KEY and k.strip() == API_KEY)

    def do_GET(self):
        if not self._auth_ok():
            return self._json(401, {"ok": False, "error": "unauthorized"})

        u = urlparse(self.path)
        if u.path == "/health":
            return self._json(200, {"ok": True})

        if u.path == "/scan":
            qs = parse_qs(u.query or "")
            t = int((qs.get("timeout", ["10"])[0] or "10"))
            t = max(3, min(25, t))
            return self._json(200, bt_scan(t))

        if u.path == "/selected":
            return self._json(200, load_selected())

        return self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._json(401, {"ok": False, "error": "unauthorized"})

        u = urlparse(self.path)
        if u.path == "/selected":
            data = self._read_json()
            addr = (data.get("addr") or "").strip().upper()
            name = (data.get("name") or "").strip()
            if not re.match(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$", addr):
                return self._json(400, {"ok": False, "error": "invalid_addr"})
            return self._json(200, save_selected(addr, name))

        return self._json(404, {"ok": False, "error": "not_found"})

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=11001)
    args = ap.parse_args()
    httpd = HTTPServer((args.host, args.port), Handler)
    print(f"toune-bt API on http://{args.host}:{args.port}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
