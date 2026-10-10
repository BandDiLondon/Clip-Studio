@echo off
chcp 65001 >nul
setlocal
title Installation de Clip Studio
cd /d "%~dp0"
echo ==============================================
echo   Installation de Clip Studio (Windows 10/11)
echo ==============================================
echo.

rem ---------- Chemin du dossier : Windows limite un chemin a 260 caracteres et les bibliotheques en ajoutent ~150
if "%CD:~100,1%"=="" goto chemin_ok
reg query "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled 2>nul | find "0x1" >nul && goto chemin_ok
echo Le dossier de Clip Studio a un chemin trop long pour Windows :
echo   %CD%
echo Deplace le dossier Clip-Studio plus pres de la racine, par exemple C:\Clip-Studio, puis relance Installer.bat.
pause
exit /b 1
:chemin_ok

rem ---------- 1. Python 3.12 (installation par utilisateur, sans droits administrateur ni redemarrage)
set "PYLOCAL=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
set "USEPY="
if not exist "%PYLOCAL%" py -3.12 -c "import sys" >nul 2>&1 && set "USEPY=1"
if not exist "%PYLOCAL%" if not defined USEPY (
  echo [1/5] Python 3.12 introuvable : telechargement depuis python.org...
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $f=Join-Path $env:TEMP 'python-3.12.10-amd64.exe'; Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $f; if ((Get-FileHash $f -Algorithm SHA256).Hash -ne '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb') { Remove-Item $f; throw 'Fichier telecharge corrompu ou modifie (empreinte SHA256 incorrecte)' }; Start-Process $f -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_test=0' -Wait; Remove-Item $f"
  if not exist "%PYLOCAL%" (echo Echec de l'installation de Python & pause & exit /b 1)
)
echo [1/5] Python 3.12 : OK

rem ---------- 2. Environnement virtuel + dépendances (versions testées)
if not exist ".venv\Scripts\python.exe" (
  echo [2/5] Creation de l'environnement .venv...
  if defined USEPY (py -3.12 -m venv .venv) else ("%PYLOCAL%" -m venv .venv)
)
if not exist ".venv\Scripts\python.exe" (echo Echec de creation du venv & pause & exit /b 1)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip
echo [2/5] Installation de torch (CPU)...
"%PY%" -m pip install torch==2.14.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (echo Echec torch & pause & exit /b 1)
echo [2/5] Installation des dependances...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (echo Echec pip. Essayer : .venv\Scripts\python.exe -m pip install -r requirements-complet.txt & pause & exit /b 1)
rem RapidOCR sans ses dependances : il exige opencv-python, en conflit avec opencv-python-headless
"%PY%" -m pip install --no-deps rapidocr==3.9.2

rem ---------- 3. ffmpeg (dans tools\ffmpeg s'il n'est pas dans le PATH)
set "FFOK="
where ffmpeg >nul 2>&1 && set "FFOK=1"
if exist "tools\ffmpeg\bin\ffmpeg.exe" set "FFOK=1"
if not defined FFOK (
  echo [3/5] ffmpeg introuvable : telechargement de ffmpeg 8.0.1 depuis gyan.dev...
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $z=Join-Path $env:TEMP 'ffmpeg.zip'; $t=Join-Path $env:TEMP 'ffmpeg_x'; Invoke-WebRequest 'https://github.com/GyanD/codexffmpeg/releases/download/8.0.1/ffmpeg-8.0.1-essentials_build.zip' -OutFile $z; if ((Get-FileHash $z -Algorithm SHA256).Hash -ne 'e2aaeaa0fdbc397d4794828086424d4aaa2102cef1fb6874f6ffd29c0b88b673') { Remove-Item $z; throw 'Fichier telecharge corrompu ou modifie (empreinte SHA256 incorrecte)' }; if (Test-Path $t) { Remove-Item $t -Recurse -Force }; Expand-Archive $z -DestinationPath $t; $b=(Get-ChildItem $t -Recurse -Filter ffmpeg.exe | Select-Object -First 1).DirectoryName; New-Item -ItemType Directory -Force 'tools\ffmpeg\bin' | Out-Null; Copy-Item (Join-Path $b '*') 'tools\ffmpeg\bin' -Force; Remove-Item $z, $t -Recurse -Force"
  if not exist "tools\ffmpeg\bin\ffmpeg.exe" (echo Echec du telechargement de ffmpeg & pause & exit /b 1)
)
if exist "tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%CD%\tools\ffmpeg\bin;%PATH%"
echo [3/5] ffmpeg : OK

rem ---------- 4. Real-ESRGAN (agrandissement des cases)
if not exist "tools\realesrgan\realesrgan-ncnn-vulkan.exe" (
  echo [4/5] Telechargement de Real-ESRGAN...
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $z=Join-Path $env:TEMP 'realesrgan.zip'; Invoke-WebRequest 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip' -OutFile $z; if ((Get-FileHash $z -Algorithm SHA256).Hash -ne 'abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d') { Remove-Item $z; throw 'Fichier telecharge corrompu ou modifie (empreinte SHA256 incorrecte)' }; Expand-Archive $z -DestinationPath 'tools\realesrgan' -Force; Remove-Item $z"
  if not exist "tools\realesrgan\realesrgan-ncnn-vulkan.exe" (echo Echec du telechargement de Real-ESRGAN & pause & exit /b 1)
)
echo [4/5] Real-ESRGAN : OK

rem ---------- 5. Vérification
echo.
echo [5/5] Verification :
set PYTHONUTF8=1
"%PY%" -m clip check
echo.
echo Optionnel : Claude Code (abonnement Claude Pro/Max) pour les boutons "avec Claude" :
echo   https://claude.com/claude-code  (ou l'extension Claude Code de VS Code)
echo.
echo Pour commencer : double-clic sur "Clip Studio.bat".
pause
