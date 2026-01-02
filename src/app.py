# Fichier: src/app.py (Version Jalon 2)
import os
import yaml
import logging
from flask import Flask, send_from_directory, request, jsonify
from functools import wraps

# Imports API
from src.api import routes_player
from src.api import routes_library
from src.api import routes_system
from src.api import routes_content
from src.api import routes_bluetooth
from src.api import routes_audio

# Config Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TouneServer")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(BASE_DIR, "ui")
SETTINGS_PATH = os.path.join(BASE_DIR, "config/settings.yaml")

app = Flask(__name__, static_folder=UI_DIR, static_url_path="")

@app.before_request
def _auth_all_api():
    # UI publique, API protégée
    # Autorise les images sans clé (les <img src> n'envoient pas X-API-Key)
    PUBLIC_API_PREFIXES = (
        '/api/content/cover',
        '/api/content/artist',
        '/api/content/album',
        '/api/content/art',
        '/api/content/image',
        '/api/content/thumb',
    )
    if request.path.startswith(PUBLIC_API_PREFIXES):
        return None

    if request.path.startswith('/api/'):
        key = request.headers.get('X-API-Key') or request.args.get('key')
        if key != API_KEY:
            return jsonify({'ok': False, 'error': 'Unauthorized'}), 401

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

SETTINGS = load_settings()
API_KEY = SETTINGS.get("api", {}).get("key", "secret")

def require_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("key")
        if key != API_KEY:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# Enregistrement des Blueprints
@routes_player.bp.before_request
@require_key
def before_player_request(): pass

@routes_library.bp.before_request
@require_key
def before_lib_request(): pass
app.register_blueprint(routes_player.bp)
app.register_blueprint(routes_audio.bp)
app.register_blueprint(routes_library.bp)
app.register_blueprint(routes_system.bp)
app.register_blueprint(routes_content.bp)
app.register_blueprint(routes_bluetooth.bp)

@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(UI_DIR, path)

if __name__ == "__main__":
    port = int(SETTINGS.get("api", {}).get("port", 11000))
    logger.info(f"🚀 Toune-o-matic démarré sur le port {port}")
    # IMPORTANT: en service systemd, PAS de reloader/debug
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
