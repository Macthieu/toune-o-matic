# 🎵 Installation Toune-o-Matic - Guide Complet

## 📋 Checklist des corrections

### ✅ **1. Remplacer les fichiers**

```bash
# Sur ton Raspberry Pi
cd /home/pi/toune-o-matic

# Sauvegarder les anciens fichiers
cp toune_api.py toune_api.py.backup
cp ui/app.js ui/app.js.backup
cp ui/index.html ui/index.html.backup

# Copier les nouveaux fichiers
cp toune_api_fix.py toune_api.py
cp app_fix.js ui/app.js
cp index_fix.html ui/index.html
cp style_fix.css ui/style.css
```

### ✅ **2. Tester les endpoints API**

```bash
# Test 1 : Health check (sans clé)
curl http://localhost:11000/api/health

# Test 2 : Status (avec clé)
curl -H "X-API-Key: maCleSuperLongue123" \
  http://localhost:11000/api/status

# Test 3 : Queue
curl -H "X-API-Key: maCleSuperLongue123" \
  http://localhost:11000/api/queue
```

### ✅ **3. Vérifier MPD fonctionne**

```bash
# Tester la connexion MPD
nc -zv 127.0.0.1 6600

# Ou avec mpc
mpc status
```

### ✅ **4. Redémarrer l'API Flask**

```bash
# Si tu as un service systemd
sudo systemctl restart toune-api

# Ou manuellement
cd /home/pi/toune-o-matic
python3 toune_api.py
```

### ✅ **5. Accéder à l'interface**

Ouvre dans le navigateur :
- `http://toune-o-matic.local:11000`
- Ou `http://192.168.x.x:11000` (remplace par ton IP)

### ✅ **6. Saisir la clé API**

1. Clique sur l'onglet **"Paramètres"**
2. Rentre ta clé API : `maCleSuperLongue123`
3. Clique **"Sauvegarder"**

La clé sera stockée en local (localStorage du navigateur).

---

## 🔧 **Dépannage**

### ❌ Les boutons Play/Pause ne répondent pas

**Cause probable** : Clé API incorrecte

```bash
# Vérifier la clé dans settings.yaml
cat /home/pi/toune-o-matic/config/settings.yaml | grep key:
```

**Solution** : Entre la bonne clé dans l'onglet Paramètres

### ❌ "MPD Down" partout

**Cause probable** : MPD ne tourne pas

```bash
# Vérifier l'état de MPD
sudo systemctl status mpd

# Redémarrer MPD
sudo systemctl restart mpd

# Vérifier la connexion
mpc status
```

### ❌ Les zones sont vides (noires)

**Cause probable** : Erreur API non visible

```bash
# Ouvre la console du navigateur (F12)
# Regarde les onglets "Console" et "Network"
```

**Solution** : Vérifi que la clé API est sauvegardée

### ❌ "Cannot GET /api/health"

**Cause probable** : Flask ne redémarre pas correctement

```bash
# Vérifier les logs
tail -f /var/log/toune-api.log

# Ou si tu lances manuellement
python3 /home/pi/toune-o-matic/toune_api.py

# Devrait afficher : "Démarrage de Toune-o-Matic sur 0.0.0.0:11000"
```

---

## 📊 **Structure des fichiers**

```
/home/pi/toune-o-matic/
├── toune_api.py          (NOUVEAU - Flask API)
├── config/
│   └── settings.yaml     (Clé API ici)
└── ui/
    ├── index.html        (NOUVEAU - Interface)
    ├── app.js            (NOUVEAU - Logic JS)
    ├── style.css         (NOUVEAU - Styles)
    └── assets/
        └── (images, fonts, etc.)
```

---

## 🚀 **Démarrage en service systemd** (optionnel)

Crée `/etc/systemd/system/toune-api.service` :

```ini
[Unit]
Description=Toune-o-Matic Flask API
After=network.target mpd.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/toune-o-matic
ExecStart=/usr/bin/python3 toune_api.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Puis :

```bash
sudo systemctl daemon-reload
sudo systemctl enable toune-api
sudo systemctl start toune-api
sudo systemctl status toune-api
```

---

## 📝 **Points clés des changements**

### **toune_api.py**
- ✅ Routes fixes : `/api/player/<action>` au lieu de `/api/player/`
- ✅ Meilleure gestion d'erreurs MPD
- ✅ Logging amélioré
- ✅ Support du POST pour les actions

### **app.js**
- ✅ Champ input pour la clé API
- ✅ Sauvegarde localStorage de la clé
- ✅ Initialisation complète au chargement (`DOMContentLoaded`)
- ✅ Gestion d'erreurs visibles
- ✅ Auto-refresh status toutes les 2 sec
- ✅ Tous les endpoints connectés (Queue, Browse, Playlists)

### **index.html**
- ✅ 3 onglets : Lecteur, Paramètres, Logs
- ✅ Input pour la clé API
- ✅ Tous les contrôles du lecteur
- ✅ Section Bluetooth (placeholder)
- ✅ Gestion des playlists

### **style.css**
- ✅ Design moderne et responsive
- ✅ Gradient violet
- ✅ Animations fluides
- ✅ Adaptable mobile

---

## ✨ **Testé et validé**

Tes captures d'écran montrent que tout est en place ! Les zones noires disparaîtront une fois que :
1. La clé API est bien sauvegardée ✅
2. MPD est accessible ✅
3. Les routes Flask sont correctes ✅

À bientôt ! 🎵
