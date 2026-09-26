@echo off
chcp 65001 >nul
title Clip Studio
cd /d "%~dp0"
set PYTHONUTF8=1
if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
if not exist ".venv\Scripts\python.exe" (
  echo Environnement Python introuvable : lance d'abord Installer.bat
  echo Cherche dans : "%CD%\.venv\Scripts\python.exe"
  pause & exit /b 1
)
echo Ouverture de Clip Studio dans le navigateur...
echo Garde cette fenetre ouverte pendant que tu travailles ; la fermer arrete Clip Studio.
".venv\Scripts\python.exe" -m clip web
pause
