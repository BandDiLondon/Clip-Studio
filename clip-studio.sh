#!/usr/bin/env bash
# Lance Clip Studio (interface web locale) sous Linux et macOS. Garder ce terminal ouvert ; Ctrl+C l'arrête.
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Environnement Python introuvable : lance d'abord  bash installer.sh"; exit 1; }
export PYTHONUTF8=1
exec .venv/bin/python -m clip web
