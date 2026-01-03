from flask import Blueprint, jsonify, request

audio_bp = Blueprint('audio', __name__)

@audio_bp.route('/status', methods=['GET'])
def audio_status():
    # Simulation d'une sortie audio pour le Mac
    return jsonify({
        "status": "ok",
        "outputs": [
            {"id": 1, "name": "Sortie Mac (Simulation)", "enabled": True},
            {"id": 2, "name": "HDMI (Simulation)", "enabled": False}
        ]
    })

@audio_bp.route('/outputs/toggle', methods=['POST'])
def toggle_output():
    return jsonify({"status": "ok", "message": "Simulation: Sortie basculée"})

@audio_bp.route('/configure', methods=['POST'])
def configure_output():
    return jsonify({"status": "ok", "message": "Simulation: Config sauvegardée"})
