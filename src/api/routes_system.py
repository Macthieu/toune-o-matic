# src/api/routes_system.py
from flask import Blueprint, jsonify, request
from src.core.sys_monitor import get_system_stats
import os

system_bp = Blueprint('system', __name__)

@system_bp.route('/stats', methods=['GET'])
def stats():
    """Renvoie les métriques CPU/RAM/Disk/Temp"""
    data = get_system_stats()
    return jsonify(data)

@system_bp.route('/restart', methods=['POST'])
def restart_service():
    """Redémarre le service (Simulation sur Mac)"""
    # Sur le Pi, on ferait: os.system("sudo systemctl restart toune-o-matic")
    return jsonify({"status": "restarting", "message": "Redémarrage commandé..."})

@system_bp.route('/shutdown', methods=['POST'])
def shutdown_system():
    """Éteint le système"""
    # os.system("sudo shutdown now")
    return jsonify({"status": "shutdown", "message": "Arrêt en cours..."})