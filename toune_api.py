#!/usr/bin/env python3
from __future__ import annotations

import os
from functools import wraps
from typing import Any, Dict, List, Optional, Callable, Tuple

import yaml
from flask import Flask, request, jsonify
from mpd import MPDClient, CommandError, ConnectionError as MPDConnectionError

APP = Flask(__name__)

# ----------------------------
# Settings (robuste: env + chemins possibles)
# ----------------------------
DEFAULT_SETTINGS_CANDIDATES = [
    "/home/pi/toune-o-matic/settings.yaml",
    "/home/pi/toune-o-matic/config/settings.yaml",
    "/home/pi/toune-o-matic/config/settings.local.yaml",
]

def _first_existing_path(paths: List[str]) -> Optional[str]:
    for p in paths:
        try:
            if p and os.path.isfile(p):
                return p
        except Exception:
            pass
    return None

def load_settings() -> Dict[str, Any]:
    env_path = os.environ.get("TOUNE_SETTINGS")
    candidates = [env_path] if env_path else []
    candidates += DEFAULT_SETTINGS_CANDIDATES

    path = _first_existing_path([p for p in candidates if p])
    if not path:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

SETTINGS = load_settings()

def get_setting(*keys: str, default=None):
    cur: Any = SETTINGS
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

API_KEY = (
    get_setting("api", "key")
    or get_setting("api_key")
    or "change-moi-une-cle-secrete"
)

LISTEN_HOST = str(get_setting("api", "host", default="0.0.0.0"))
LISTEN_PORT = int(get_setting("api", "port", default=8787))

MPD_HOST = str(get_setting("mpd", "host", default="127.0.0.1"))
MPD_PORT = int(get_setting("mpd", "port", default=6600))
MPD_TIMEOUT = float(get_setting("mpd", "timeout", default=3.0))

OUT_DAC_NAME = str(get_setting("outputs", "dac_name", default="DAC strict"))
OUT_SNAP_NAME = str(get_setting("outputs", "snapcast_name", default="snapcast"))

# ----------------------------
# Helpers
# ----------------------------
def parse_int(v: Optional[str], default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except Exception:
        return default

def parse_bool(v: Optional[str]) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def require_key(fn: Callable[..., Any]):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        provided = request.headers.get("X-API-Key") or request.args.get("key")
        if not provided or provided != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

def with_mpd(work: Callable[[MPDClient], Any]):
    c = MPDClient()
    c.timeout = MPD_TIMEOUT
    c.idletimeout = MPD_TIMEOUT
    try:
        c.connect(MPD_HOST, MPD_PORT)
        return work(c)
    finally:
        try:
            c.close()
        except Exception:
            pass
        try:
            c.disconnect()
        except Exception:
            pass

def mpd_outputs(c: MPDClient) -> Dict[str, Dict[str, Any]]:
    outs: Dict[str, Dict[str, Any]] = {}
    for o in c.outputs():
        name = o.get("outputname", "")
        outs[name] = o
    return outs

def normalize_lsinfo(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MPD lsinfo retourne une liste d'objets hétérogènes:
      - {"directory": "..."}
      - {"file": "...", "Title": "...", "Artist": "...", "Album": "...", "Time": "..."}
    On normalise en:
      - {"type":"dir","path":"..."}
      - {"type":"file","path":"...","title":...,"artist":...,"album":...,"duration":...}
    """
    items: List[Dict[str, Any]] = []

    for it in raw or []:
        if "directory" in it:
            items.append({"type": "dir", "path": it.get("directory", "")})
            continue

        if "file" in it:
            duration = it.get("Time") or it.get("time") or ""
            items.append({
                "type": "file",
                "path": it.get("file", ""),
                "title": it.get("Title") or it.get("title") or "",
                "artist": it.get("Artist") or it.get("artist") or "",
                "album": it.get("Album") or it.get("album") or "",
                "duration": str(duration),
            })
            continue

    # tri: dossiers d'abord, puis fichiers; tri alpha sur path
    items.sort(key=lambda x: (0 if x.get("type") == "dir" else 1, x.get("path", "")))
    return items

# ----------------------------
# Routes
# ----------------------------
@APP.get("/api/health")
def health():
    return jsonify({"ok": True})

@APP.get("/api/status")
@require_key
def status():
    def work(c: MPDClient):
        return jsonify({
            "ok": True,
            "status": c.status() or {},
            "song": c.currentsong() or {},
            "outputs": mpd_outputs(c),
        })

    try:
        return with_mpd(work)
    except MPDConnectionError as e:
        return jsonify({"ok": False, "error": f"mpd connection error: {e}"}), 503
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.post("/api/mode")
@require_key
def mode():
    body = request.get_json(silent=True) or {}
    m = str(body.get("mode", "")).strip().lower()
    if m not in ("dac", "snap", "both"):
        return jsonify({"ok": False, "error": "mode must be dac|snap|both"}), 400

    def work(c: MPDClient):
        outs = mpd_outputs(c)

        if OUT_DAC_NAME not in outs:
            return jsonify({"ok": False, "error": f"Output not found: {OUT_DAC_NAME}"}), 400
        if OUT_SNAP_NAME not in outs:
            return jsonify({"ok": False, "error": f"Output not found: {OUT_SNAP_NAME}"}), 400

        dac_id = int(outs[OUT_DAC_NAME]["outputid"])
        snap_id = int(outs[OUT_SNAP_NAME]["outputid"])

        if m == "both":
            c.enableoutput(dac_id)
            c.enableoutput(snap_id)
        elif m == "dac":
            c.enableoutput(dac_id)
            c.disableoutput(snap_id)
        else:  # snap
            c.disableoutput(dac_id)
            c.enableoutput(snap_id)

        return jsonify({"ok": True, "mode": m})

    try:
        return with_mpd(work)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.post("/api/cmd")
@require_key
def cmd():
    body = request.get_json(silent=True) or {}
    action = str(body.get("action", "")).strip().lower()

    def work(c: MPDClient):
        if action == "play":
            c.play()
        elif action == "pause":
            c.pause(1)
        elif action == "resume":
            c.pause(0)
        elif action == "stop":
            c.stop()
        elif action == "toggle":
            st = (c.status() or {}).get("state", "")
            if st == "play":
                c.pause(1)
            else:
                c.play()
        elif action in ("next", "n"):
            c.next()
        elif action in ("prev", "previous", "p"):
            c.previous()
        else:
            return jsonify({"ok": False, "error": "unknown action"}), 400

        return jsonify({"ok": True, "action": action})

    try:
        return with_mpd(work)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.get("/api/browse")
@require_key
def browse():
    path = request.args.get("path", "") or ""
    limit = clamp(parse_int(request.args.get("limit"), 200), 1, 500)
    offset = max(0, parse_int(request.args.get("offset"), 0))
    dirs_only = parse_bool(request.args.get("dirs_only"))
    files_only = parse_bool(request.args.get("files_only"))

    def work(c: MPDClient):
        raw = c.lsinfo(path)
        items = normalize_lsinfo(raw)

        if dirs_only:
            items = [x for x in items if x.get("type") == "dir"]
        if files_only:
            items = [x for x in items if x.get("type") == "file"]

        total = len(items)
        page = items[offset:offset + limit]

        return jsonify({
            "ok": True,
            "path": path,
            "limit": limit,
            "offset": offset,
            "total": total,
            "items": page,
        })

    try:
        return with_mpd(work)
    except CommandError as e:
        return jsonify({"ok": False, "error": f"MPD CommandError: {e}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.get("/api/queue")
@require_key
def queue():
    limit = clamp(parse_int(request.args.get("limit"), 200), 1, 500)
    offset = max(0, parse_int(request.args.get("offset"), 0))

    def work(c: MPDClient):
        # MPD moderne supporte playlistinfo("start:end") => très efficace
        try:
            page = c.playlistinfo(f"{offset}:{offset + limit}")
            st = c.status() or {}
            total = int(st.get("playlistlength", "0"))
            return jsonify({"ok": True, "limit": limit, "offset": offset, "total": total, "queue": page})
        except Exception:
            allq = c.playlistinfo()
            total = len(allq)
            page = allq[offset:offset + limit]
            return jsonify({"ok": True, "limit": limit, "offset": offset, "total": total, "queue": page})

    try:
        return with_mpd(work)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.post("/api/queue/clear")
@require_key
def queue_clear():
    def work(c: MPDClient):
        c.clear()
        return jsonify({"ok": True})
    try:
        return with_mpd(work)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@APP.post("/api/queue/add")
@require_key
def queue_add():
    data = request.get_json(silent=True) or {}
    uri = data.get("uri")
    play = bool(data.get("play", False))
    if not uri:
        return jsonify({"ok": False, "error": "missing uri"}), 400

    def work(c: MPDClient):
        sid = c.addid(uri)
        if play:
            c.playid(sid)
        return jsonify({"ok": True, "uri": uri, "play": play, "id": sid})

    try:
        return with_mpd(work)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Petit print utile (journalctl) pour diagnostiquer port/settings
    print(f"[toune-api] settings loaded keys={list(SETTINGS.keys())}", flush=True)
    print(f"[toune-api] listening on {LISTEN_HOST}:{LISTEN_PORT} (mpd {MPD_HOST}:{MPD_PORT})", flush=True)
    APP.run(host=LISTEN_HOST, port=LISTEN_PORT)