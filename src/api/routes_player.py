from flask import Blueprint, jsonify

player_bp = Blueprint('player', __name__)

@player_bp.route('/toggle', methods=['POST'])
def toggle():
    return jsonify({"status": "ok", "state": "play"})

@player_bp.route('/next', methods=['POST'])
def next_track():
    return jsonify({"status": "ok"})

@player_bp.route('/previous', methods=['POST'])
def prev_track():
    return jsonify({"status": "ok"})

@player_bp.route('/seek', methods=['POST'])
def seek():
    return jsonify({"status": "ok"})
    
@player_bp.route('/shuffle', methods=['POST'])
def shuffle():
    return jsonify({"status": "ok", "random": True})

@player_bp.route('/repeat', methods=['POST'])
def repeat():
    return jsonify({"status": "ok", "repeat": True})
