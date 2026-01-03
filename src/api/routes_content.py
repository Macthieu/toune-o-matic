from flask import Blueprint, jsonify, request

content_bp = Blueprint('content', __name__)

@content_bp.route('/browse/artists', methods=['GET'])
def browse_artists():
    # Fausses données pour tester l'affichage
    return jsonify({
        "ok": True,
        "items": [
            {"artist": "Pink Floyd"},
            {"artist": "Jean Leloup"},
            {"artist": "Daft Punk"},
            {"artist": "Nirvana"}
        ]
    })

@content_bp.route('/browse/albums', methods=['GET'])
def browse_albums():
    return jsonify({
        "ok": True,
        "items": [
            {"album": "The Dark Side of the Moon", "artist": "Pink Floyd", "path": "mock/path"},
            {"album": "Le Dôme", "artist": "Jean Leloup", "path": "mock/path"}
        ]
    })

@content_bp.route('/browse/tracks', methods=['GET'])
def browse_tracks():
    return jsonify({
        "ok": True,
        "items": [
            {"title": "Money", "artist": "Pink Floyd", "path": "file1.mp3"},
            {"title": "Time", "artist": "Pink Floyd", "path": "file2.mp3"}
        ]
    })

@content_bp.route('/browse/genres', methods=['GET'])
def browse_genres():
    return jsonify({"ok": True, "items": [{"genre": "Rock", "count": 42}, {"genre": "Jazz", "count": 12}]})

@content_bp.route('/playlists', methods=['GET'])
def playlists():
    return jsonify({"ok": True, "playlists": [{"playlist": "Favoris"}, {"playlist": "Soirée"}]})
    
# Route pour éviter les erreurs 404 sur les tâches
@content_bp.route('/tasks/<action>', methods=['POST'])
def tasks(action):
    return jsonify({"ok": True, "message": f"Tâche {action} simulée"})
    
# Route simulée pour les images (évite les erreurs 404)
@content_bp.route('/cover', methods=['GET'])
def get_cover():
    return jsonify({"error": "No cover in mock mode"}), 404
    
@content_bp.route('/artist_image', methods=['GET'])
def get_artist_image():
    return jsonify({"error": "No image in mock mode"}), 404
