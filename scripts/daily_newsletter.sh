#!/bin/bash
# Collecte RSS + envoi des 10 articles les plus pertinents jamais envoyés.
# Exécuté chaque jour à 8h via crontab — installe avec : make cron-install
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Veille quotidienne ==="
conda run -n lacoste python main.py collect
conda run -n lacoste python main.py newsletter --limit 10 --prod
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Terminé ==="
