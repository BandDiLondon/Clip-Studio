#!/usr/bin/env bash
# Installation de Clip Studio sous Linux (testé : Ubuntu 24.04, y compris WSL).
# Usage : bash installer.sh
set -e
cd "$(dirname "$0")"
echo "=============================================="
echo "  Installation de Clip Studio (Linux)"
echo "=============================================="

# ---------- 1. Paquets système : Python (venv), ffmpeg, polices, unzip
manque=()
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null || manque+=(python3)
python3 -c 'import ensurepip, venv' 2>/dev/null || manque+=(python3-venv)
command -v ffmpeg >/dev/null || manque+=(ffmpeg)
command -v curl >/dev/null || manque+=(curl ca-certificates)
[ -f /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf ] || manque+=(fonts-liberation)
if [ ${#manque[@]} -gt 0 ]; then
  echo "[1/5] Paquets manquants : ${manque[*]}"
  if command -v apt-get >/dev/null; then
    sudo apt-get update && sudo apt-get install -y "${manque[@]}"
  else
    echo "Installe-les avec le gestionnaire de paquets de ta distribution, puis relance ce script."; exit 1
  fi
fi
echo "[1/5] Python, ffmpeg, polices : OK"

# ---------- 2. Environnement virtuel + dépendances (versions testées)
[ -x .venv/bin/python ] || { echo "[2/5] Création de .venv…"; python3 -m venv .venv; }
PY=.venv/bin/python
"$PY" -m pip install --upgrade pip
echo "[2/5] torch (CPU)…"
"$PY" -m pip install torch==2.14.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
echo "[2/5] Dépendances…"
"$PY" -m pip install -r requirements.txt \
  || { echo "Échec pip. Essayer : $PY -m pip install -r requirements-complet.txt"; exit 1; }

# ---------- 3. ffmpeg : vérification des filtres utilisés
ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass " || echo "⚠ ffmpeg sans filtre « ass » : le karaoké ne s'affichera pas"
echo "[3/5] ffmpeg : OK"

# ---------- 4. Real-ESRGAN (agrandissement des cases ; carte graphique compatible Vulkan)
if [ ! -x tools/realesrgan/realesrgan-ncnn-vulkan ]; then
  echo "[4/5] Téléchargement de Real-ESRGAN…"
  mkdir -p tools/realesrgan
  z=$(mktemp --suffix=.zip)
  curl -fL -o "$z" https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip
  "$PY" -m zipfile -e "$z" tools/realesrgan
  rm -f "$z"
  chmod +x tools/realesrgan/realesrgan-ncnn-vulkan
fi
echo "[4/5] Real-ESRGAN : OK (sans GPU Vulkan : Découpe avec --scale 1)"

# ---------- 5. Vérification
chmod +x clip-studio.sh sauvegarder-projets.sh 2>/dev/null || true
echo
echo "[5/5] Vérification :"
PYTHONUTF8=1 "$PY" -m clip check || true
echo
echo "Optionnel : Claude Code (abonnement Claude Pro/Max) pour les boutons « avec Claude » : https://claude.com/claude-code"
echo "Pour commencer : ./clip-studio.sh"
