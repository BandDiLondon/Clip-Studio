#!/usr/bin/env bash
# macOS : double-clic dans le Finder pour lancer Clip Studio. Garder la fenêtre du Terminal ouverte ;
# la fermer arrête Clip Studio. (Première fois : clic droit → Ouvrir, si macOS bloque le fichier.)
cd "$(dirname "$0")" && exec ./clip-studio.sh
