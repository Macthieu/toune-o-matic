import sqlite3
import os
import logging

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "library.db")
logger = logging.getLogger("DB")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Table principale des chansons
    c.execute('''CREATE TABLE IF NOT EXISTS tracks (
        path TEXT PRIMARY KEY,
        title TEXT,
        artist TEXT,
        album TEXT,
        genre TEXT,
        duration INTEGER,
        year INTEGER
    )''')
    
    # Index pour recherche rapide (Full Text Search)
    # On crée une table virtuelle qui permet de chercher "Pink Floyd Wall" instantanément
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
        title, artist, album, genre, path, content='tracks', content_rowid='rowid'
    )''')
    
    # Triggers pour garder FTS synchronisé avec la table tracks
    c.execute('''CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
      INSERT INTO tracks_fts(rowid, title, artist, album, genre, path) VALUES (new.rowid, new.title, new.artist, new.album, new.genre, new.path);
    END;''')
    c.execute('''CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
      INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album, genre, path) VALUES('delete', old.rowid, old.title, old.artist, old.album, old.genre, old.path);
    END;''')
    c.execute('''CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
      INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album, genre, path) VALUES('delete', old.rowid, old.title, old.artist, old.album, old.genre, old.path);
      INSERT INTO tracks_fts(rowid, title, artist, album, genre, path) VALUES (new.rowid, new.title, new.artist, new.album, new.genre, new.path);
    END;''')

    conn.commit()
    conn.close()
    logger.info("Base de données initialisée.")

# Initialiser au chargement du module si pas fait
if not os.path.exists(DB_PATH):
    init_db()
