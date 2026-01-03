import os
import requests
import platform

# --- CONFIGURATION INTELLIGENTE ---
# On détecte si on est sur macOS ("Darwin") ou Linux
if platform.system() == "Darwin":
    # MODE DÉVELOPPEMENT (MAC)
    # On met tout dans un dossier de test dans tes Documents
    MUSIC_PATH = os.path.expanduser("~/Documents/TouneOmatic_TestDrive")
    print(f"🖥️ Mode Mac détecté : Utilisation de {MUSIC_PATH}")
else:
    # MODE PRODUCTION (RASPBERRY PI)
    MUSIC_PATH = "/mnt/music"

DOCS_PATH = os.path.join(MUSIC_PATH, "Documents")

FOLDERS = {
    "bios": os.path.join(DOCS_PATH, "Biographies"),
    "artist_imgs": os.path.join(DOCS_PATH, "Photos d'artiste"),
    "reviews": os.path.join(DOCS_PATH, "Critiques d'albums"),
    "covers": os.path.join(DOCS_PATH, "Pochettes")
}

class MetadataManager:
    def __init__(self, base_path=None):
        # Si un chemin spécifique est forcé, on l'utilise
        if base_path:
            global DOCS_PATH
            DOCS_PATH = os.path.join(base_path, "Documents")
            for key in FOLDERS:
                FOLDERS[key] = os.path.join(DOCS_PATH, os.path.basename(FOLDERS[key]))

        # Création automatique des dossiers
        # (Sur Mac, ça créera TouneOmatic_TestDrive s'il n'existe pas)
        for path in FOLDERS.values():
            os.makedirs(path, exist_ok=True)

    def get_artist_bio(self, artist_name):
        """Récupère la bio (Disque -> Sinon Internet -> Sauvegarde)"""
        filename = f"{artist_name}.txt"
        filepath = os.path.join(FOLDERS["bios"], filename)

        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()

        # Simulation simple si pas de réseau ou API
        return f"Biographie simulée pour {artist_name}. (Mode Dev)"

    def get_artist_image(self, artist_name):
        """Récupère la photo HD de l'artiste"""
        filename = f"{artist_name}.jpg"
        filepath = os.path.join(FOLDERS["artist_imgs"], filename)

        if os.path.exists(filepath):
            return filepath
        return None
