# src/api/routes_metadata.py
from flask import Blueprint, jsonify, request, send_from_directory, current_app
from src.core.metadata import MetadataManager
import os

# On crée un "Blueprint" (un groupe de routes)
metadata_bp = Blueprint('metadata', __name__)

# On initialise le gestionnaire (Il utilisera le chemin défini dans metadata.py)
# Sur le Pi, ce sera /mnt/music/Documents
meta_manager = MetadataManager()

@metadata_bp.route('/info/<artist_name>', methods=['GET'])
def get_artist_info(artist_name):
    """
    API: Récupère la bio et l'URL de l'image
    Exemple: GET /api/metadata/info/Pink%20Floyd
    """
    # 1. On récupère le texte
    bio = meta_manager.get_artist_bio(artist_name)
    
    # 2. On s'assure que l'image existe (le script la télécharge si besoin)
    image_path = meta_manager.get_artist_image(artist_name)
    
    # 3. On construit la réponse JSON pour l'interface
    response = {
        "artist": artist_name,
        "bio": bio,
        "has_image": image_path is not None
    }
    return jsonify(response)

@metadata_bp.route('/image/<artist_name>.jpg')
def serve_artist_image(artist_name):
    """
    API: Sert l'image .jpg directement au navigateur
    """
    # Le dossier où sont stockées les images
    img_folder = meta_manager.FOLDERS["artist_imgs"]
    return send_from_directory(img_folder, f"{artist_name}.jpg")