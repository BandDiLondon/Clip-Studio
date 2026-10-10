@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Copie projets\ vers un dossier de sauvegarde (OneDrive par defaut). Ne supprime jamais rien dans la sauvegarde.
rem Exclus car recalculables : rendus .mp4 de build\, images extraites des videos, cartes de profondeur.
rem Langue des messages : CLIP_LANG si defini (fr / en), sinon francais si Windows est en francais, sinon anglais
set "LG=en"
if /i "%CLIP_LANG:~0,2%"=="fr" set "LG=fr"
if not defined CLIP_LANG for /f "usebackq delims=" %%L in (`powershell -NoProfile -Command "(Get-UICulture).TwoLetterISOLanguageName"`) do if /i "%%L"=="fr" set "LG=fr"
if "%LG%"=="fr" (title Sauvegarde des projets Clip Studio) else (title Clip Studio project backup)

set "CONF=projets\.sauvegarde"
set "DEST="
if exist "%CONF%" set /p DEST=<"%CONF%"
if not defined DEST if defined OneDrive set "DEST=%OneDrive%\Sauvegardes\Clip Studio projets"
call :msg "Dossier de sauvegarde :" "Backup folder:"
echo   %DEST%
set "NEW="
if "%LG%"=="fr" (set /p NEW=Entree pour confirmer, ou tape un autre dossier, ex. E:\Sauvegardes : ) else (set /p NEW=Enter to confirm, or type another folder, e.g. E:\Backups: )
if defined NEW set "DEST=%NEW%"
if defined DEST goto dest_ok
call :msg "Aucun dossier choisi." "No folder chosen."
pause
exit /b 1
:dest_ok
> "%CONF%" echo %DEST%

echo.
call :msg "Copie en cours vers :" "Copying to:"
echo   %DEST%
robocopy "projets" "%DEST%" /E /XO /R:1 /W:1 /NP /NFL /NDL /XD video_frames depth /XF *.mp4 .sauvegarde
if not errorlevel 8 goto copie_ok
echo.
call :msg "Erreur pendant la copie : voir ci-dessus." "Error during the copy: see above."
pause
exit /b 1
:copie_ok
rem les videos Flow (videos\*.mp4) ne sont pas recalculables : on les copie a part
for /d %%P in (projets\*) do if exist "%%P\videos" robocopy "%%P\videos" "%DEST%\%%~nxP\videos" *.mp4 *.mov *.webm *.m4v /XO /R:1 /W:1 /NP /NFL /NDL /NJH /NJS >nul
echo.
call :msg "Sauvegarde terminee :" "Backup done:"
echo   %DEST%
call :msg "(les rendus .mp4 de build\ ne sont pas copies : ils se refont avec Rendu final)" "(the .mp4 renders in build\ are not copied: they can be redone with Final render)"
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
