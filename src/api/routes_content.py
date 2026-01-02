import os
import logging
import requests
import threading
import time
from flask import Blueprint, jsonify, request, send_file, abort
from src.core.mpd_wrapper import mpd_wrapper
from src.core.db import get_db

logger = logging.getLogger("ContentAPI")
bp = Blueprint("content", __name__, url_prefix="/api/content")

MUSIC_ROOT = "/mnt/music"
COVERS_ROOT = "/mnt/music/Pochettes"
ARTIST_IMG_ROOT = "/mnt/music/Photos d'artistes"

# --- SYSTEME DE QUEUE ---
task_queue = []
scan_state = { "active": False, "type": None, "message": "Prêt", "current": 0, "total": 0, "queue": [] }
queue_lock = threading.Lock()

def worker_loop():
    while True:
        task = None
        with queue_lock:
            if task_queue:
                task = task_queue.pop(0)
                # Mise à jour de la liste visible
                scan_state["queue"] = [t['desc'] for t in task_queue]
        
        if task:
            scan_state.update({"active": True, "type": task['type'], "message": f"Démarrage {task['desc']}...", "current": 0, "total": 0})
            try: task['func']()
            except Exception as e: 
                logger.error(e)
                scan_state["message"] = f"Erreur: {str(e)}"
                time.sleep(2)
            scan_state.update({"active": False, "message": "Terminé", "type": None})
        else: time.sleep(1)

threading.Thread(target=worker_loop, daemon=True).start()

def queue_task(type_id, desc, func):
    with queue_lock:
        task_queue.append({"type": type_id, "desc": desc, "func": func})
        scan_state["queue"] = [t['desc'] for t in task_queue]

# --- JOBS ---
def job_scan_mpd():
    scan_state.update({"message": "Mise à jour MPD...", "total": 1, "current": 1})
    mpd_wrapper.exec(lambda c: c.update())
    time.sleep(2) # Fake wait pour UX

def job_dl_albums():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT album, artist FROM tracks WHERE album != 'Unknown'").fetchall()
    conn.close()
    scan_state["total"] = len(rows)
    for i, r in enumerate(rows):
        scan_state.update({"current": i+1, "message": f"Album: {r['album']}"})
        safe = r['album'].replace("/", "-").strip()
        path = os.path.join(COVERS_ROOT, f"{safe}.jpg")
        if not os.path.exists(path):
            try:
                # Code simplifié téléchargement
                url = "https://musicbrainz.org/ws/2/release"
                p = {'query': f'release:{r["album"]} AND artist:{r["artist"]}', 'fmt': 'json'}
                req = requests.get(url, params=p, headers={'User-Agent': 'Toune/1.0'}, timeout=5)
                d = req.json()
                if 'releases' in d and d['releases']:
                    img = f"https://coverartarchive.org/release/{d['releases'][0]['id']}/front"
                    r2 = requests.get(img, timeout=10)
                    if r2.status_code==200: 
                        os.makedirs(COVERS_ROOT, exist_ok=True)
                        with open(path,'wb') as f: f.write(r2.content)
            except: pass
            time.sleep(1.0)

def job_dl_artists():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT artist FROM tracks").fetchall()
    conn.close()
    scan_state["total"] = len(rows)
    for i, r in enumerate(rows):
        scan_state.update({"current": i+1, "message": f"Artiste: {r['artist']}"})
        safe = r['artist'].replace("/", "-").strip()
        path = os.path.join(ARTIST_IMG_ROOT, f"{safe}.jpg")
        if not os.path.exists(path):
            try:
                url = f"https://www.theaudiodb.com/api/v1/json/2/search.php?s={r['artist']}"
                d = requests.get(url, timeout=5).json()
                if d and d.get('artists') and d['artists'][0].get('strArtistThumb'):
                    r2 = requests.get(d['artists'][0]['strArtistThumb'], timeout=10)
                    if r2.status_code==200:
                        os.makedirs(ARTIST_IMG_ROOT, exist_ok=True)
                        with open(path,'wb') as f: f.write(r2.content)
            except: pass
            time.sleep(0.5)

# --- ROUTES ---
@bp.route("/scan_status")
def get_status(): return jsonify(scan_state)

@bp.route("/tasks/mpd_update", methods=["POST"])
def t_mpd(): queue_task("mpd", "Scan Fichiers MPD", job_scan_mpd); return jsonify({"ok":True})

@bp.route("/tasks/albums", methods=["POST"])
def t_alb(): queue_task("albums", "Pochettes Albums", job_dl_albums); return jsonify({"ok":True})

@bp.route("/tasks/artists", methods=["POST"])
def t_art(): queue_task("artists", "Photos Artistes", job_dl_artists); return jsonify({"ok":True})

# --- IMAGES & NAV ---
def fuzzy_file(root, name):
    if not os.path.exists(root): return None
    t = name.lower().replace("/", "").strip()
    try:
        for f in os.listdir(root):
            if f.lower().startswith(t) and f.lower().endswith(('.jpg','.png')): return os.path.join(root, f)
    except: pass
    return None

@bp.route("/cover")
def gc():
    p, a = request.args.get("path",""), request.args.get("album","")
    if p:
        d = os.path.dirname(os.path.join(MUSIC_ROOT, p))
        if os.path.exists(d):
            for n in ["folder.jpg","cover.jpg","art.png"]:
                if os.path.exists(os.path.join(d,n)): return send_file(os.path.join(d,n))
    if a:
        f = fuzzy_file(COVERS_ROOT, a)
        if f: return send_file(f)
    return abort(404)

@bp.route("/artist_image")
def gai():
    f = fuzzy_file(ARTIST_IMG_ROOT, request.args.get("name",""))
    if f: return send_file(f)
    return abort(404)

def get_pg(): return int(request.args.get("limit",50)), (int(request.args.get("page",1))-1)*int(request.args.get("limit",50))

@bp.route("/browse/artists")
def ba(): l,o=get_pg(); c=get_db(); r=c.execute("SELECT artist, COUNT(*) as count FROM tracks GROUP BY artist ORDER BY artist LIMIT ? OFFSET ?", (l,o)).fetchall(); c.close(); return jsonify({"ok":True, "items":[dict(x) for x in r]})

@bp.route("/browse/genres")
def bg(): 
    # Nouvelle route GENRES
    c=get_db(); 
    r=c.execute("SELECT genre, COUNT(*) as count FROM tracks WHERE genre != '' GROUP BY genre ORDER BY genre").fetchall(); 
    c.close(); 
    return jsonify({"ok":True, "items":[dict(x) for x in r]})

@bp.route("/browse/albums_global")
def bag(): l,o=get_pg(); c=get_db(); r=c.execute("SELECT album,artist,path FROM tracks GROUP BY album ORDER BY album LIMIT ? OFFSET ?", (l,o)).fetchall(); c.close(); return jsonify({"ok":True, "items":[dict(x) for x in r]})

@bp.route("/browse/tracks_global")
def btg(): l,o=get_pg(); c=get_db(); r=c.execute("SELECT title,artist,album,path FROM tracks ORDER BY title LIMIT ? OFFSET ?", (l,o)).fetchall(); c.close(); return jsonify({"ok":True, "items":[dict(x) for x in r]})

@bp.route("/browse/albums")
def bal(): 
    c=get_db()
    # Support filtre par artiste ou genre
    a, g = request.args.get("artist"), request.args.get("genre")
    if a: r=c.execute("SELECT album,artist,path FROM tracks WHERE artist=? GROUP BY album ORDER BY year DESC", (a,)).fetchall()
    elif g: r=c.execute("SELECT album,artist,path FROM tracks WHERE genre=? GROUP BY album ORDER BY album", (g,)).fetchall()
    else: r=[]
    c.close(); return jsonify({"ok":True, "items":[dict(x) for x in r]})

@bp.route("/browse/tracks")
def btr(): c=get_db(); r=c.execute("SELECT * FROM tracks WHERE album=? ORDER BY path", (request.args.get("album"),)).fetchall(); c.close(); return jsonify({"ok":True, "items":[dict(x) for x in r]})

@bp.route("/browse/folders")
def bfo():
    try:
        i=mpd_wrapper.exec(lambda c: c.lsinfo(request.args.get("path","")))
        res=[]
        for x in i:
            if 'directory' in x: res.append({"type":"folder", "name":os.path.basename(x['directory']), "path":x['directory']})
            elif 'file' in x: res.append({"type":"file", "name":os.path.basename(x['file']), "path":x['file']})
        return jsonify({"ok":True, "items":res, "parent":os.path.dirname(request.args.get("path",""))})
    except: return jsonify({"ok":False, "items":[]})

@bp.route("/playlists")
def lpl(): return jsonify({"ok":True, "playlists":mpd_wrapper.exec(lambda c:c.listplaylists()) or []})
@bp.route("/playlist/load", methods=["POST"])
def lop(): n,c=request.json.get("name"),request.json.get("clear"); mpd_wrapper.exec(lambda x: (x.clear() if c else None, x.load(n), x.play() if c else None)); return jsonify({"ok":True})
@bp.route("/playlist/save", methods=["POST"])
def sap(): mpd_wrapper.exec(lambda c: c.save(request.json.get("name"))); return jsonify({"ok":True})
@bp.route("/playlist/delete", methods=["POST"])
def dep(): mpd_wrapper.exec(lambda c: c.rm(request.json.get("name"))); return jsonify({"ok":True})
@bp.route("/playlist/add_items", methods=["POST"])
def adi(): mpd_wrapper.exec(lambda c: [c.playlistadd(request.json.get("playlist"), x) for x in request.json.get("paths")]); return jsonify({"ok":True})