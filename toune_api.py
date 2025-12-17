#!/usr/bin/env python3
from __future__ import annotations

import os
import yaml
from functools import wraps
from typing import Any, Dict, List, Callable, Optional, Tuple

from flask import Flask, request, jsonify
from mpd import MPDClient, CommandError, ConnectionError as MPDConnectionError

APP = Flask(__name__)

# ----------------------------
# Settings
# ----------------------------
def load_settings() -> Dict[str, Any]:
    path = os.environ.get("TOUNE_SETTINGS", "/home/pi/toune-o-matic/settings.yaml")
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
def _as_int(v: Optional[str], default: int) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except Exception:
        return default

def _as_bool(v: Optional[str]) -> bool:
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def paginate(items: List[Dict[str, Any]], limit: int, offset: int) -> Tuple[int, List[Dict[str, Any]]]:
    total = len(items)
    if limit <= 0:
        return total, []
    offset = max(0, offset)
    return total, items[offset: offset + limit]

def require_key(fn: Callable[..., Any]):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # header prioritaire; fallback possible en query ?key=...
        provided = request.headers.get("X-API-Key") or request.args.get("key")
        if not provided or provided != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

def mpd_call(work: Callable[[MPDClient], Any]) -> Any:
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

def mpd_safe(work: Callable[[MPDClient], Any]) -> Tuple[bool, Any, int]:
    try:
        data = mpd_call(work)
        return True, data, 200
    except MPDConnectionError as e:
        return False, {"ok": False, "error": f"mpd connection error: {e}"}, 503
    except CommandError as e:
        return False, {"ok": False, "error": f"mpd command error: {e}"}, 400
    except Exception as e:
        return False, {"ok": False, "error": str(e)}, 500

def mpd_outputs(c: MPDClient) -> Dict[str, Dict[str, Any]]:
    outs = {}
    for o in c.outputs():
        name = o.get("outputname", "")
        outs[name] = o
    return outs

# ----------------------------
# Routes
# ----------------------------
@APP.get("/api/health")
def health():
    return jsonify({"ok": True})

@APP.get("/api/status")
@require_key
def status():
    ok, payload, code = mpd_safe(lambda c: {
        "status": c.status() or {},
        "song": c.currentsong() or {},
        "outputs": mpd_outputs(c),
    })
    if ok:
        return jsonify({"ok": True, **payload})
    return jsonify(payload), code

@APP.post("/api/mode")
@require_key
def mode():
    body = request.get_json(silent=True) or {}
    m = str(body.get("mode", "")).strip().lower()
    if m not in ("dac", "snap", "both"):
        return jsonify({"ok": False, "error": "mode must be dac|snap|both"}), 400

    def _do(c: MPDClient):
        outs = mpd_outputs(c)
        if OUT_DAC_NAME not in outs:
            raise RuntimeError(f"Output not found: {OUT_DAC_NAME}")
        if OUT_SNAP_NAME not in outs:
            raise RuntimeError(f"Output not found: {OUT_SNAP_NAME}")

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

        return {"mode": m}

    ok, payload, code = mpd_safe(_do)
    if ok:
        return jsonify({"ok": True, **payload})
    return jsonify(payload), code

@APP.post("/api/cmd")
@require_key
def cmd():
    body = request.get_json(silent=True) or {}
    action = str(body.get("action", "")).strip().lower()

    def _do(c: MPDClient):
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
        elif action == "next":
            c.next()
        elif action == "prev":
            c.previous()
        else:
            raise RuntimeError("action must be: play|pause|resume|stop|toggle|next|prev")
        return {"action": action}

    ok, payload, code = mpd_safe(_do)
    if ok:
        return jsonify({"ok": True, **payload})
    return jsonify(payload), code

@APP.get("/api/queue")
@require_key
def queue():
    limit = _clamp(_as_int(request.args.get("limit"), 200), 1, 1000)
    offset = max(0, _as_int(request.args.get("offset"), 0))

    def _do(c: MPDClient):
        items = c.playlistinfo() or []
        total, page = paginate(items, limit, offset)
        return {"total": total, "limit": limit, "offset": offset, "queue": page}

    ok, payload, code = mpd_safe(_do)
    if ok:
        return jsonify({"ok": True, **payload})
    return jsonify(payload), code

@APP.post("/api/queue/clear")
@require_key
def queue_clear():
    ok, payload, code = mpd_safe(lambda c: (c.clear() or True))
    if ok:
        return jsonify({"ok": True})
    return jsonify(payload), code

@APP.post("/api/queue/add")
@require_key
def queue_add():
    body = request.get_json(silent=True) or {}
    uri = body.get("uri")
    play = bool(body.get("play", False))
    if not uri or not isinstance(uri, str):
        return jsonify({"ok": False, "error": "missing uri"}), 400

    def _do(c: MPDClient):
        # addid retourne un id (string) si supporté; sinon fallback sur add + last id
        sid = None
        try:
            sid = c.addid(uri)
        except Exception:
            c.add(uri)
        # si play demandé
        if play:
            if sid:
                c.playid(sid)
            else:
                # fallback: joue la dernière position
                st = c.status() or {}
                plen = int(st.get("playlistlength", "0") or 0)
                if plen > 0:
                    c.play(plen - 1)
        return {"uri": uri, "play": play, "id": sid}

    ok, payload, code = mpd_safe(_do)
    if ok:
        return jsonify({"ok": True, **payload})
    return jsonify(payload), code

@APP.get("/api/browse")
@require_key
def browse():
    path = request.args.get("path") or ""
    dirs_only = _as_bool(request.args.get("dirs_only"))
    files_only = _as_bool(request.args.get("files_only"))

    limit = _clamp(_as_int(request.args.get("limit"), 200), 1, 1000)
    offset = max(0, _as_int(request.args.get("offset"), 0))

    if dirs_only and files_only:
        return jsonify({"ok": False, "error": "dirs_only and files_only cannot both be true"}), 400

    def _do(c: MPDClient):
        raw = c.lsinfo(path) or []

        items: List[Dict[str, Any]] = []
        for it in raw:
            if "directory" in it:
                if files_only:
                    continue
                items.append({"type": "dir", "path": it["directory"]})
            elif "file" in it:
                if dirs_only:
                    continue
                items.append({
                    "type": "file",
                    "path": it["file"],
                    "title": it.get("title"),
                    "artist": it.get("artist"),
                    "album": it.get("album"),
                    "duration": it.get("duration"),
                })

        # tri : dirs d'abord puis files, alpha par path
        items.sort(key=lambda x: (0 if x["type"] == "dir" else 1, str(x.get("path", "")).lower()))

        total, page = paginate(items, limit, offset)
        return {"path": path, "total": total, "limit": limit, "offset": offset, "items": page}

    ok, payload, code = mpd_safe(_do)
    if ok:
        return jsonify({"ok": True, **payload})
    return jsonify(payload), code

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    # Flask dev server (OK pour ton Pi en LAN; plus tard on passera à gunicorn)
    APP.run(host=LISTEN_HOST, port=LISTEN_PORT)