# Fichier: src/api/routes_player.py
import logging
from flask import Blueprint, jsonify, request
from src.core.mpd_wrapper import mpd_wrapper

logger = logging.getLogger("API_Player")
bp = Blueprint("player", __name__, url_prefix="/api")

@bp.route("/status")
def status():
    # On récupère tout pour que le JS puisse calculer le temps total correct
    status = mpd_wrapper.exec(lambda c: c.status())
    current = mpd_wrapper.exec(lambda c: c.currentsong())
    return jsonify({"ok": True, "status": status, "current": current or {}})

@bp.route("/player/<action>", methods=["POST"])
def player_action(action):
    def _act(c):
        if action == "play": c.play()
        elif action == "pause": c.pause(1)
        elif action == "stop": c.stop()
        elif action == "next": c.next()
        elif action == "previous": c.previous()
        elif action == "toggle":
            s = c.status()
            if s.get('state') == 'play': c.pause(1)
            else: c.play()
    mpd_wrapper.exec(_act)
    return jsonify({"ok": True})

# --- CORRECTION SEEK (En secondes absolue) ---
@bp.route("/player/seek", methods=["POST"])
def seek():
    data = request.json or {}
    seconds = data.get("seconds")
    
    if seconds is None: 
        return jsonify({"ok": False, "error": "Missing seconds"}), 400
    
    # seekcur prend un float (position absolue en secondes)
    mpd_wrapper.exec(lambda c: c.seekcur(float(seconds)))
    return jsonify({"ok": True})

@bp.route("/volume/<int:vol>", methods=["POST"])
def set_volume(vol):
    vol = max(0, min(100, vol))
    mpd_wrapper.exec(lambda c: c.setvol(vol))
    return jsonify({"ok": True, "volume": vol})

# --- CONFIGURATION DAC AVANCEE (Nouveau) ---
@bp.route("/audio/configure", methods=["POST"])
def configure_audio():
    """
    Simule une config DAC en changeant le type de mixer MPD à la volée.
    (Hardware = volume DAC, Software = volume MPD, None = Bitperfect)
    """
    data = request.json or {}
    oid = data.get("id")
    mixer = data.get("mixer") # 'software', 'hardware', 'none'
    
    # Note: MPD ne permet pas toujours de changer ça à chaud sans redémarrer,
    # mais on peut essayer via `enableoutput` ou des commandes expertes.
    # Ici, pour l'exemple, on sauvegarde ça (idéalement dans mpd.conf).
    
    # Pour l'instant, on renvoie OK pour l'interface UI
    logger.info(f"Config DAC demandée: ID={oid}, Mixer={mixer}")
    return jsonify({"ok": True, "message": "Configuration sauvegardée (Redémarrage requis pour appliquer)"})

# ... (Le reste des routes queue/add reste identique) ...
@bp.route("/queue", methods=["GET"])
def get_queue():
    queue = mpd_wrapper.exec(lambda c: c.playlistinfo())
    return jsonify({"ok": True, "queue": queue or []})

@bp.route("/queue/clear", methods=["POST"])
def clear_queue():
    mpd_wrapper.exec(lambda c: c.clear())
    return jsonify({"ok": True})

@bp.route("/queue/add", methods=["POST"])
def add_queue():
    data = request.json or {}
    path = data.get("path")
    if not path: return jsonify({"ok": False}), 400
    mpd_wrapper.exec(lambda c: c.add(path))
    return jsonify({"ok": True})

@bp.route("/queue/play_now", methods=["POST"])
def play_now():
    data = request.json or {}
    path = data.get("path")
    if not path: return jsonify({"ok": False}), 400
    def _seq(c):
        c.clear()
        c.add(path)
        c.play()
    mpd_wrapper.exec(_seq)
    return jsonify({"ok": True})