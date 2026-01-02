from flask import Blueprint, request, jsonify
import subprocess
import re
import time

bp = Blueprint("bluetooth", __name__, url_prefix="/api/bluetooth")

def _run(cmd, timeout=30):
    try:
        # On utilise Popen pour éviter certains blocages
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return (p.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return str(e)

@bp.get("/paired")
def paired():
    # Récupère les appareils appairés
    raw = _run(["bluetoothctl", "devices", "Paired"], timeout=10)
    devices = []
    seen = set()
    
    clean_raw = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    
    for line in clean_raw.splitlines():
        m = re.search(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)$", line)
        if m:
            mac = m.group(1).upper()
            name = m.group(2).strip()
            if mac not in seen:
                # Vérif connexion rapide
                info = _run(["bluetoothctl", "info", mac], timeout=2)
                is_conn = "Connected: yes" in info
                devices.append({"mac": mac, "name": name, "connected": is_conn})
                seen.add(mac)
                
    return jsonify({"ok": True, "devices": devices})

@bp.post("/scan")
def scan():
    _run(["bluetoothctl", "power", "on"])
    # Scan court
    _run(["bluetoothctl", "--timeout", "5", "scan", "on"], timeout=6)
    dev_log = _run(["bluetoothctl", "devices"], timeout=5)
    
    devices = []
    seen = set()
    clean_log = re.sub(r"\x1b\[[0-9;]*m", "", dev_log)
    
    for line in clean_log.splitlines():
        m = re.search(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)$", line)
        if m:
            mac = m.group(1).upper()
            if mac not in seen:
                devices.append({"mac": mac, "name": m.group(2).strip()})
                seen.add(mac)
    return jsonify({"ok": True, "devices": devices})

@bp.post("/connect")
def connect():
    mac = (request.json or {}).get("mac", "")
    if not mac: return jsonify({"ok": False}), 400

    # 1. Trust (Important pour les enceintes)
    _run(["bluetoothctl", "trust", mac], timeout=5)
    
    # 2. Connect
    res = _run(["bluetoothctl", "connect", mac], timeout=25)
    
    # 3. Vérification
    info = _run(["bluetoothctl", "info", mac], timeout=5)
    
    if "Connected: yes" in info:
        return jsonify({"ok": True, "connected": True, "details": res})
    else:
        return jsonify({"ok": False, "error": "Échec connexion", "details": res})

@bp.post("/disconnect")
def disconnect():
    mac = (request.json or {}).get("mac", "")
    _run(["bluetoothctl", "disconnect", mac], timeout=10)
    return jsonify({"ok": True})