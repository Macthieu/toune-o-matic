# Fichier: src/core/mpd_wrapper.py
import logging
import threading
from mpd import MPDClient, ConnectionError, CommandError

logger = logging.getLogger("MPDWrapper")

class MPDWrapper:
    def __init__(self, host="127.0.0.1", port=6600):
        self.host = host
        self.port = port
        self._client = MPDClient()
        self._client.timeout = None  # Infini pour éviter les coupures sur gros scans
        self._connected = False
        # Le verrou empêche deux threads (ex: Status + Ajout Queue) de parler en même temps
        self._lock = threading.Lock()

    def connect(self):
        try:
            self._client.connect(self.host, self.port)
            self._connected = True
            logger.info(f"Connecté à MPD {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Echec connexion MPD: {e}")
            self._connected = False

    def ensure_connection(self):
        try:
            self._client.ping()
        except (ConnectionError, BrokenPipeError, OSError):
            logger.warning("Connexion MPD perdue, reconnexion...")
            try:
                self._client.disconnect()
            except: pass
            self._connected = False
            self.connect()

    def exec(self, func, *args, **kwargs):
        """Exécute une commande de manière Thread-Safe."""
        with self._lock:  # <-- C'est ici que la magie opère
            self.ensure_connection()
            try:
                return func(self._client, *args, **kwargs)
            except (ConnectionError, BrokenPipeError, OSError):
                # Retry once
                logger.warning("Erreur réseau MPD, nouvelle tentative...")
                self.connect()
                try:
                    return func(self._client, *args, **kwargs)
                except Exception as e2:
                    logger.error(f"Echec final commande MPD: {e2}")
                    return None
            except CommandError as e:
                logger.error(f"Erreur logique MPD (fichier introuvable ?): {e}")
                return None
            except Exception as e:
                logger.error(f"Erreur inconnue MPD: {e}")
                return None

# Instance globale
mpd_wrapper = MPDWrapper()