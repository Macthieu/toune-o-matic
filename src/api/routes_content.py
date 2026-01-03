from flask import Blueprint, jsonify, request

content_bp = Blueprint('content', __name__)

# --- DONNÉES DE TEST ---
ARTISTS = [
    {"artist": "Pink Floyd"}, {"artist": "Jean Leloup"}, {"artist": "Daft Punk"},
    {"artist": "Nirvana"}, {"artist": "The Beatles"}, {"artist": "Radiohead"},
    {"artist": "Led Zeppelin"}, {"artist": "Queen"}, {"artist": "Metallica"}
]

@content_bp.route('/browse/artists', methods=['GET'])
def browse_artists():
    query = request.args.get('q', '').lower()
    # Filtrage intelligent
    filtered = [a for a in ARTISTS if query in a['artist'].lower()] if query else ARTISTS
    return jsonify({"ok": True, "items": filtered})

@content_bp.route('/browse/albums', methods=['GET'])
def browse_albums():
    # On renvoie toujours des albums fictifs pour tester le design
    return jsonify({
        "ok": True,
        "items": [
            {"album": "The Dark Side of the Moon", "artist": "Pink Floyd", "path": "mock/path"},
            {"album": "Le Dôme", "artist": "Jean Leloup", "path": "mock/path"},
            {"album": "Random Access Memories", "artist": "Daft Punk", "path": "mock/path"},
            {"album": "Nevermind", "artist": "Nirvana", "path": "mock/path"}
        ]
    })

@content_bp.route('/browse/tracks', methods=['GET'])
def browse_tracks():
    return jsonify({
        "ok": True,
        "items": [
            {"title": "Money", "artist": "Pink Floyd", "path": "file1.mp3"},
            {"title": "Time", "artist": "Pink Floyd", "path": "file2.mp3"},
            {"title": "Us and Them", "artist": "Pink Floyd", "path": "file3.mp3"}
        ]
    })

@content_bp.route('/browse/genres', methods=['GET'])
def browse_genres():
    return jsonify({"ok": True, "items": [{"genre": "Rock", "count": 42}, {"genre": "Jazz", "count": 12}]})

@content_bp.route('/playlists', methods=['GET'])
def playlists():
    return jsonify({"ok": True, "playlists": [{"playlist": "Favoris"}, {"playlist": "Soirée"}]})

@content_bp.route('/tasks/<action>', methods=['POST'])
def tasks(action):
    return jsonify({"ok": True, "message": f"Tâche {action} simulée"})

@content_bp.route('/cover', methods=['GET'])
def get_cover():
    return jsonify({"error": "No cover"}), 404

@content_bp.route('/artist_image', methods=['GET'])
def get_artist_image():
    return jsonify({"error": "No image"}), 404
