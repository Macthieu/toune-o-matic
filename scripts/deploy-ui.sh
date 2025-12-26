#!/usr/bin/env bash
set -euo pipefail
sudo install -m 0644 ~/toune-o-matic/ui/index.html /var/www/toune-ui/index.html
sudo nginx -t
sudo systemctl reload nginx
echo "✅ UI déployée"
