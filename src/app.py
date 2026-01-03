import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Imports des Blueprints (nos modules)
# Assure-toi que ces fichiers existent bien dans src/api/
from src.api.routes_audio import audio_bp
from src.api.routes_player import player_bp
from src.api.routes_content import content_bp
from src.api.routes_queue import queue_bp
from src.api.routes_system import system_bp   # <--- C'est lui qui posait problème (system_bp)
from src.api.routes_metadata import metadata_bp
from src.api.routes_bluetooth import bluetooth_bp

def create_app():
    # Création de l'application Flask
    app = Flask(__name__, 
                static_folder='../ui',    # Dossier pour les fichiers JS/CSS
                static_url_path='')       # URL racine pour les statiques

    # Activation de CORS (pour autoriser les requêtes du navigateur)
    CORS(app)

    # Configuration des Logs
    logging.basicConfig(level=logging.DEBUG)
    
    # Configuration par défaut
    app.config['SECRET_KEY'] = 'dev_secret_key_toune_o_matic'

    # --- Enregistrement des Routes (Blueprints) ---
    app.register_blueprint(audio_bp, url_prefix='/api/audio')
    app.register_blueprint(player_bp, url_prefix='/api/player')
    app.register_blueprint(content_bp, url_prefix='/api/content')
    app.register_blueprint(queue_bp, url_prefix='/api/queue')
    app.register_blueprint(system_bp, url_prefix='/api/system') # <--- Correction ici
    app.register_blueprint(metadata_bp, url_prefix='/api/metadata')
    app.register_blueprint(bluetooth_bp, url_prefix='/api/bluetooth')

    # --- Route pour l'interface utilisateur (UI) ---
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    @app.route('/<path:path>')
    def static_proxy(path):
        # Permet de servir les fichiers CSS/JS/IMG s'ils existent
        if os.path.exists(os.path.join(app.static_folder, path)):
            return app.send_static_file(path)
        # Sinon on renvoie l'index (pour les applis Single Page)
        return app.send_static_file('index.html')

    # --- Route de santé (Health Check) ---
    @app.route('/api/status')
    def status():
        # Simulation d'un statut simple pour le Mac
        return jsonify({
            "status": {"state": "stop", "random": False, "repeat": False},
            "current": {"title": "Prêt", "artist": "Toune-o-matic", "album": "Mac Dev Mode"}
        })

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)