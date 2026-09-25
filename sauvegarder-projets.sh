#!/usr/bin/env bash
# Copie projets/ vers un dossier de sauvegarde (Linux). Ne supprime jamais rien dans la sauvegarde.
# Exclus car recalculables : rendus .mp4 de build/, images extraites des vidéos, cartes de profondeur.
cd "$(dirname "$0")"
conf=projets/.sauvegarde
dest=$( [ -f "$conf" ] && cat "$conf" || echo "$HOME/Sauvegardes/Clip Studio projets" )
echo "Dossier de sauvegarde : $dest"
read -r -p "Entrée pour confirmer, ou tape un autre dossier : " autre
[ -n "$autre" ] && dest=$autre
mkdir -p "$dest" && printf '%s\n' "$dest" > "$conf"
if command -v rsync >/dev/null; then
  rsync -a --update --exclude video_frames --exclude depth --exclude '/*/build/*.mp4' --exclude .sauvegarde \
    projets/ "$dest/"
else
  echo "(rsync absent : copie simple, sans exclusions)"
  cp -ru projets/. "$dest/"
fi
echo "Sauvegarde terminée : $dest (les rendus .mp4 de build/ ne sont pas copiés : ils se refont avec « Rendu final »)"
