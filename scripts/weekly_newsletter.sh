#!/bin/bash
# Collecte RSS + envoi newsletter — exécuté chaque lundi à 8h via crontab.
# Installe avec : make cron-install
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Veille hebdomadaire ==="
conda run -n lacoste python main.py collect
conda run -n lacoste python main.py newsletter
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Terminé ==="
