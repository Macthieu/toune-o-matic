# Fichier: src/api/routes_audio.py
from flask import Blueprint, jsonify, request
from src.core.mpd_wrapper import mpd_wrapper
import re

bp = Blueprint("audio", __name__, url_prefix="/api/audio")

@bp.route("/status")
def status():
    """Liste toutes les sorties configurées dans MPD."""
    outputs = mpd_wrapper.exec(lambda c: c.outputs())
    if not outputs: outputs = []
    
    # Conversion propre pour le JSON
    clean_outs = []
    for o in outputs:
        clean_outs.append({
            "id": int(o.get("outputid", 0)),
            "name": o.get("outputname", "Unknown"),
            "enabled": (o.get("outputenabled", "0") == "1")
        })
        
    return jsonify({"ok": True, "outputs": clean_outs})

@bp.route("/outputs/toggle", methods=["POST"])
def toggle_output():
    """Active ou désactive une sortie audio."""
    data = request.json or {}
    oid = data.get("id")
    enabled = data.get("enabled")
    
    if oid is None: return jsonify({"ok": False}), 400
    
    def _act(c):
        if enabled: c.enableoutput(oid)
        else: c.disableoutput(oid)
        
    mpd_wrapper.exec(_act)
    return jsonify({"ok": True})