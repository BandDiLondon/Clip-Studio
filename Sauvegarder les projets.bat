@echo off
chcp 65001 >nul
setlocal
title Sauvegarde des projets Clip Studio
cd /d "%~dp0"
rem Copie projets\ vers un dossier de sauvegarde (OneDrive par défaut). Ne supprime jamais rien dans la sauvegarde.
rem Exclus car recalculables : rendus .mp4 de build\, images extraites des vidéos, cartes de profondeur.

set "CONF=projets\.sauvegarde"
set "DEST="
if exist "%CONF%" set /p DEST=<"%CONF%"
if not defined DEST if defined OneDrive set "DEST=%OneDrive%\Sauvegardes\Clip Studio projets"
echo Dossier de sauvegarde : %DEST%
set "NEW="
set /p NEW=Entree pour confirmer, ou tape un autre dossier (ex. E:\Sauvegardes) :
if defined NEW set "DEST=%NEW%"
if not defined DEST (echo Aucun dossier choisi. & pause & exit /b 1)
> "%CONF%" echo %DEST%

echo.
echo Copie en cours vers %DEST% ...
robocopy "projets" "%DEST%" /E /XO /R:1 /W:1 /NP /NFL /NDL /XD video_frames depth /XF *.mp4 .sauvegarde
if errorlevel 8 (echo. & echo Erreur pendant la copie : voir ci-dessus. & pause & exit /b 1)
rem les vidéos Flow (videos\*.mp4) ne sont pas recalculables : on les copie à part
for /d %%P in (projets\*) do if exist "%%P\videos" robocopy "%%P\videos" "%DEST%\%%~nxP\videos" *.mp4 *.mov *.webm *.m4v /XO /R:1 /W:1 /NP /NFL /NDL /NJH /NJS >nul
echo.
echo Sauvegarde terminee : %DEST%
echo (les rendus .mp4 de build\ ne sont pas copies : ils se refont avec « Rendu final »)
pause
