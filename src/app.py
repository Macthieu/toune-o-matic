import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Imports des Blueprints
from src.api.routes_audio import audio_bp
from src.api.routes_player import player_bp
from src.api.routes_content import content_bp
from src.api.routes_queue import queue_bp
from src.api.routes_system import system_bp
from src.api.routes_metadata import metadata_bp
from src.api.routes_bluetooth import bluetooth_bp
from src.api.routes_settings import settings_bp  # <--- NOUVEAU

def create_app():
    app = Flask(__name__, static_folder='../ui', static_url_path='')
    CORS(app)
    logging.basicConfig(level=logging.DEBUG)
    app.config['SECRET_KEY'] = 'dev_secret_key_toune_o_matic'

    # Enregistrement des Routes
    app.register_blueprint(audio_bp, url_prefix='/api/audio')
    app.register_blueprint(player_bp, url_prefix='/api/player')
    app.register_blueprint(content_bp, url_prefix='/api/content')
    app.register_blueprint(queue_bp, url_prefix='/api/queue')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    app.register_blueprint(metadata_bp, url_prefix='/api/metadata')
    app.register_blueprint(bluetooth_bp, url_prefix='/api/bluetooth')
    app.register_blueprint(settings_bp, url_prefix='/api/settings') # <--- NOUVEAU

    @app.route('/')
    def index(): return app.send_static_file('index.html')

    @app.route('/<path:path>')
    def static_proxy(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return app.send_static_file(path)
        return app.send_static_file('index.html')

    @app.route('/api/status')
    def status():
        return jsonify({
            "status": {"state": "stop", "random": False, "repeat": False},
            "current": {"title": "Prêt", "artist": "Toune-o-matic", "album": "Mac Dev Mode"}
        })

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
