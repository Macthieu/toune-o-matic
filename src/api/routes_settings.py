from flask import Blueprint, jsonify, request
from src.core.config_manager import config_manager

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/', methods=['GET'])
def get_all_settings():
    """Renvoie toute la configuration actuelle"""
    return jsonify({"ok": True, "config": config_manager.config})

@settings_bp.route('/update', methods=['POST'])
def update_setting():
    """Met à jour un réglage spécifique"""
    data = request.json
    section = data.get('section')
    key = data.get('key')
    value = data.get('value')
    
    if section and key:
        config_manager.set(section, key, value)
        
        # --- ICI : LOGIQUE D'APPLICATION ---
        # C'est ici qu'on appliquera les changements réels sur le Pi plus tard.
        # Exemple: Si on change le DAC, on réécrit /etc/mpd.conf
        print(f"🔧 Réglage changé : [{section}] {key} = {value}")
        
        return jsonify({"ok": True, "message": "Sauvegardé"})
    return jsonify({"ok": False, "error": "Données invalides"}), 400