#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

MPD_CONF = Path("/etc/mpd.conf")
PLAYLIST_DIR = Path("/var/lib/mpd/playlists")

def get_music_dir():
    if not MPD_CONF.exists():
        return None
    for line in MPD_CONF.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("music_directory"):
            parts = line.split(None, 1)
            if len(parts) == 2:
                return Path(parts[1].strip().strip('"').strip("'"))
    return None

MUSIC_DIR = get_music_dir()

def normalize_line(line: str) -> str:
    line = line.strip()
    if not line or line.startswith("#"):
        return ""
    line = line.replace("\\", "/")

    if "://" in line:   # radios/urls
        return line

    # Harmoniser /mnt/music -> music_directory (si tes .m3u contiennent /mnt/music)
    if MUSIC_DIR:
        md = str(MUSIC_DIR).rstrip("/")
        if line.startswith("/mnt/music/") and md.startswith("/mnt/libraries/mpd"):
            line = md + line[len("/mnt/music"):]

    # Rendre relatif au music_directory (MPD aime ça)
    if MUSIC_DIR:
        md = str(MUSIC_DIR).rstrip("/") + "/"
        if line.startswith(md):
            return line[len(md):].lstrip("/")

    # Playlist venant d’un Mac avec /music/
    if "/music/" in line:
        return line.split("/music/", 1)[1].lstrip("/")

    return line.lstrip("/")

def import_dir(src: Path):
    if not src.exists():
        print(f"❌ Dossier introuvable: {src}")
        sys.exit(1)

    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
    m3us = sorted(src.glob("*.m3u"))
    if not m3us:
        print(f"❌ Aucun .m3u trouvé dans: {src}")
        sys.exit(2)

    for f in m3us:
        out_lines = []
        for raw in f.read_text(errors="ignore").splitlines():
            nl = normalize_line(raw)
            if nl:
                out_lines.append(nl)

        dest = PLAYLIST_DIR / f.name
        dest.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        print(f"✅ Importé: {f.name} ({len(out_lines)} entrées)")

    print("\n➡️ OK. Teste: mpc lsplaylists")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: import_playlists.py /chemin/vers/playlist_mpd")
        sys.exit(0)
    import_dir(Path(sys.argv[1]))
