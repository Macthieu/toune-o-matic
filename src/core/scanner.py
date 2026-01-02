import time
import logging
import os
from src.core.mpd_wrapper import mpd_wrapper
from src.core.db import get_db, init_db

logger = logging.getLogger("Scanner")

def fetch_files_recursive(path=""):
    """Récupère les fichiers dossier par dossier pour éviter le timeout."""
    results = []
    items = mpd_wrapper.exec(lambda c: c.lsinfo(path))
    if items is None: 
        return []
    
    for item in items:
        if 'directory' in item:
            results.extend(fetch_files_recursive(item['directory']))
        elif 'file' in item:
            results.append(item)
    return results

def safe_get(d, key, default=''):
    """Extrait une valeur unique même si MPD renvoie une liste (tags multiples)."""
    val = d.get(key, default)
    if isinstance(val, list):
        # Si on a plusieurs artistes/genres/dates, on prend le premier
        val = val[0]
    return str(val)

def scan_library():
    start_t = time.time()
    logger.info("Démarrage du scan...")
    
    # 1. Tentative rapide
    files = mpd_wrapper.exec(lambda c: c.listallinfo())
    
    # 2. Plan B si échec
    if files is None:
        logger.warning("⚠️ Scan rapide échoué, passage en mode dossier par dossier...")
        files = fetch_files_recursive("")

    if not files:
        logger.warning("Aucun fichier trouvé.")
        return {"ok": False, "count": 0}

    # 3. Nettoyage des données
    tracks = []
    for f in files:
        if 'file' in f:
            # Extraction sécurisée des champs
            path = f['file']
            title = safe_get(f, 'title', os.path.basename(path))
            artist = safe_get(f, 'artist', 'Unknown')
            album = safe_get(f, 'album', 'Unknown')
            genre = safe_get(f, 'genre', '')
            
            # Durée (peut être 'time' ou 'duration')
            raw_dur = safe_get(f, 'duration', safe_get(f, 'time', '0'))
            try:
                duration = int(float(raw_dur))
            except:
                duration = 0

            # Année (Date)
            raw_date = safe_get(f, 'date', '0')
            # On prend les 4 premiers caractères (ex: "2022-01-01" -> "2022")
            year_str = raw_date[:4]
            year = int(year_str) if year_str.isdigit() else 0

            tracks.append((path, title, artist, album, genre, duration, year))

    # 4. Insertion SQL
    init_db()
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM tracks")
        c.executemany("INSERT INTO tracks (path, title, artist, album, genre, duration, year) VALUES (?, ?, ?, ?, ?, ?, ?)", tracks)
        conn.commit()
        duration = time.time() - start_t
        logger.info(f"✅ Scan terminé : {len(tracks)} titres en {duration:.2f}s")
        return {"ok": True, "count": len(tracks), "time": duration}
        
    except Exception as e:
        logger.error(f"Erreur SQL : {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()