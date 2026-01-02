#!/usr/bin/env python3
import json, os, re, subprocess, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = "/home/pi/toune-o-matic"
SETTINGS_YAML = os.path.join(BASE_DIR, "config", "settings.yaml")
STATE_FILE = os.path.join(BASE_DIR, "config", "bt_selected.json")
MPD_CONF = "/etc/mpd.conf"

def load_api_key():
    if not os.path.exists(SETTINGS_YAML):
        return ""
    txt = open(SETTINGS_YAML, "r", encoding="utf-8", errors="ignore").read()
    m = re.search(r'^\s*key:\s*"(.*?)"\s*$', txt, flags=re.M) \
        or re.search(r"^\s*key:\s*'(.*?)'\s*$", txt, flags=re.M) \
        or re.search(r"^\s*key:\s*(\S+)\s*$", txt, flags=re.M)
    return (m.group(1).strip() if m else "")

API_KEY = load_api_key()

def run(cmd, timeout=30):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()

def bt_list_known():
    # bluetoothctl devices
    rc, out = run(["bluetoothctl", "devices"], timeout=10)
    devs = []
    if rc == 0:
        for line in out.splitlines():
            # Device AA:BB:CC:DD:EE:FF Name
            m = re.match(r"^\s*Device\s+([0-9A-F:]{17})\s+(.+?)\s*$", line, flags=re.I)
            if m:
                devs.append({"addr": m.group(1).upper(), "name": m.group(2).strip()})
    devs.sort(key=lambda d: d["name"].lower())
    return {"ok": True, "devices": devs, "count": len(devs)}

def bt_scan(timeout_s=12):
    timeout_s = max(3, min(25, int(timeout_s)))
    rc, out = run(["bluetoothctl", "--timeout", str(timeout_s), "scan", "on"], timeout=timeout_s+10)

    found = {}
    for line in out.splitlines():
        m = re.search(r"\bDevice\s+([0-9A-F:]{17})\s+(.+)$", line, flags=re.I)
        if m:
            addr = m.group(1).upper()
            name = re.sub(r"^Name:\s*", "", m.group(2).strip(), flags=re.I).strip()
            if name:
                found[addr] = name

    devices = [{"addr": a, "name": n} for a, n in sorted(found.items(), key=lambda x: x[1].lower())]
    return {"ok": True, "timeout": timeout_s, "count": len(devices), "devices": devices, "raw": out[:2000]}

def load_selected():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        return json.load(open(STATE_FILE, "r", encoding="utf-8"))
    except Exception:
        return None

def save_selected(addr, name=""):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    data = {"addr": addr.upper(), "name": name, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(data, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return data

def apply_mpd_bluetooth(addr):
    # Remplace le device du bloc audio_output name "Bluetooth"
    txt = open(MPD_CONF, "r", encoding="utf-8", errors="ignore").read()

    pat = r'(audio_output\s*\{[^}]*name\s*"Bluetooth"[^}]*device\s*")bluealsa:DEV=[0-9A-F:]{17},PROFILE=a2dp(".*?\})'
    repl = r'\1bluealsa:DEV=%s,PROFILE=a2dp\2' % addr.upper()

    new_txt, n = re.subn(pat, repl, txt, flags=re.S|re.I)
    if n != 1:
        raise RuntimeError(f"Bloc Bluetooth introuvable ou multiple (n={n}). Vérifie mpd.conf: output name \"Bluetooth\" + device \"bluealsa:DEV=...\"")

    # backup + write
    bk = MPD_CONF + ".bak." + time.strftime("%Y-%m-%d_%H%M%S")
    subprocess.run(["cp", "-a", MPD_CONF, bk], check=False)
    open(MPD_CONF, "w", encoding="utf-8").write(new_txt)

    # restart mpd
    subprocess.run(["systemctl", "restart", "mpd"], check=True)

def bt_connect(addr):
    # pair/trust/connect (idempotent-ish)
    steps = [
        ["bluetoothctl", "pair", addr],
        ["bluetoothctl", "trust", addr],
        ["bluetoothctl", "connect", addr],
    ]
    out_all = []
    for cmd in steps:
        rc, out = run(cmd, timeout=30)
        out_all.append(f"$ {' '.join(cmd)}\n{out}\n")
    return "\n".join(out_all)[:4000]

class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence
        return

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self):
        if self.path.startswith("/api/bt/health"):
            return True
        k = self.headers.get("X-API-Key", "") or ""
        return (API_KEY and k.strip() == API_KEY)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n <= 0:
            return {}
        raw = self.rfile.read(n).decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        if not self._auth_ok():
            return self._json(401, {"ok": False, "error": "unauthorized"})

        u = urlparse(self.path)
        if u.path == "/api/bt/health":
            return self._json(200, {"ok": True})

        if u.path == "/api/bt/devices":
            return self._json(200, bt_list_known())

        if u.path == "/api/bt/scan12":
            return self._json(200, bt_scan(12))

        if u.path == "/api/bt/selected":
            return self._json(200, {"ok": True, "selected": load_selected()})

        return self._json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._json(401, {"ok": False, "error": "unauthorized"})

        u = urlparse(self.path)
        if u.path == "/api/bt/selected":
            data = self._read_json()
            addr = (data.get("addr") or "").strip().upper()
            name = (data.get("name") or "").strip()

            if not re.match(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$", addr):
                return self._json(400, {"ok": False, "error": "invalid_addr"})

            sel = save_selected(addr, name)

            # connect + apply mpd.conf + restart mpd
            try:
                btlog = bt_connect(addr)
                apply_mpd_bluetooth(addr)
            except Exception as e:
                return self._json(500, {"ok": False, "selected": sel, "error": str(e)})

            return self._json(200, {"ok": True, "selected": sel, "btlog": btlog})

        return self._json(404, {"ok": False, "error": "not_found"})

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=11001)
    args = ap.parse_args()
    httpd = HTTPServer((args.host, args.port), H)
    print(f"toune-bt-api on http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
