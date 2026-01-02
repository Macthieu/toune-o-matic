from flask import Blueprint, jsonify, request
from src.core.db import get_db
from src.core.scanner import scan_library
import threading

bp = Blueprint("library", __name__, url_prefix="/api/library")

@bp.route("/scan", methods=["POST"])
def trigger_scan():
    """Lance le scan en tâche de fond (thread) pour ne pas bloquer l'UI."""
    def run():
        scan_library()
        
    threading.Thread(target=run).start()
    return jsonify({"ok": True, "message": "Scan started in background"})

@bp.route("/search")
def search():
    """Recherche Full-Text (titre, artiste, album...)"""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"ok": True, "results": []})
    
    # Recherche FTS (rapide)
    # On ajoute * pour faire une recherche préfixe (ex: "pink fl" -> "pink floyd")
    query_str = f"{q}*"
    
    conn = get_db()
    # On limite à 100 résultats pour ne pas tuer le navigateur
    rows = conn.execute(
        "SELECT * FROM tracks_fts WHERE tracks_fts MATCH ? ORDER BY rank LIMIT 100", 
        (query_str,)
    ).fetchall()
    
    results = [dict(r) for r in rows]
    conn.close()
    
    return jsonify({"ok": True, "count": len(results), "results": results})

@bp.route("/stats")
def stats():
    conn = get_db()
    count = conn.execute("SELECT Count(*) FROM tracks").fetchone()[0]
    conn.close()
    return jsonify({"ok": True, "total_tracks": count})
