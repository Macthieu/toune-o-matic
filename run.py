import argparse
import yaml
import os
import sys
from src.core.audio_engine import AudioEngine

def main():
    parser = argparse.ArgumentParser(description="Toune-o-matic – Lecteur audio CLI")
    parser.add_argument("command", choices=["play", "info", "make-test"], help="Commande à exécuter")
    parser.add_argument("filename", nargs="?", help="Nom du fichier audio à lire (pour la commande 'play')")
    args = parser.parse_args()

    # Charger la configuration YAML
    config_path = os.path.join("config", "settings.yaml")
    if not os.path.exists(config_path):
        print(f"Fichier de configuration introuvable : {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        settings = yaml.safe_load(f)

    device = settings.get("audio_device", "default")

    if args.command == "info":
        print(f"🎧 Appareil audio actif : {device}")

    elif args.command == "play":
        if not args.filename:
            print("Erreur : vous devez spécifier un fichier à lire.")
            sys.exit(1)
        player = AudioEngine(device)
        print(f"Lecture du fichier : {args.filename} sur {device}")
        player.play_any_file(args.filename)

    elif args.command == "make-test":
        import wave
        import struct
        import math
        import shutil
        import subprocess

        sample_rate = 44100
        duration = 3  # secondes
        frequency = 440.0  # Hz – La (A4)

        output_file = "test.wav"
        num_samples = int(sample_rate * duration)

        with wave.open(output_file, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16 bits
            wav_file.setframerate(sample_rate)

            for i in range(num_samples):
                value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
                data = struct.pack('<h', value)
                wav_file.writeframesraw(data)

        print(f"✅ Fichier {output_file} généré.")

        if shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-i", output_file, "test.mp3"])
            print("✅ Fichier test.mp3 généré.")
        else:
            print("⚠️  ffmpeg non installé – MP3 non généré.")

if __name__ == "__main__":
    main()
