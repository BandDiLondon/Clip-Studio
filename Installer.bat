@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Langue des messages : CLIP_LANG si defini (fr / en), sinon francais si Windows est en francais, sinon anglais
set "LG=en"
if /i "%CLIP_LANG:~0,2%"=="fr" set "LG=fr"
if not defined CLIP_LANG for /f "usebackq delims=" %%L in (`powershell -NoProfile -Command "(Get-UICulture).TwoLetterISOLanguageName"`) do if /i "%%L"=="fr" set "LG=fr"
set "CLIP_LANG=%LG%"
if "%LG%"=="fr" (title Installation de Clip Studio) else (title Clip Studio setup)
echo ==============================================
call :msg "  Installation de Clip Studio (Windows 10/11)" "  Clip Studio setup (Windows 10/11)"
echo ==============================================
echo.

rem ---------- Chemin du dossier : Windows limite un chemin a 260 caracteres et les bibliotheques en ajoutent ~150
if "%CD:~100,1%"=="" goto chemin_ok
reg query "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled 2>nul | find "0x1" >nul && goto chemin_ok
call :msg "Le dossier de Clip Studio a un chemin trop long pour Windows :" "The Clip Studio folder has a path too long for Windows:"
echo   %CD%
call :msg "Deplace le dossier Clip-Studio plus pres de la racine, par exemple C:\Clip-Studio, puis relance Installer.bat." "Move the Clip-Studio folder closer to the root, for example C:\Clip-Studio, then run Installer.bat again."
pause
exit /b 1
:chemin_ok

rem ---------- 1. Python 3.12 (installation par utilisateur, sans droits administrateur ni redemarrage)
set "PYLOCAL=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
set "USEPY="
if not exist "%PYLOCAL%" py -3.12 -c "import sys" >nul 2>&1 && set "USEPY=1"
if not exist "%PYLOCAL%" if not defined USEPY (
  call :msg "[1/5] Python 3.12 introuvable : telechargement depuis python.org..." "[1/5] Python 3.12 not found: downloading from python.org..."
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $f=Join-Path $env:TEMP 'python-3.12.10-amd64.exe'; Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $f; if ((Get-FileHash $f -Algorithm SHA256).Hash -ne '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb') { Remove-Item $f; throw 'Fichier corrompu ou modifie / corrupted or modified file (SHA256)' }; Start-Process $f -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_test=0' -Wait; Remove-Item $f"
  if not exist "%PYLOCAL%" (call :msg "Echec de l'installation de Python" "Python installation failed" & pause & exit /b 1)
)
echo [1/5] Python 3.12 : OK

rem ---------- 2. Environnement virtuel + dependances (versions testees)
if not exist ".venv\Scripts\python.exe" (
  call :msg "[2/5] Creation de l'environnement .venv..." "[2/5] Creating the .venv environment..."
  if defined USEPY (py -3.12 -m venv .venv) else ("%PYLOCAL%" -m venv .venv)
)
if not exist ".venv\Scripts\python.exe" (call :msg "Echec de creation du venv" "Failed to create the venv" & pause & exit /b 1)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip
call :msg "[2/5] Installation de torch (CPU)..." "[2/5] Installing torch (CPU)..."
"%PY%" -m pip install torch==2.14.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (call :msg "Echec de torch" "torch failed" & pause & exit /b 1)
call :msg "[2/5] Installation des dependances..." "[2/5] Installing the dependencies..."
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (call :msg "Echec de pip. Essayer : .venv\Scripts\python.exe -m pip install -r requirements-complet.txt" "pip failed. Try: .venv\Scripts\python.exe -m pip install -r requirements-complet.txt" & pause & exit /b 1)
rem RapidOCR sans ses dependances : il exige opencv-python, en conflit avec opencv-python-headless
"%PY%" -m pip install --no-deps rapidocr==3.9.2

rem ---------- 3. ffmpeg (dans tools\ffmpeg s'il n'est pas dans le PATH)
set "FFOK="
where ffmpeg >nul 2>&1 && set "FFOK=1"
if exist "tools\ffmpeg\bin\ffmpeg.exe" set "FFOK=1"
if not defined FFOK (
  call :msg "[3/5] ffmpeg introuvable : telechargement de ffmpeg 8.0.1 depuis gyan.dev..." "[3/5] ffmpeg not found: downloading ffmpeg 8.0.1 from gyan.dev..."
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $z=Join-Path $env:TEMP 'ffmpeg.zip'; $t=Join-Path $env:TEMP 'ffmpeg_x'; Invoke-WebRequest 'https://github.com/GyanD/codexffmpeg/releases/download/8.0.1/ffmpeg-8.0.1-essentials_build.zip' -OutFile $z; if ((Get-FileHash $z -Algorithm SHA256).Hash -ne 'e2aaeaa0fdbc397d4794828086424d4aaa2102cef1fb6874f6ffd29c0b88b673') { Remove-Item $z; throw 'Fichier corrompu ou modifie / corrupted or modified file (SHA256)' }; if (Test-Path $t) { Remove-Item $t -Recurse -Force }; Expand-Archive $z -DestinationPath $t; $b=(Get-ChildItem $t -Recurse -Filter ffmpeg.exe | Select-Object -First 1).DirectoryName; New-Item -ItemType Directory -Force 'tools\ffmpeg\bin' | Out-Null; Copy-Item (Join-Path $b '*') 'tools\ffmpeg\bin' -Force; Remove-Item $z, $t -Recurse -Force"
  if not exist "tools\ffmpeg\bin\ffmpeg.exe" (call :msg "Echec du telechargement de ffmpeg" "ffmpeg download failed" & pause & exit /b 1)
)
if exist "tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%CD%\tools\ffmpeg\bin;%PATH%"
echo [3/5] ffmpeg : OK

rem ---------- 4. Real-ESRGAN (agrandissement des cases)
if not exist "tools\realesrgan\realesrgan-ncnn-vulkan.exe" (
  call :msg "[4/5] Telechargement de Real-ESRGAN..." "[4/5] Downloading Real-ESRGAN..."
  powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $z=Join-Path $env:TEMP 'realesrgan.zip'; Invoke-WebRequest 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip' -OutFile $z; if ((Get-FileHash $z -Algorithm SHA256).Hash -ne 'abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d') { Remove-Item $z; throw 'Fichier corrompu ou modifie / corrupted or modified file (SHA256)' }; Expand-Archive $z -DestinationPath 'tools\realesrgan' -Force; Remove-Item $z"
  if not exist "tools\realesrgan\realesrgan-ncnn-vulkan.exe" (call :msg "Echec du telechargement de Real-ESRGAN" "Real-ESRGAN download failed" & pause & exit /b 1)
)
echo [4/5] Real-ESRGAN : OK

rem ---------- 5. Verification
echo.
call :msg "[5/5] Verification :" "[5/5] Check:"
set PYTHONUTF8=1
"%PY%" -m clip check
echo.
call :msg "Optionnel : Claude Code (abonnement Claude Pro/Max) pour les boutons avec Claude :" "Optional: Claude Code (Claude Pro/Max subscription) for the with Claude buttons:"
call :msg "  https://claude.com/claude-code  (ou l'extension Claude Code de VS Code)" "  https://claude.com/claude-code  (or the Claude Code extension for VS Code)"
echo.
call :msg "Pour commencer : double-clic sur Clip Studio.bat" "To start: double-click Clip Studio.bat"
pause
exit /b 0

rem ---------- message dans la langue choisie : call :msg "francais" "English" (hors de tout bloc, parentheses permises)
:msg
if "%LG%"=="en" goto msg_en
echo(%~1
exit /b 0
:msg_en
echo(%~2
exit /b 0
