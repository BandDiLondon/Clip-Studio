@echo off
chcp 65001 >nul
title Installation de Clip Studio
cd /d "%~dp0"
echo ==============================================
echo   Installation de Clip Studio (Windows 10/11)
echo ==============================================
echo.

rem ---------- 1. Python 3.12
set "PYBASE="
py -3.12 -c "import sys" >nul 2>&1 && set "PYBASE=py -3.12"
if not defined PYBASE (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1 && set "PYBASE=python"
)
if not defined PYBASE (
  echo [1/5] Python introuvable : installation de Python 3.12 via winget...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo Python est installe. FERME cette fenetre et relance Installer.bat.
  pause & exit /b 0
)
echo [1/5] Python : %PYBASE%

rem ---------- 2. Environnement virtuel + dépendances
if not exist ".venv\Scripts\python.exe" (
  echo [2/5] Creation de l'environnement .venv...
  %PYBASE% -m venv .venv || (echo Echec de creation du venv & pause & exit /b 1)
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip
echo [2/5] Installation de torch (CPU)...
"%PY%" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu || (echo Echec torch & pause & exit /b 1)
echo [2/5] Installation des dependances...
"%PY%" -m pip install -r requirements.txt || (echo Echec pip & pause & exit /b 1)

rem ---------- 3. ffmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo [3/5] ffmpeg introuvable : installation via winget...
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  set "FFMPEG_NEUF=1"
) else (
  echo [3/5] ffmpeg : deja installe
)

rem ---------- 4. Real-ESRGAN (agrandissement des cases)
if not exist "tools\realesrgan\realesrgan-ncnn-vulkan.exe" (
  echo [4/5] Telechargement de Real-ESRGAN...
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $z=Join-Path $env:TEMP 'realesrgan.zip'; Invoke-WebRequest 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip' -OutFile $z; Expand-Archive $z -DestinationPath 'tools\realesrgan' -Force; Remove-Item $z"
  if errorlevel 1 (echo Echec du telechargement de Real-ESRGAN & pause & exit /b 1)
) else (
  echo [4/5] Real-ESRGAN : deja present
)

rem ---------- 5. Vérification
echo.
echo [5/5] Verification :
set PYTHONUTF8=1
if defined FFMPEG_NEUF (
  echo ffmpeg vient d'etre installe : ferme cette fenetre, puis relance Installer.bat pour la verification finale.
) else (
  "%PY%" -m clip check
)
echo.
echo Optionnel : Claude Code (abonnement Claude Pro/Max) pour les boutons "Rediger avec Claude" :
echo   https://claude.com/claude-code  (ou l'extension Claude Code de VS Code)
echo.
echo Pour commencer : double-clic sur "Clip Studio.bat".
pause
