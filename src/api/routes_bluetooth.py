from flask import Blueprint, jsonify

bluetooth_bp = Blueprint('bluetooth', __name__)

@bluetooth_bp.route('/scan', methods=['POST'])
def scan():
    return jsonify({
        "ok": True,
        "devices": [
            {"name": "JBL Flip 5", "mac": "00:11:22:33:44:55", "connected": False},
            {"name": "Sony WH-1000XM4", "mac": "AA:BB:CC:DD:EE:FF", "connected": False}
        ]
    })

@bluetooth_bp.route('/paired', methods=['GET'])
def paired():
    return jsonify({"ok": True, "devices": []})
