#!/usr/bin/env bash
# Installation de Clip Studio sous Linux (testé : Ubuntu 24.04, y compris WSL) et macOS (expérimental, avec Homebrew).
# Usage : bash installer.sh
set -e
cd "$(dirname "$0")"
SYS=$(uname -s)
echo "=============================================="
echo "  Installation de Clip Studio ($([ "$SYS" = Darwin ] && echo "macOS, expérimental" || echo Linux))"
echo "=============================================="

# vérifie l'empreinte SHA256 d'un fichier téléchargé (sha256sum sous Linux, shasum sous macOS)
verifier() {
  if command -v sha256sum >/dev/null; then echo "$1  $2" | sha256sum -c --status
  else echo "$1  $2" | shasum -a 256 -c --status; fi \
    || { rm -f "$2"; echo "Fichier téléchargé corrompu ou modifié (empreinte SHA256 incorrecte)"; exit 1; }
}

# ---------- 1. Paquets système : Python, ffmpeg, polices
if [ "$SYS" = Darwin ]; then
  # macOS : le Python d'Apple (3.9) est trop ancien ; Python 3.12 et ffmpeg viennent de Homebrew
  command -v brew >/dev/null || { echo "Homebrew est nécessaire : installe-le depuis https://brew.sh (une ligne à coller"
    echo "dans le Terminal), puis relance : bash installer.sh"; exit 1; }
  command -v python3.12 >/dev/null || { echo "[1/5] Installation de Python 3.12 (Homebrew)…"; brew install python@3.12; }
  command -v ffmpeg >/dev/null || { echo "[1/5] Installation de ffmpeg (Homebrew)…"; brew install ffmpeg; }
  PY3=$(command -v python3.12 || echo "$(brew --prefix python@3.12)/bin/python3.12")
else
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
  PY3=python3
fi
echo "[1/5] Python, ffmpeg, polices : OK"

# ---------- 2. Environnement virtuel + dépendances (versions testées)
[ -x .venv/bin/python ] || { echo "[2/5] Création de .venv…"; "$PY3" -m venv .venv; }
PY=.venv/bin/python
"$PY" -m pip install --upgrade pip
echo "[2/5] torch (CPU)…"
if [ "$SYS" = Darwin ]; then
  "$PY" -m pip install torch==2.14.0 torchaudio==2.11.0
else
  "$PY" -m pip install torch==2.14.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
fi
echo "[2/5] Dépendances…"
"$PY" -m pip install -r requirements.txt \
  || { echo "Échec pip. Essayer : $PY -m pip install -r requirements-complet.txt"; exit 1; }
# RapidOCR sans ses dépendances : il exige opencv-python, en conflit avec opencv-python-headless
"$PY" -m pip install --no-deps rapidocr==3.9.2

# ---------- 3. ffmpeg : vérification des filtres utilisés
ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass " || echo "⚠ ffmpeg sans filtre « ass » : le karaoké ne s'affichera pas"
echo "[3/5] ffmpeg : OK"

# ---------- 4. Real-ESRGAN (agrandissement des cases ; carte graphique compatible Vulkan, ou Metal sous macOS)
if [ ! -x tools/realesrgan/realesrgan-ncnn-vulkan ]; then
  echo "[4/5] Téléchargement de Real-ESRGAN…"
  mkdir -p tools/realesrgan
  z=$(mktemp "${TMPDIR:-/tmp}/realesrgan.XXXXXX")
  url=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424
  if [ "$SYS" = Darwin ]; then
    curl -fL -o "$z" "$url-macos.zip"
    verifier e0ad05580abfeb25f8d8fb55aaf7bedf552c375b5b4d9bd3c8d59764d2cc333a "$z"
  else
    curl -fL -o "$z" "$url-ubuntu.zip"
    verifier e5aa6eb131234b87c0c51f82b89390f5e3e642b7b70f2b9bbe95b6a285a40c96 "$z"
  fi
  "$PY" -m zipfile -e "$z" tools/realesrgan
  rm -f "$z"
  chmod +x tools/realesrgan/realesrgan-ncnn-vulkan
  [ "$SYS" = Darwin ] && xattr -dr com.apple.quarantine tools/realesrgan 2>/dev/null || true
fi
echo "[4/5] Real-ESRGAN : OK (sans carte graphique compatible : agrandissement classique, un peu moins net)"

# ---------- 5. Vérification
chmod +x clip-studio.sh sauvegarder-projets.sh "Clip Studio.command" 2>/dev/null || true
echo
echo "[5/5] Vérification :"
PYTHONUTF8=1 "$PY" -m clip check || true
echo
echo "Optionnel : Claude Code (abonnement Claude Pro/Max) pour les boutons « avec Claude » : https://claude.com/claude-code"
if [ "$SYS" = Darwin ]; then
  echo "Pour commencer : double-clic sur « Clip Studio.command » (ou ./clip-studio.sh dans le Terminal)"
else
  echo "Pour commencer : ./clip-studio.sh"
fi
