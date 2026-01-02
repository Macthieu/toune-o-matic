import subprocess
import re

print("🔍 Scan du matériel audio en cours...")

# 1. On scanne les cartes avec aplay
res = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
cards = []

# Regex pour trouver: card 1: Hifiberry [Hifiberry DAC+], ...
for line in res.stdout.splitlines():
    if line.startswith("card"):
        # On capture l'ID et le nom entre crochets qui est le plus précis
        m = re.search(r'card (\d+):.*?\[(.*?)\]', line)
        if m:
            c_id = m.group(1)
            c_name = m.group(2)
            # On ignore la carte Loopback si elle existe
            if "Loopback" not in c_name:
                cards.append((c_id, c_name))

print(f"✅ {len(cards)} cartes trouvées : {', '.join([c[1] for c in cards])}")

# 2. On prépare le contenu de mpd.conf
mpd_conf = """
music_directory "/mnt/music"
playlist_directory "/var/lib/mpd/playlists"
db_file "/var/lib/mpd/tag_cache"
log_file "/var/log/mpd/mpd.log"
pid_file "/run/mpd/pid"
state_file "/var/lib/mpd/state"
user "mpd"
bind_to_address "0.0.0.0"
port "6600"
auto_update "yes"

# --- SORTIE 1 : BLUETOOTH ---
audio_output {
    type "alsa"
    name "🎧 Bluetooth"
    device "bluealsa"
    mixer_type "software"
}
"""

# 3. On ajoute une sortie pour chaque carte trouvée
for c_id, c_name in cards:
    clean_name = c_name.replace('"', '') # Sécurité
    print(f"   -> Ajout de la sortie : 🔊 {clean_name}")
    mpd_conf += f"""
# Sortie détectée automatiquement
audio_output {{
    type "alsa"
    name "🔊 {clean_name}"
    device "hw:{c_id},0"
    mixer_type "software"
}}
"""

# 4. On ajoute Snapcast à la fin (optionnel)
mpd_conf += """
# --- SORTIE MULTIROOM ---
audio_output {
    type "fifo"
    name "📡 Multiroom (Snapcast)"
    path "/tmp/snapfifo"
    format "48000:16:2"
    mixer_type "software"
}
"""

# 5. On écrit le fichier
with open("/etc/mpd.conf", "w") as f:
    f.write(mpd_conf)

print("✅ Configuration /etc/mpd.conf générée avec succès !")
