#!/usr/bin/env bash
# Copie projets/ vers un dossier de sauvegarde (Linux, macOS). Ne supprime jamais rien dans la sauvegarde.
# Exclus car recalculables : rendus .mp4 de build/, images extraites des vidéos, cartes de profondeur.
# Langue des messages : CLIP_LANG (fr / en), sinon celle du système (LANG).
cd "$(dirname "$0")"
case "${CLIP_LANG:-${LANG:-fr}}" in fr*) EN= ;; *) EN=1 ;; esac
m() { if [ -n "$EN" ]; then echo "$2"; else echo "$1"; fi; }
conf=projets/.sauvegarde
dest=$( [ -f "$conf" ] && cat "$conf" || echo "$HOME/$(m Sauvegardes Backups)/Clip Studio $(m projets projects)" )
m "Dossier de sauvegarde : $dest" "Backup folder: $dest"
read -r -p "$(m "Entrée pour confirmer, ou tape un autre dossier : " "Enter to confirm, or type another folder: ")" autre
[ -n "$autre" ] && dest=$autre
mkdir -p "$dest" && printf '%s\n' "$dest" > "$conf"
if command -v rsync >/dev/null; then
  rsync -a --update --exclude video_frames --exclude depth --exclude '/*/build/*.mp4' --exclude .sauvegarde \
    projets/ "$dest/"
else
  m "(rsync absent : copie simple, sans exclusions)" "(rsync missing: simple copy, without exclusions)"
  cp -R projets/. "$dest/"
fi
m "Sauvegarde terminée : $dest (les rendus .mp4 de build/ ne sont pas copiés : ils se refont avec « Rendu final »)" \
  "Backup done: $dest (the .mp4 renders in build/ are not copied: they can be redone with “Final render”)"
