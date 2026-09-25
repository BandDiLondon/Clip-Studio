@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set PYTHONUTF8=1
cd /d "%ROOT%"
if not exist "%PY%" (
  echo Environnement Python introuvable : %PY%
  pause & exit /b 1
)

:choisir
cls
echo ==============================================
echo   CLIP - choix du projet
echo ==============================================
set i=0
for /f "delims=" %%P in ('"%PY%" -m clip list') do (
  set /a i+=1
  set "P!i!=%%P"
  echo   !i!. %%P
)
echo.
echo   N. Nouveau projet
echo   Q. Quitter
echo.
set "c="
set /p "c=Choix : "
if /i "%c%"=="q" exit /b 0
if /i "%c%"=="n" goto nouveau
if defined P%c% (
  set "NOM=!P%c%!"
  goto menu
)
goto choisir

:nouveau
set "NOM="
set /p "NOM=Nom du projet (sans espaces) : "
if "%NOM%"=="" goto choisir
"%PY%" -m clip new "%NOM%"
if errorlevel 1 ( pause & goto choisir )
start "" "%ROOT%projets\%NOM%"
echo.
echo Depose la chanson (.mp3) et les paroles (.txt) dans le dossier qui vient de s'ouvrir,
echo et les photos de solo (solo1.png...) dans solos\ si tu en as.
pause
goto menu

:menu
set "PR=%ROOT%projets\%NOM%"
cls
echo ==============================================
echo   CLIP - projet : %NOM%
echo ==============================================
echo   1. Preparer      beats + paroles + prompts
echo   2. Ouvrir les prompts (ou la liste a decrire)
echo   3. Verifier les planches
echo   4. Apercu rapide verif + decoupe + plan + apercu 960x540
echo   5. Rendu final   verif + decoupe + plan + video 1080p
echo   6. Rendu seul    apres modification de projet.json
echo   7. Ouvrir le dossier du projet
echo   8. Changer de projet
echo   Q. Quitter
echo.
set "c="
set /p "c=Choix : "
if /i "%c%"=="q" exit /b 0
if "%c%"=="1" goto preparer
if "%c%"=="2" goto prompts
if "%c%"=="3" goto verifier
if "%c%"=="4" ( set "CMD=build-preview" & set "OUT=preview.mp4" & goto construire )
if "%c%"=="5" ( set "CMD=build" & set "OUT=%NOM%.mp4" & goto construire )
if "%c%"=="6" goto rendu
if "%c%"=="7" ( start "" "%PR%" & goto menu )
if "%c%"=="8" goto choisir
goto menu

:preparer
"%PY%" -m clip prepare "%NOM%"
if errorlevel 1 ( pause & goto menu )
call :ouvrir_prompts
pause
goto menu

:prompts
call :ouvrir_prompts
goto menu

:ouvrir_prompts
if exist "%PR%\build\a_decrire.md" (
  echo.
  echo Colle le contenu de a_decrire.md a Claude, enregistre sa reponse dans
  echo build\descriptions.json, puis relance "1. Preparer".
  start "" notepad "%PR%\build\a_decrire.md"
) else if exist "%PR%\build\prompts_planches.md" (
  echo.
  echo Genere chaque planche avec son prompt, enregistre-les en P1.png, P2.png...
  echo dans le dossier des planches, puis "4. Apercu rapide".
  start "" notepad "%PR%\build\prompts_planches.md"
) else (
  echo Aucun prompt : lancer d'abord "1. Preparer".
  pause
)
exit /b 0

:verifier
"%PY%" -m clip verify "%NOM%"
pause
goto menu

:construire
"%PY%" -m clip %CMD% "%NOM%"
if errorlevel 1 (
  echo.
  set "o="
  set /p "o=Continuer malgre les avertissements sur les planches ? (O/N) : "
  if /i "!o!"=="o" (
    "%PY%" -m clip %CMD% "%NOM%" --force
    if errorlevel 1 ( pause & goto menu )
  ) else (
    goto menu
  )
)
start "" "%PR%\build\planche_contact.jpg"
start "" "%PR%\build\%OUT%"
pause
goto menu

:rendu
"%PY%" -m clip render "%NOM%"
if errorlevel 1 ( pause & goto menu )
start "" "%PR%\build\%NOM%.mp4"
pause
goto menu
