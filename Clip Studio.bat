@echo off
chcp 65001 >nul
setlocal
title Clip Studio
cd /d "%~dp0"
rem Langue des messages : CLIP_LANG si defini (fr / en), sinon francais si Windows est en francais, sinon anglais
set "LG=en"
if /i "%CLIP_LANG:~0,2%"=="fr" set "LG=fr"
if not defined CLIP_LANG for /f "usebackq delims=" %%L in (`powershell -NoProfile -Command "(Get-UICulture).TwoLetterISOLanguageName"`) do if /i "%%L"=="fr" set "LG=fr"
set "CLIP_LANG=%LG%"
set PYTHONUTF8=1
if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"
if exist ".venv\Scripts\python.exe" goto lancer
call :msg "Environnement Python introuvable : lance d'abord Installer.bat" "Python environment not found: run Installer.bat first"
call :msg "Cherche dans :" "Looked in:"
echo   "%CD%\.venv\Scripts\python.exe"
pause
exit /b 1
:lancer
call :msg "Ouverture de Clip Studio dans le navigateur..." "Opening Clip Studio in the browser..."
call :msg "Garde cette fenetre ouverte pendant que tu travailles : la fermer arrete Clip Studio." "Keep this window open while you work: closing it stops Clip Studio."
".venv\Scripts\python.exe" -m clip web
pause
exit /b 0

rem ---------- message dans la langue choisie : call :msg "francais" "English"
:msg
if "%LG%"=="en" goto msg_en
echo(%~1
exit /b 0
:msg_en
echo(%~2
exit /b 0
