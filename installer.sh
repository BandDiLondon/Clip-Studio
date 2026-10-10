#!/usr/bin/env bash
# Installation de Clip Studio sous Linux (testé : Ubuntu 24.04, y compris WSL) et macOS (expérimental, avec Homebrew).
# Usage : bash installer.sh      Langue des messages : CLIP_LANG (fr / en), sinon celle du système (LANG).
set -e
cd "$(dirname "$0")"
SYS=$(uname -s)
case "${CLIP_LANG:-${LANG:-fr}}" in fr*) export CLIP_LANG=fr ;; *) export CLIP_LANG=en ;; esac
m() { if [ "$CLIP_LANG" = en ]; then echo "$2"; else echo "$1"; fi; }
echo "=============================================="
if [ "$SYS" = Darwin ]; then m "  Installation de Clip Studio (macOS, expérimental)" "  Clip Studio setup (macOS, experimental)"
else m "  Installation de Clip Studio (Linux)" "  Clip Studio setup (Linux)"; fi
echo "=============================================="

# vérifie l'empreinte SHA256 d'un fichier téléchargé (par Python : sha256sum diffère entre Linux et macOS)
verifier() {
  [ "$("$PY" -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$2")" = "$1" ] \
    || { rm -f "$2"; m "Fichier téléchargé corrompu ou modifié (empreinte SHA256 incorrecte)" \
                       "Downloaded file corrupted or modified (wrong SHA256 checksum)"; exit 1; }
}

# ---------- 1. Paquets système : Python, ffmpeg, polices
if [ "$SYS" = Darwin ]; then
  # macOS : le Python d'Apple (3.9) est trop ancien ; Python 3.12 et ffmpeg viennent de Homebrew
  command -v brew >/dev/null || {
    m "Homebrew est nécessaire : installe-le depuis https://brew.sh (une ligne à coller dans le Terminal), puis relance : bash installer.sh" \
      "Homebrew is required: install it from https://brew.sh (one line to paste in the Terminal), then run again: bash installer.sh"
    exit 1; }
  command -v python3.12 >/dev/null || { m "[1/5] Installation de Python 3.12 (Homebrew)…" "[1/5] Installing Python 3.12 (Homebrew)…"
    brew install python@3.12; }
  # le ffmpeg de base de Homebrew n'a pas libass (karaoké) : « ffmpeg-full », non ajouté au PATH, d'où les liens
  # dans tools/ffmpeg/bin (Clip Studio met ce dossier en tête du PATH)
  if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass "; then
    brew list ffmpeg-full >/dev/null 2>&1 || { m "[1/5] Installation de ffmpeg (Homebrew, ffmpeg-full)…" "[1/5] Installing ffmpeg (Homebrew, ffmpeg-full)…"
      brew install ffmpeg-full; }
    mkdir -p tools/ffmpeg/bin
    ln -sf "$(brew --prefix ffmpeg-full)/bin/ffmpeg" "$(brew --prefix ffmpeg-full)/bin/ffprobe" tools/ffmpeg/bin/
  fi
  PY3=$(command -v python3.12 || echo "$(brew --prefix python@3.12)/bin/python3.12")
else
  manque=()
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null || manque+=(python3)
  python3 -c 'import ensurepip, venv' 2>/dev/null || manque+=(python3-venv)
  command -v ffmpeg >/dev/null || manque+=(ffmpeg)
  command -v curl >/dev/null || manque+=(curl ca-certificates)
  [ -f /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf ] || manque+=(fonts-liberation)
  if [ ${#manque[@]} -gt 0 ]; then
    m "[1/5] Paquets manquants : ${manque[*]}" "[1/5] Missing packages: ${manque[*]}"
    if command -v apt-get >/dev/null; then
      sudo apt-get update && sudo apt-get install -y "${manque[@]}"
    else
      m "Installe-les avec le gestionnaire de paquets de ta distribution, puis relance ce script." \
        "Install them with your distribution's package manager, then run this script again."; exit 1
    fi
  fi
  PY3=python3
fi
m "[1/5] Python, ffmpeg, polices : OK" "[1/5] Python, ffmpeg, fonts: OK"

# ---------- 2. Environnement virtuel + dépendances (versions testées)
[ -x .venv/bin/python ] || { m "[2/5] Création de .venv…" "[2/5] Creating .venv…"; "$PY3" -m venv .venv; }
PY=.venv/bin/python
"$PY" -m pip install --upgrade pip
echo "[2/5] torch (CPU)…"
if [ "$SYS" = Darwin ]; then
  "$PY" -m pip install torch==2.14.0 torchaudio==2.11.0
else
  "$PY" -m pip install torch==2.14.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
fi
m "[2/5] Dépendances…" "[2/5] Dependencies…"
"$PY" -m pip install -r requirements.txt \
  || { m "Échec de pip. Essayer : $PY -m pip install -r requirements-complet.txt" \
         "pip failed. Try: $PY -m pip install -r requirements-complet.txt"; exit 1; }
# RapidOCR sans ses dépendances : il exige opencv-python, en conflit avec opencv-python-headless
"$PY" -m pip install --no-deps rapidocr==3.9.2

# ---------- 3. ffmpeg : vérification des filtres utilisés
[ -d tools/ffmpeg/bin ] && export PATH="$PWD/tools/ffmpeg/bin:$PATH"
ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass " \
  || m "⚠ ffmpeg sans filtre « ass » : le karaoké ne s'affichera pas" "⚠ ffmpeg without the “ass” filter: the karaoke will not show"
echo "[3/5] ffmpeg : OK"

# ---------- 4. Real-ESRGAN (agrandissement des cases ; carte graphique compatible Vulkan, ou Metal sous macOS)
if [ ! -x tools/realesrgan/realesrgan-ncnn-vulkan ]; then
  m "[4/5] Téléchargement de Real-ESRGAN…" "[4/5] Downloading Real-ESRGAN…"
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
m "[4/5] Real-ESRGAN : OK (sans carte graphique compatible : agrandissement classique, un peu moins net)" \
  "[4/5] Real-ESRGAN: OK (without a compatible graphics card: classic upscaling, a bit less sharp)"

# ---------- 5. Vérification
chmod +x clip-studio.sh sauvegarder-projets.sh "Clip Studio.command" 2>/dev/null || true
echo
m "[5/5] Vérification :" "[5/5] Check:"
PYTHONUTF8=1 "$PY" -m clip check || true
echo
m "Optionnel : Claude Code (abonnement Claude Pro/Max) pour les boutons « avec Claude » : https://claude.com/claude-code" \
  "Optional: Claude Code (Claude Pro/Max subscription) for the “with Claude” buttons: https://claude.com/claude-code"
if [ "$SYS" = Darwin ]; then
  m "Pour commencer : double-clic sur « Clip Studio.command » (ou ./clip-studio.sh dans le Terminal)" \
    "To start: double-click “Clip Studio.command” (or ./clip-studio.sh in the Terminal)"
else
  m "Pour commencer : ./clip-studio.sh" "To start: ./clip-studio.sh"
fi
