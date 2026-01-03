from flask import Blueprint, jsonify

queue_bp = Blueprint('queue', __name__)

@queue_bp.route('/', methods=['GET'])
def get_queue():
    return jsonify({
        "ok": True,
        "queue": [
            {"title": "Money", "artist": "Pink Floyd"},
            {"title": "Time", "artist": "Pink Floyd"}
        ]
    })

@queue_bp.route('/add', methods=['POST'])
def add_queue():
    return jsonify({"ok": True})

@queue_bp.route('/clear', methods=['POST'])
def clear_queue():
    return jsonify({"ok": True})
