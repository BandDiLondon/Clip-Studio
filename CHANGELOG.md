# Journal des versions

Les changements de chaque version de Clip Studio. La section d'une version sert aussi de notes à sa Release GitHub.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; numéros de version `majeure.mineure.correctif`.

## [Non publié]

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
