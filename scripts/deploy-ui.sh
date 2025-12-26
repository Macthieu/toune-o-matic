#!/usr/bin/env bash
set -euo pipefail

# Déploie tout le dossier UI (index + assets/) vers Nginx
SRC_DIR="$HOME/toune-o-matic/ui/"
DST_DIR="/var/www/toune-ui/"

sudo mkdir -p "$DST_DIR"
sudo rsync -a --delete "$SRC_DIR" "$DST_DIR"

sudo nginx -t
sudo systemctl reload nginx

echo "✅ UI déployée (index.html + assets/)"
