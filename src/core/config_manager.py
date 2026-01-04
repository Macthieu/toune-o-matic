import json
import os

CONFIG_FILE = 'toune_settings.json'

DEFAULT_CONFIG = {
    "system": {
        "player_name": "Toune-o-matic",
        "startup_sound": True
    },
    "audio": {
        "output_device": "jack",
        "mixer_type": "software",
        "dual_audio": False,
        # --- NOUVEAU: Options Volume ---
        "vol_startup": 40,      # Volume au démarrage
        "vol_max": 100,         # Limite max pour protéger les enceintes
        "vol_curve": "log",     # 'log' (naturel) ou 'linear'
        "vol_steps": 5          # Saut de volume par clic
    },
    "playback": {
        "buffer_size": "8 MB",
        "dsd_mode": "direct",
        # --- NOUVEAU: Options Lecture ---
        "buffer_before_play": "10%", # Pour éviter les coupures au début
        "volume_normalization": False, # Égalisation du volume auto
        "auto_update": False
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
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    self._merge(self.config, saved)
            except Exception as e:
                print(f"Erreur chargement config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Erreur sauvegarde config: {e}")

    def get(self, section, key): return self.config.get(section, {}).get(key)
    
    def set(self, section, key, value):
        if section not in self.config: self.config[section] = {}
        self.config[section][key] = value
        self.save()

    def _merge(self, defaults, saved):
        for key, value in saved.items():
            if key in defaults and isinstance(defaults[key], dict) and isinstance(value, dict):
                self._merge(defaults[key], value)
            else:
                defaults[key] = value

config_manager = ConfigManager()