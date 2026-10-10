# Journal des versions

Les changements de chaque version de Clip Studio. La section d'une version sert aussi de notes à sa Release GitHub.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; numéros de version `majeure.mineure.correctif`.

## [Non publié]

### Ajouté
- **macOS (expérimental)** : `installer.sh` installe aussi sous macOS (Homebrew : Python 3.12 et ffmpeg ; Real-ESRGAN
  universel Intel / puces Apple), lanceur `Clip Studio.command`, police Arial et mémoire disponible sous macOS. Zip
  `…-macOS.zip` dans chaque Release. Validé automatiquement sur les Mac de GitHub, pas encore sur un vrai Mac.
- Essai complet automatique (`scripts/essai_complet.py`) : chanson synthétique → aperçu vidéo contrôlé, lancé sur
  GitHub sous Linux et macOS après `installer.sh`.
- Étape 2 : choix du modèle de calage des paroles. « Précis » (Whisper medium, ~5 Go de mémoire, par défaut) ou
  « Mémoire limitée » (Whisper small, ~2 Go, deux fois plus rapide mais karaoké moins précis). Le choix est gardé dans
  le projet (`whisper`) ; le changer fait recaler les paroles au prochain « Préparer ». Les projets existants ne sont
  pas recalés.

## [1.3.8] - 2026-10-10

### Corrigé
- `projet.json`, les descriptions, l'alignement des paroles (`words.json`) et la liste d'images sont écrits d'un
  coup (fichier temporaire puis remplacement) : une coupure pendant l'écriture laisse l'ancienne version intacte au
  lieu d'un fichier vide.

### Modifié
- README : précise ce qui tourne en local et ce qui passe par Internet (générateur d'images, Claude).

## [1.3.7] - 2026-10-10

### Sécurité
- `setuptools` 83.0.0 (au lieu de 78.1.0) : corrige deux failles signalées par Dependabot, qui ne touchaient pas
  Clip Studio (fonctions non utilisées).

### Ajouté
- `Installer.bat` s'arrête avec un message clair si le dossier de Clip Studio a un chemin trop long pour Windows
  (plus de 100 caractères, sauf si les chemins longs sont activés), au lieu d'échouer au milieu de l'installation.
- Tests automatiques sous Windows et Linux sur GitHub à chaque envoi et à chaque pull request.

### Corrigé
- Les commandes ne plantent plus quand leur sortie est redirigée vers un fichier sous Windows (caractères comme
  « → » impossibles à écrire en cp1252).

## [1.3.6] - 2026-10-10

### Corrigé
- `Installer.bat` (1.3.5) : l'installation s'arrêtait à l'étape ffmpeg (« ... était inattendu ») quand ffmpeg
  n'était pas déjà installé, à cause de parenthèses dans un message.

## [1.3.5] - 2026-10-10

### Sécurité
- Serveur local : les requêtes venues d'un autre site (en-tête `Host` ou `Origin` étranger) sont refusées. Une page
  web ouverte en même temps ne peut plus piloter Clip Studio.
- Installateurs : chaque fichier téléchargé (Python, ffmpeg, Real-ESRGAN) est vérifié par son empreinte SHA256.

### Modifié
- `Installer.bat` installe ffmpeg 8.0.1 (version testée) au lieu de la dernière version publiée.
- README : les mesures qui limitent l'usage de tokens de Claude sont expliquées, ainsi que le cadre du projet (projet
  personnel, aide apportée au mieux).

## [1.3.4] - 2026-10-10

### Corrigé
- « Début du chant » : s'applique aussi quand l'alignement place le 1er couplet trop tard (tassé contre le
  refrain) ; ce couplet est avancé d'un bloc jusqu'au début indiqué.
- « Début du chant » : la réparation automatique ne déplace plus la 1re section calée sur ce début ; les vers
  aspirés dans l'intro sont posés à partir de ce début à leur durée naturelle (plus étirés jusqu'au refrain).

## [1.3.3] - 2026-09-25

### Retiré
- Ancien menu console `Clip.bat` (remplacé par Clip Studio ; la ligne de commande `python -m clip` reste disponible).
- Dossier `legacy/` (anciens scripts d'avant Clip Studio, plus utilisés).

## [1.3.2] - 2026-09-25

### Ajouté
- README : section « Comment Clip Studio a été fait » (conception humaine, code écrit en grande partie avec Claude).

### Modifié
- Appels à Claude bien moins coûteux en limite d'utilisation : Claude Code est lancé sans outils,
  connecteurs ni réglages (~700 tokens de contexte au lieu de ~34 500 par appel), pour la même réponse.

## [1.3.1] - 2026-09-25

### Ajouté
- Logo de Clip Studio : icône de l'onglet du navigateur (`favicon.ico`) et logo dans l'en-tête de l'interface.

### Corrigé
- `scripts/captures.py` attend que le navigateur ait fini d'écrire chaque capture (échecs aléatoires).

## [1.3.0] - 2026-09-25

### Modifié
- **Détection du texte dans les cases** : RapidOCR remplace l'OCR intégré à Windows, et fonctionne désormais aussi sous
  Linux. Il repère bien mieux le texte dans les images (sur 165 cases : 14 textes réels trouvés au lieu de 3, dont
  t-shirts imprimés, néons et enseignes). Télémétrie d'onnxruntime désactivée.
  **Mise à jour d'une installation existante : relancer `Installer.bat` ou `installer.sh`** (installe RapidOCR).

## [1.2.0] - 2026-09-25

### Corrigé
- **Rendu environ 2× plus rapide** sur les processeurs à nombreux cœurs : chaque processus de rendu lançait autant de
  threads de calcul que de cœurs, et ils se gênaient (1080p : 2 min → 1 min pour une chanson de 3 min, sur 16 cœurs).

### Modifié
- Durées indiquées dans le guide et dans l'interface remplacées par des temps mesurés (nouvelle section
  « Temps de calcul » du guide, PC puissant et PC ordinaire).

## [1.1.0] - 2026-09-25

### Ajouté
- Documentation réorganisée :
  - [docs/GUIDE.md](docs/GUIDE.md) pour l'utilisation (premiers pas, générateurs d'images, conseils, dépannage) ;
  - [docs/TECHNIQUE.md](docs/TECHNIQUE.md) pour le code (architecture, commandes, `projet.json`, conventions) ;
  - `AGENTS.md` réécrit pour l'assistant IA de n'importe quel utilisateur.
- README illustré (captures des étapes et image d'un clip) ; `scripts/captures.py` les régénère.
- Étape Vidéos : `?sel=p1_c3` dans l'adresse présélectionne une image.

### Modifié
- Les notes de chaque Release sont reprises de ce journal.

## [1.0.0] - 2026-09-24

Première version publiée.

### Ajouté
- **Clip Studio**, interface web locale en 8 étapes : Projet, Préparer, Descriptions, Planches, Vidéos, Options,
  Rendu, Publication.
- Calage automatique des paroles mot à mot (Whisper / stable-ts) et du rythme (beats, tempo automatique).
- Planches : 1 image par vers unique, rangées dans le minimum de générations ; découpe et agrandissement ×4
  (Real-ESRGAN) ; retouche d'une seule case ; détection du texte parasite (Windows).
- Vidéos (Flow, Veo…) à la place de n'importe quelle image.
- Une centaine de réglages : caméra, parallaxe 3D, looks, particules, fumée, flammes, éclairs, transitions, karaoké,
  formats 16:9 / 4K / 9:16 / 1:1, préréglages.
- Claude Code (abonnement) sur demande : descriptions, évaluation du storyboard, prompts de solos et de vidéos,
  publication YouTube avec chapitres et mention IA.
- Fiabilité : mp3, paroles ou début du chant modifiés détectés et analyses refaites, montage recalculé au besoin,
  historique des réglages, sauvegarde des projets, rendu adapté à la mémoire disponible.
- Windows (`Installer.bat`, sans droits administrateur) et Linux (`installer.sh`) ; zips séparés dans les Releases.
- 21 tests automatiques.
