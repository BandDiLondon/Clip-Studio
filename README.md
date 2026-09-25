# Clip Studio

Clip Studio fabrique des clips musicaux illustrés à partir d'une chanson (mp3) et de ses paroles (txt). Tout tourne en local,
sous **Windows** ou **Linux**.

- Chaque vers unique a son image. Les images sont générées par **planches** (6 cases par image générée) pour limiter les générations IA.
- Les paroles s'affichent en **karaoké mot à mot**, grâce à un alignement automatique (Whisper / stable-ts).
- Le montage est calé sur les **beats** détectés.
- Les solos passent en **travelling** sur des photos panoramiques.
- Des **vidéos** de ~10 s (Flow, Veo…) peuvent remplacer n'importe quelle image.
- Une centaine de réglages sont disponibles : caméra, looks, particules, fumée, feu, éclairs, transitions, parallaxe 3D, formats 16:9 / 4K / 9:16 / 1:1…
- Claude (Claude Code, avec un abonnement Claude Pro/Max) peut rédiger, **uniquement quand tu cliques sur un bouton** : descriptions de scènes, évaluation du storyboard, prompts de solos et de vidéos, titre et description YouTube.

## Installation

Télécharger la dernière version dans l'onglet **[Releases](../../releases/latest)** : un zip par système, avec
seulement les fichiers utiles (`…-Windows.zip` ou `…-Linux.zip`). Puis décompresser.
(Autres possibilités : **Code → Download ZIP**, qui contient les deux systèmes, ou `git clone`.)

### Windows 10 / 11
Double-cliquer sur **`Installer.bat`**. Il installe, si besoin, sans droits administrateur ni redémarrage :
- Python 3.12 (python.org) ;
- l'environnement `.venv` et les bibliothèques, aux versions testées ;
- ffmpeg (dans `tools\ffmpeg`) ;
- Real-ESRGAN (dans `tools\realesrgan`).

### Linux (Ubuntu 24.04, Debian et dérivés ; WSL compris)
```
bash installer.sh
```
Il installe au besoin, avec `sudo apt` : `python3-venv`, `ffmpeg`, `curl` et `fonts-liberation`. Puis il crée `.venv` avec
les bibliothèques et télécharge Real-ESRGAN. Sur une autre distribution, installe ces paquets toi-même avant de le lancer.

### Les deux
- Optionnel : [Claude Code](https://claude.com/claude-code) pour les boutons « ✨ … avec Claude ».
- Le premier alignement des paroles télécharge le modèle Whisper « medium » (~1,5 Go, une seule fois). Il lui faut
  environ **5 Go de mémoire vive**.

## Utilisation

- **Windows** : double-clic sur **`Clip Studio.bat`**. Garde la fenêtre noire ouverte pendant que tu travailles.
- **Linux** : `./clip-studio.sh`. Garde le terminal ouvert ; Ctrl+C arrête Clip Studio.

L'interface s'ouvre dans le navigateur (`http://127.0.0.1:8765`).

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

- **Ligne de commande** : `.venv\Scripts\python.exe -m clip --help` (Windows) ou `.venv/bin/python -m clip --help` (Linux).
  Sous Windows, il y a aussi le menu `Clip.bat`.
- **Sauvegarde** : tes projets (mp3, images, vidéos) ne sont pas dans le dépôt. **`Sauvegarder les projets.bat`** (Windows)
  ou `./sauvegarder-projets.sh` (Linux) les copie vers le dossier de ton choix.
- **Tests** : `.venv\Scripts\python.exe -m unittest` (Windows) ou `.venv/bin/python -m unittest` (Linux).

Documentation complète : [METHODE_CREATION_CLIP.md](METHODE_CREATION_CLIP.md).

## Prérequis et différences Windows / Linux

| | Windows | Linux |
|---|---|---|
| Agrandissement ×4 des cases (Real-ESRGAN) | carte graphique Vulkan | carte graphique Vulkan (pilotes Mesa / NVIDIA) ; sinon, découpe sans agrandissement |
| Encodage | GPU AMD (h264_amf) si disponible, sinon libx264 | libx264 |
| Détection de texte dans les cases (OCR) | intégrée à Windows | non disponible (avertissement absent) |
| Boutons « Ouvrir » / « Dossier » | Explorateur | `xdg-open` (ouvre le dossier) |
| Police du karaoké | Arial | Liberation Sans (mêmes dimensions) |

## Licence

Copyright (C) 2026 BandDiLondon

Clip Studio est un logiciel libre. Tu peux le redistribuer et le modifier selon les termes de la
**GNU General Public License version 3** (ou toute version ultérieure), publiée par la Free Software Foundation.
Il est distribué sans aucune garantie. Voir le fichier [LICENSE](LICENSE).

Les outils utilisés (ffmpeg, Real-ESRGAN, Whisper / stable-ts, bibliothèques Python) gardent leur propre licence.
Les projets créés avec Clip Studio (chansons, images, vidéos) appartiennent à leurs auteurs et ne sont pas
couverts par cette licence.
