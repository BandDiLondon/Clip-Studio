#!/usr/bin/env bash
# macOS : double-clic dans le Finder pour lancer Clip Studio. Garder la fenêtre du Terminal ouverte ;
# la fermer arrête Clip Studio. (Première fois : clic droit → Ouvrir, si macOS bloque le fichier.)
# macOS: double-click in the Finder to start Clip Studio. Keep the Terminal window open; closing it stops
# Clip Studio. (First time: right-click → Open, if macOS blocks the file.)
cd "$(dirname "$0")" && exec ./clip-studio.sh
