#!/usr/bin/env python3

import os, yaml, subprocess, re, json, logging
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from mpd import MPDClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = "/home/pi/toune-o-matic"
UI_DIR = os.path.join(BASE_DIR, "ui")
SETTINGS_PATH = os.path.join(BASE_DIR, "config/settings.yaml")

APP = Flask(__name__, static_folder=UI_DIR, static_url_path="")

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

SETTINGS = load_settings()
API_KEY = SETTINGS.get("api", {}).get("key", "secret")

logger.info(f"API Key chargée : {API_KEY[:10]}...")

# --- Middleware Sécurité ---
def require_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("key")
        if key != API_KEY:
            logger.warning(f"Accès refusé : clé invalide {key}")
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# --- Helpers MPD ---
def get_mpd():
    try:
        c = MPDClient()
        c.connect(
            SETTINGS.get("mpd", {}).get("host", "127.0.0.1"),
            SETTINGS.get("mpd", {}).get("port", 6600)
        )
        return c
    except Exception as e:
        logger.error(f"Erreur MPD : {e}")
        return None

# --- ROUTES UI ---
@APP.route('/')
def index():
    return send_from_directory(UI_DIR, 'index.html')

@APP.route('/<path:filename>')
def send_static(filename):
    return send_from_directory(UI_DIR, filename)

# --- ROUTES API ---
@APP.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "toune-o-matic"})

@APP.route("/api/status")
@require_key
def get_status():
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        status = c.status()
        current = c.currentsong()
        c.disconnect()
        return jsonify({"ok": True, "status": status, "current": current})
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/player/<action>", methods=["POST"])
@require_key
def player_action(action):
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        if action == "toggle":
            s = c.status()
            if s.get('state') == 'play':
                c.pause(1)
            else:
                c.play()
        elif action == "play":
            c.play()
        elif action == "pause":
            c.pause(1)
        elif action == "next":
            c.next()
        elif action == "previous":
            c.previous()
        elif action == "stop":
            c.stop()
        else:
            c.disconnect()
            return jsonify({"ok": False, "error": f"Action inconnue: {action}"}), 400
        
        c.disconnect()
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Player error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/volume/<int:vol>", methods=["POST"])
@require_key
def set_volume(vol):
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        vol = max(0, min(100, vol))
        c.setvol(vol)
        c.disconnect()
        return jsonify({"ok": True, "volume": vol})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/browse")
@require_key
def browse():
    path = request.args.get("path", "")
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        files = c.lsinfo(path) if path else c.lsinfo()
        c.disconnect()
        return jsonify({"ok": True, "files": files})
    except Exception as e:
        logger.error(f"Browse error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/queue")
@require_key
def get_queue():
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        queue = c.playlist()
        c.disconnect()
        return jsonify({"ok": True, "queue": queue})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/queue/clear", methods=["POST"])
@require_key
def clear_queue():
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        c.clear()
        c.disconnect()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/queue/add", methods=["POST"])
@require_key
def add_to_queue():
    data = request.get_json() or {}
    path = data.get("path", "")
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        c.add(path)
        c.disconnect()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/playlist/list")
@require_key
def list_playlists():
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        pls = [p.get('playlist', p) for p in c.listplaylists()]
        c.disconnect()
        return jsonify({"ok": True, "playlists": pls})
    except Exception as e:
        logger.error(f"List playlists error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/playlist/load/<name>", methods=["POST"])
@require_key
def load_pl(name):
    c = get_mpd()
    if not c:
        return jsonify({"ok": False, "error": "MPD Down"}), 503
    try:
        c.clear()
        c.load(name)
        c.play()
        c.disconnect()
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Load playlist error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.route("/api/logs")
@require_key
def get_logs():
    service = request.args.get("service", "toune-o-matic.service")
    lines = request.args.get("lines", "100")
    
    allowed = ["toune-o-matic.service", "mpd.service", "nginx.service"]
    if service not in allowed:
        return jsonify({"ok": False, "error": "Service non autorisé"}), 400
    
    try:
        result = subprocess.run(
            ["journalctl", "-u", service, "-n", str(lines), "-o", "short"],
            capture_output=True, text=True, timeout=10
        )
        return jsonify({"ok": True, "logs": result.stdout})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "Non trouvé"}), 404

if __name__ == "__main__":
    logger.info("Démarrage de Toune-o-Matic sur 0.0.0.0:11000")
    APP.run(host="0.0.0.0", port=11000, debug=False)
