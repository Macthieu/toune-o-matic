# src/core/metadata.py
import os
import requests
import json
import time

# CONFIGURATION DES CHEMINS (À adapter selon si on est sur Mac ou Pi)
# Sur le Pi ce sera /mnt/music/Documents
# Sur le Mac pour tester, on mettra un dossier local
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
        # Si on force un chemin (pour tester sur Mac)
        if base_path:
            global DOCS_PATH
            DOCS_PATH = os.path.join(base_path, "Documents")
            for key in FOLDERS:
                FOLDERS[key] = os.path.join(DOCS_PATH, os.path.basename(FOLDERS[key]))

        # Création automatique des dossiers s'ils n'existent pas
        for path in FOLDERS.values():
            os.makedirs(path, exist_ok=True)
            
        print(f"📂 Gestionnaire de métadonnées initialisé dans : {DOCS_PATH}")

    def get_artist_bio(self, artist_name):
        """Récupère la bio (Disque -> Sinon Internet -> Sauvegarde)"""
        filename = f"{artist_name}.txt"
        filepath = os.path.join(FOLDERS["bios"], filename)

        # 1. Vérifier si on l'a déjà sur le disque
        if os.path.exists(filepath):
            print(f"✅ Bio trouvée localement pour : {artist_name}")
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()

        # 2. Sinon, on cherche sur Internet (TheAudioDB)
        print(f"🌍 Recherche de la bio pour : {artist_name}...")
        bio_text = self._fetch_bio_from_web(artist_name)

        # 3. On sauvegarde
        if bio_text:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(bio_text)
            print(f"💾 Bio sauvegardée pour : {artist_name}")
            return bio_text
        
        return "Biographie non disponible."

    def get_artist_image(self, artist_name):
        """Récupère la photo HD de l'artiste"""
        filename = f"{artist_name}.jpg"
        filepath = os.path.join(FOLDERS["artist_imgs"], filename)

        if os.path.exists(filepath):
            return filepath

        print(f"🌍 Téléchargement photo pour : {artist_name}...")
        img_url = self._fetch_artist_image_url(artist_name)
        
        if img_url:
            self._download_image(img_url, filepath)
            return filepath
        return None

    def _fetch_bio_from_web(self, artist):
        """Interroge TheAudioDB pour la bio"""
        # API Gratuite de test '2' de TheAudioDB
        url = f"https://www.theaudiodb.com/api/v1/json/2/search.php?s={artist}"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if data and data['artists']:
                # On essaie de trouver la bio en Français, sinon Anglais
                bio = data['artists'][0].get('strBiographyFR')
                if not bio:
                    bio = data['artists'][0].get('strBiographyEN')
                return bio
        except Exception as e:
            print(f"❌ Erreur API : {e}")
        return None

    def _fetch_artist_image_url(self, artist):
        """Trouve l'URL de la meilleure photo"""
        url = f"https://www.theaudiodb.com/api/v1/json/2/search.php?s={artist}"
        try:
            resp = requests.get(url)
            data = resp.json()
            if data and data['artists']:
                return data['artists'][0].get('strArtistThumb') # Photo HD
        except:
            pass
        return None

    def _download_image(self, url, dest_path):
        try:
            resp = requests.get(url, stream=True)
            if resp.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                print(f"📸 Image sauvegardée : {dest_path}")
        except Exception as e:
            print(f"Erreur téléchargement image: {e}")

# --- ZONE DE TEST POUR LE MAC ---
if __name__ == "__main__":
    # On simule le disque dur dans un dossier temporaire sur le Mac
    test_path = os.path.expanduser("~/Documents/TouneOmatic_TestDrive")
    
    manager = MetadataManager(base_path=test_path)
    
    # Test avec quelques artistes
    print("\n--- TEST BIOGRAPHIE ---")
    print(manager.get_artist_bio("Pink Floyd")[:200] + "...") # On affiche le début
    
    print("\n--- TEST PHOTO ---")
    manager.get_artist_image("Pink Floyd")
    
    print("\n--- TEST ARTISTE FRANCAIS ---")
    print(manager.get_artist_bio("Jean Leloup")[:200] + "...")
    manager.get_artist_image("Jean Leloup")