#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

# --- Paths
REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = REPO_ROOT / "config" / "settings.yaml"
STATE_DIR = REPO_ROOT / ".state"
PID_FILE = STATE_DIR / "player.pid"
META_FILE = STATE_DIR / "player.meta.yaml"
OUT_LOG = STATE_DIR / "player.out.log"
ERR_LOG = STATE_DIR / "player.err.log"


# --- Utils
def _p(path_like: Union[str, Path]) -> Path:
    """Normalize any path-like to an absolute Path."""
    if isinstance(path_like, Path):
        pth = path_like
    else:
        pth = Path(str(path_like))
    if not pth.is_absolute():
        pth = (REPO_ROOT / pth).resolve()
    return pth.expanduser().resolve()


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_yaml(path_like: Union[str, Path]) -> Dict[str, Any]:
    path = _p(path_like)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def save_yaml(path_like: Union[str, Path], data: Dict[str, Any]) -> None:
    path = _p(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def read_pid() -> Optional[int]:
    try:
        if not PID_FILE.exists():
            return None
        txt = PID_FILE.read_text(encoding="utf-8").strip()
        if not txt:
            return None
        return int(txt)
    except Exception:
        return None


def write_pid(pid: int) -> None:
    ensure_state_dir()
    PID_FILE.write_text(str(pid), encoding="utf-8")


def clear_state() -> None:
    for p in (PID_FILE, META_FILE):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


# --- Audio Engine import
def get_engine(device: str):
    # Import here to keep commands like "devices" usable even if deps missing
    from src.core.audio_engine import AudioEngine
    return AudioEngine(device=device)


# --- Commands
def cmd_devices(args: argparse.Namespace) -> None:
    print("=== PLAYBACK devices (aplay -l) ===")
    try:
        subprocess.run(["aplay", "-l"], check=False)
    except FileNotFoundError:
        print("❌ aplay introuvable")
    print("\n=== CAPTURE devices (arecord -l) ===")
    try:
        subprocess.run(["arecord", "-l"], check=False)
    except FileNotFoundError:
        print("❌ arecord introuvable")


def cmd_info(args: argparse.Namespace) -> None:
    cfg = _p(args.config)
    settings = load_yaml(cfg)
    dev = settings.get("audio_device", "default")
    ok = "OK" if cfg.exists() else "ABSENT"
    print(f"📄 Config: {cfg} ({ok})")
    print(f"🎧 Appareil audio actif : {dev}")


def cmd_set_device(args: argparse.Namespace) -> None:
    cfg = _p(args.config)
    settings = load_yaml(cfg)
    settings["audio_device"] = args.device
    save_yaml(cfg, settings)
    print(f"✅ audio_device mis à jour : {args.device}")
    print(f"📄 Config: {cfg}")


def spawn_background_play(args: argparse.Namespace, device: str, filename: str) -> None:
    ensure_state_dir()

    cfg = _p(args.config)
    file_abs = _p(filename)

    # Build command
    cmd = [
        sys.executable,
        str(REPO_ROOT / "run.py"),
        "--config",
        str(cfg),
        "play",
        "--device",
        device,
        "--no-bg",
    ]

    # loop / repeat
    if getattr(args, "loop", False):
        cmd.append("--loop")
    if getattr(args, "repeat", None) is not None and int(args.repeat) > 1:
        cmd += ["--repeat", str(int(args.repeat))]

    cmd.append(str(file_abs))

    # Open logs
    out_f = OUT_LOG.open("ab")
    err_f = ERR_LOG.open("ab")

    # Spawn
    p = subprocess.Popen(
        cmd,
        stdout=out_f,
        stderr=err_f,
        cwd=str(REPO_ROOT),
        start_new_session=True,  # detach from terminal
    )

    # Save state
    write_pid(p.pid)
    meta = {
        "pid": p.pid,
        "device": device,
        "file": str(file_abs),
        "started": now_str(),
        "cmd": cmd,
        "logs": {"out": str(OUT_LOG), "err": str(ERR_LOG)},
    }
    save_yaml(META_FILE, meta)

    print("✅ Lecture lancée en arrière-plan")
    print(f"   PID: {p.pid}")
    print(f"   Device: {device}")
    print(f"   Fichier: {file_abs}")
    print(f"   Logs: {OUT_LOG} / {ERR_LOG}")


def cmd_play(args: argparse.Namespace) -> None:
    cfg = _p(args.config)
    settings = load_yaml(cfg)

    cfg_device = settings.get("audio_device", "default")
    device = args.device or cfg_device

    filename = args.filename

    if args.bg:
        spawn_background_play(args, device=device, filename=filename)
        return

    file_abs = _p(filename)
    print(f"🎧 Device utilisé : {device}")
    print(f"▶️ Lecture : {file_abs}")

    repeats = int(args.repeat) if args.repeat is not None else 1
    if repeats < 1:
        repeats = 1

    try:
        if args.loop:
            while True:
                engine = get_engine(device)
                engine.play_any_file(str(file_abs))
        else:
            for _ in range(repeats):
                engine = get_engine(device)
                engine.play_any_file(str(file_abs))
    except KeyboardInterrupt:
        print("\n⏹️ Lecture interrompue.")


def cmd_status(args: argparse.Namespace) -> None:
    print("📟 Toune-o-matic status")
    pid = read_pid()
    meta = load_yaml(META_FILE) if META_FILE.exists() else {}

    if pid is None:
        print("ℹ️ Aucun lecteur en arrière-plan (pas de PID).")
        return

    running = pid_exists(pid)
    print(f"PID: {pid}")
    print(f"En cours: {'OUI' if running else 'NON'}")

    if meta:
        print(f"Device: {meta.get('device', '?')}")
        print(f"Fichier: {meta.get('file', '?')}")
        print(f"Démarré: {meta.get('started', '?')}")
    else:
        print("ℹ️ Pas de meta.")

    if not running:
        print("🧹 Nettoyage: PID n’existe plus.")
        clear_state()


def cmd_stop(args: argparse.Namespace) -> None:
    pid = read_pid()
    if pid is None:
        print("ℹ️ Aucun lecteur en arrière-plan à arrêter (pas de PID).")
        return

    if not pid_exists(pid):
        print("ℹ️ Le PID ne tourne plus. Nettoyage.")
        clear_state()
        return

    print(f"⏹️ Stop: envoi SIGTERM au PID {pid}...")
    try:
        os.killpg(pid, signal.SIGTERM)  # kill the process group
    except ProcessLookupError:
        pass
    except PermissionError:
        # fallback: kill the pid only
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    # Wait a bit
    t0 = time.time()
    while time.time() - t0 < 2.0:
        if not pid_exists(pid):
            break
        time.sleep(0.05)

    if pid_exists(pid):
        print("⚠️ Toujours vivant → SIGKILL")
        try:
            os.killpg(pid, signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

    clear_state()
    print("✅ Arrêt demandé / état nettoyé.")


def cmd_make_test(args: argparse.Namespace) -> None:
    import math
    import struct
    import wave

    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_rate = int(args.rate)
    duration = float(args.seconds)
    freq = float(args.freq)
    channels = int(args.channels)

    wav_path = out_dir / "test.wav"
    mp3_path = out_dir / "test.mp3"

    num_samples = int(sample_rate * duration)

    with wave.open(str(wav_path), "w") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sample_rate)

        for i in range(num_samples):
            v = int(32767 * 0.5 * math.sin(2 * math.pi * freq * i / sample_rate))
            if channels == 1:
                w.writeframesraw(struct.pack("<h", v))
            else:
                w.writeframesraw(struct.pack("<hh", v, v))

    print(f"✅ Fichier WAV généré : {wav_path}")

    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-i", str(wav_path), str(mp3_path)], check=False)
        if mp3_path.exists():
            print(f"✅ Fichier MP3 généré : {mp3_path}")
    else:
        print("⚠️ ffmpeg non installé — MP3 non généré.")


def cmd_doctor(args: argparse.Namespace) -> None:
    print("🩺 Toune-o-matic doctor\n")

    print(f"🐍 Python: {sys.executable}")
    print(f"📦 sys.prefix: {sys.prefix}")
    venv_active = (Path(sys.prefix) / "bin" / "python").exists() and ("venv" in str(Path(sys.prefix)))
    print(f"🧪 venv actif: {'OUI' if venv_active else 'NON'}")

    # Modules
    for mod, label in [("yaml", "yaml (PyYAML)"), ("alsaaudio", "alsaaudio (pyalsaaudio)"), ("pydub", "pydub")]:
        try:
            __import__(mod)
            print(f"✅ module {label}")
        except Exception as e:
            print(f"❌ module {label} : {e}")

    # ffmpeg
    ff = shutil.which("ffmpeg")
    if ff:
        print(f"\n✅ ffmpeg: {ff}")
        try:
            r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
            first = (r.stdout or r.stderr).splitlines()[0] if (r.stdout or r.stderr) else ""
            if first:
                print(f"   ↳ {first}")
        except Exception:
            pass
    else:
        print("\n❌ ffmpeg introuvable")

    # Config
    cfg = _p(args.config)
    settings = load_yaml(cfg)
    if cfg.exists():
        print(f"\n✅ Config trouvée: {cfg}")
        print(f"   ↳ audio_device: {settings.get('audio_device', 'default')}")
    else:
        print(f"\n❌ Config absente: {cfg}")

    # aplay summary
    print("\n🔊 aplay -l (résumé)")
    try:
        subprocess.run(["aplay", "-l"], check=False)
    except Exception as e:
        print(f"❌ aplay -l : {e}")

    # ALSA open test (optional)
    dev = settings.get("audio_device", "default")
    try:
        import alsaaudio
        print(f"\n🎛️ Test ALSA open: {dev}")
        pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_PLAYBACK,
            mode=alsaaudio.PCM_NORMAL,
            device=dev,
            channels=2,
            rate=44100,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=1024,
        )
        pcm.close()
        print("✅ OK (device ouvrable)")
    except Exception as e:
        print(f"❌ ALSA open failed: {e}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run.py")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="Chemin du fichier config YAML")

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("devices", help="Lister les devices ALSA (aplay/arecord)")
    sp.set_defaults(func=cmd_devices)

    sp = sub.add_parser("info", help="Afficher le device audio configuré")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("set-device", help="Écrire audio_device dans la config")
    sp.add_argument("device", help='Ex: "plughw:CARD=BossDAC,DEV=0"')
    sp.set_defaults(func=cmd_set_device)

    sp = sub.add_parser("make-test", help="Générer un fichier test.wav (+ test.mp3 si ffmpeg)")
    sp.add_argument("--seconds", type=float, default=3.0, help="Durée du test (secondes)")
    sp.add_argument("--freq", type=float, default=440.0, help="Fréquence (Hz)")
    sp.add_argument("--rate", type=int, default=44100, help="Sample rate (Hz)")
    sp.add_argument("--channels", type=int, choices=[1, 2], default=1, help="1=mono, 2=stéréo")
    sp.add_argument("--out-dir", default="audio/_local_test", help="Dossier de sortie")
    sp.set_defaults(func=cmd_make_test)

    sp = sub.add_parser("play", help="Jouer un fichier audio")
    sp.add_argument("filename", help="Chemin du fichier à lire")
    sp.add_argument("--device", help="Override device ALSA (sinon config)")
    sp.add_argument("--bg", action="store_true", help="Lecture en arrière-plan")
    sp.add_argument("--no-bg", action="store_false", dest="bg", help=argparse.SUPPRESS)
    sp.add_argument("--loop", action="store_true", help="Boucle infinie (foreground ou bg)")
    sp.add_argument("--repeat", type=int, default=1, help="Nombre de répétitions (foreground ou bg)")
    sp.set_defaults(func=cmd_play)

    sp = sub.add_parser("status", help="État du lecteur en arrière-plan")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("stop", help="Arrêter le lecteur en arrière-plan")
    sp.set_defaults(func=cmd_stop)

    sp = sub.add_parser("doctor", help="Diagnostic venv/config/audio")
    sp.set_defaults(func=cmd_doctor)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()