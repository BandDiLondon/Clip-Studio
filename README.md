# Clip Studio

Clip Studio fabrique des clips musicaux illustrés à partir d'une chanson (mp3) et de ses paroles (txt). Tout tourne en local sur Windows.

- Chaque vers unique a son image. Les images sont générées par **planches** (6 cases par image générée) pour limiter les générations IA.
- Les paroles s'affichent en **karaoké mot à mot**, grâce à un alignement automatique (Whisper / stable-ts).
- Le montage est calé sur les **beats** détectés.
- Les solos passent en **travelling** sur des photos panoramiques.
- Des **vidéos** de ~10 s (Flow, Veo…) peuvent remplacer n'importe quelle image.
- Une centaine de réglages sont disponibles : caméra, looks, particules, fumée, feu, éclairs, transitions, parallaxe 3D, formats 16:9 / 4K / 9:16 / 1:1…
- Claude (Claude Code, avec un abonnement Claude Pro/Max) peut rédiger, **uniquement quand tu cliques sur un bouton** : descriptions de scènes, évaluation du storyboard, prompts de solos et de vidéos, titre et description YouTube.

## Installation

1. Télécharger le dépôt : **Code → Download ZIP**, puis décompresser. Tu peux aussi faire `git clone`.
2. Double-cliquer sur **`Installer.bat`**. Il installe, si besoin, sans droits administrateur ni redémarrage :
   - Python 3.12 (python.org) ;
   - l'environnement `.venv` et les bibliothèques, aux versions testées ;
   - ffmpeg (dans `toolsfmpeg`) ;
   - Real-ESRGAN (dans `toolsealesrgan`).
3. Optionnel : installer [Claude Code](https://claude.com/claude-code) pour les boutons « ✨ … avec Claude ».

Le premier alignement des paroles télécharge le modèle Whisper « medium » (~1,5 Go, une seule fois).

## Utilisation

Double-clic sur **`Clip Studio.bat`** : l'interface s'ouvre dans le navigateur (`http://127.0.0.1:8765`). Garde la fenêtre noire ouverte pendant que tu travailles.

Étapes :
1. Projet
2. Préparer
3. Descriptions
4. Planches
5. Vidéos
6. Options
7. Rendu
8. Publication

Chaque projet vit dans `projets/<nom>/`. Ce dossier n'est pas versionné.

En mode texte, il y a `Clip.bat`, ou `.venv\Scripts\python.exe -m clip --help`.

Tes projets (mp3, images, vidéos) ne sont pas dans le dépôt : **`Sauvegarder les projets.bat`** les copie vers OneDrive
ou vers le dossier de ton choix.

Tests : `.venv\Scripts\python.exe -m unittest`.

Documentation complète : [METHODE_CREATION_CLIP.md](METHODE_CREATION_CLIP.md).

## Prérequis

- Windows 10 ou 11.
- Carte graphique compatible Vulkan, pour Real-ESRGAN.
- Encodage GPU AMD (h264_amf) si disponible, sinon libx264.

## Licence

Copyright (C) 2026 BandDiLondon

Clip Studio est un logiciel libre. Tu peux le redistribuer et le modifier selon les termes de la
**GNU General Public License version 3** (ou toute version ultérieure), publiée par la Free Software Foundation.
Il est distribué sans aucune garantie. Voir le fichier [LICENSE](LICENSE).

Les outils utilisés (ffmpeg, Real-ESRGAN, Whisper / stable-ts, bibliothèques Python) gardent leur propre licence.
Les projets créés avec Clip Studio (chansons, images, vidéos) appartiennent à leurs auteurs et ne sont pas
couverts par cette licence.
