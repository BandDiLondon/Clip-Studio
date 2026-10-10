#!/usr/bin/env bash
# Lance Clip Studio (interface web locale) sous Linux et macOS. Garder ce terminal ouvert ; Ctrl+C l'arrête.
# Langue des messages : CLIP_LANG (fr / en), sinon celle du système (LANG).
cd "$(dirname "$0")"
case "${CLIP_LANG:-${LANG:-fr}}" in fr*) export CLIP_LANG=fr ;; *) export CLIP_LANG=en ;; esac
if [ ! -x .venv/bin/python ]; then
  if [ "$CLIP_LANG" = en ]; then echo "Python environment not found: run  bash installer.sh  first"
  else echo "Environnement Python introuvable : lance d'abord  bash installer.sh"; fi
  exit 1
fi
export PYTHONUTF8=1
exec .venv/bin/python -m clip web
