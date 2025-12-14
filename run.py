import sys
import yaml
from src.core.audio_engine import AudioEngine

def load_settings():
    with open("config/settings.yaml", "r") as f:
        return yaml.safe_load(f)

def main():
    if len(sys.argv) < 3:
        print("Usage: python run.py play <filename>")
        sys.exit(1)

    command = sys.argv[1]
    filename = sys.argv[2]
    settings = load_settings()
    device = settings["audio_device"]

    player = AudioEngine(device)

    if command == "play":
        print(f"Lecture du fichier : {filename} sur {device}")
        player.play_any_file(filename)
    else:
        print("Commande non reconnue.")

if __name__ == "__main__":
    main()
