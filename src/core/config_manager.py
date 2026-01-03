import json
import os

# Fichier où seront sauvegardés tes réglages
CONFIG_FILE = 'toune_settings.json'

# Les réglages par défaut (Style Volumio)
DEFAULT_CONFIG = {
    "system": {
        "player_name": "Toune-o-matic",
        "startup_sound": True
    },
    "audio": {
        "output_device": "jack",  # hifiberry, usb, hdmi...
        "mixer_type": "software", # hardware, none
        "dual_audio": False,      # Le fameux mode Multiroom (DAC + BT)
        "volume_init": 40
    },
    "playback": {
        "buffer_size": "8 MB",    # 2MB, 8MB, 12MB
        "dsd_mode": "direct",     # direct, dop, pcm
        "fade_in_out": True
    },
    "plugins": {
        "metadata_fetcher": True,
        "cockpit_integration": True,
        "bluetooth_controller": True
    }
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.load()

    def load(self):
        """Charge la config depuis le fichier JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    # On fusionne avec les défauts pour éviter les bugs si on ajoute des options
                    self._merge(self.config, saved)
            except Exception as e:
                print(f"Erreur chargement config: {e}")

    def save(self):
        """Sauvegarde la config"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Erreur sauvegarde config: {e}")

    def get(self, section, key):
        return self.config.get(section, {}).get(key)

    def set(self, section, key, value):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save()

    def _merge(self, defaults, saved):
        """Fusion récursive simple"""
        for key, value in saved.items():
            if key in defaults and isinstance(defaults[key], dict) and isinstance(value, dict):
                self._merge(defaults[key], value)
            else:
                defaults[key] = value

# Instance globale
config_manager = ConfigManager()