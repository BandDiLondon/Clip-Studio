# Journal des versions

**Français** | [English](CHANGELOG.en.md)

Les changements de chaque version de Clip Studio. La section d'une version sert aussi de notes à sa Release GitHub.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/); numéros de version `majeure.mineure.correctif`.

## [Non publié]

### Sécurité
- Interface : les réglages de chemin (audio, paroles, planches, solos, logo) restent dans le dossier du projet, et
  « Ouvrir » n'ouvre que des dossiers et des vidéos (alertes CodeQL).

## [1.6.0] - 2026-10-31

### Ajouté
- **Chanson instrumentale** (étape 1) : sans paroles ni karaoké, des images abstraites qui suivent le rythme. Analyse
  de l'énergie (passages calmes, modérés, intenses, en frise à l'étape 2), des mesures et des pics; coupes toutes les
  2 mesures au calme, à chaque mesure en modéré, tous les 2 beats en intense (réglable), et sur chaque pic marqué.
  24 à 36 images suffisent : celles qui reviennent sont transformées (miroir, rotation, teinte). Claude choisit le
  style d'après la musique et décrit chaque image selon son énergie. Publication avec chapitres d'énergie.
- Option **Effets sur les pics** (étape 6) : zoom, éclair plafonné et décalage RVB sur chaque pic détecté, aussi pour
  les chansons avec paroles.
- Option **Effets au beat selon l'énergie** (étape 6) : gonflement, tremblement de caméra, projecteurs, RVB et glitch
  plus doux dans les passages calmes, plus forts dans les intenses, avec un coup en plus sur chaque pic. Activée
  d'office pour une chanson instrumentale.
- **Égaliseur** (étape 6) : effets qui réagissent au son, bande par bande : graves → zoom et tremblement, médiums →
  lumière et couleurs, aigus → scintillement, chacun avec son curseur. Visualiseur : nouveaux styles **barres miroir**
  et **anneau au centre**, et couleurs par fréquence.

### Sécurité
- Pillow 13.0.0, filelock 4.2.1 et setuptools 84.1.0 : corrigent les failles signalées par GitHub (Dependabot).

## [1.5.1] - 2026-10-16

### Ajouté
- Étape 2, carte **Vérifier le calage** : sections avec leurs temps, vers mal calés signalés (⚠), alerte quand les
  paroles finissent bien avant la fin de l'audio (« C'est normal » pour une outro instrumentale). Outils de correction
  par section : **▶ écouter**, **Recaler** à partir d'une seconde (Whisper réaligne la section seule) et **Décaler**.
  Commande `section`. « Préparer » liste dans son journal les vers encore mal calés.

### Corrigé
- Rendu : les temps impossibles du calage (fin avant début) sont corrigés avant d'écrire le karaoké.

## [1.5.0] - 2026-10-16

### Ajouté
- Publication : options de l'étape 8, enregistrées dans le projet. **Crédits et liens** (paroles, musique,
  interprétation, clip, mention Clip Studio, liens, lien officiel en fan-made) ajoutés tels quels; **rédaction** (ton,
  accroche courte ou normale, emojis, blocs de la description à garder); **miniature** : 3 idées rédigées d'un coup,
  vignette de référence (personnages tels que dans le clip), texte et couleur du bandeau, formats carré et vertical.
  **Profils** réutilisables d'un projet à l'autre (ex. « KPR », « Fan-made »).
- Publication : deux origines **Fan-made** (chanson officielle d'un autre artiste, ou reprise IA de sa chanson) :
  mention « Fan-made » dans le titre et la miniature, description qui déclare n'avoir aucun droit sur la chanson (fan
  qui travaille avec Clip Studio, sans but lucratif, retrait sur demande), droits laissés à l'artiste et rappel du
  Content ID de YouTube.

### Corrigé
- Calage des paroles : un refrain chanté deux fois de suite (souvent avec un solo entre les deux) n'est plus traité
  comme un seul bloc (le second devient « Chorus (bis) »), et une section ratée est d'abord recalée seule entre les
  vers bien calés qui l'entourent. Avant, le dernier refrain après un solo était tassé en une fraction de seconde.

## [1.4.1] - 2026-10-14

### Corrigé
- Calage des paroles : quand l'alignement global rate des vers (plusieurs vers tassés en un instant après une longue
  intro ou un solo), Clip Studio écoute la chanson, repère chaque section et la cale séparément.
- La réparation du calage était appliquée deux fois (affichage du message).

## [1.4.0] - 2026-10-10

### Ajouté
- **Clip Studio en anglais** : interface, messages, installateurs, lanceurs, ligne de commande et documentation en
  français et en anglais. Langue choisie en haut à droite de l'interface (par défaut, celle du navigateur); ailleurs,
  celle du système, ou `CLIP_LANG=fr` / `en`.
- **Langue de la chanson** (étape 1, `"langue"` dans `projet.json`) : calage des paroles par Whisper dans la bonne
  langue, et textes rédigés dans cette langue (descriptions de scènes, prompts d'images, solos, vidéos, évaluation,
  publication YouTube avec chapitres et mention IA). Indépendante de la langue de l'interface. Les projets existants
  restent en français et ne sont pas recalés.
- Effets automatiques (particules, fumée, flammes, éclairs, rayons, mouvement de caméra) : mots-clés anglais en plus des
  mots-clés français dans les descriptions.

### Modifié
- Français de l'interface et de la documentation : typographie québécoise (pas d'espace avant `;` `?` `!`).

## [1.3.9] - 2026-10-10

### Ajouté
- **macOS (expérimental)** : `installer.sh` installe aussi sous macOS (Homebrew : Python 3.12 et ffmpeg; Real-ESRGAN
  universel Intel / puces Apple), lanceur `Clip Studio.command`, police Arial et mémoire disponible sous macOS. Zip
  `…-macOS.zip` dans chaque Release. Validé automatiquement sur les Mac de GitHub, pas encore sur un vrai Mac.
- Essai complet automatique (`scripts/essai_complet.py`) : chanson synthétique → aperçu vidéo contrôlé, lancé sur
  GitHub sous Linux et macOS après `installer.sh`.
- Étape 2 : choix du modèle de calage des paroles. « Précis » (Whisper medium, ~5 Go de mémoire, par défaut) ou
  « Mémoire limitée » (Whisper small, ~2 Go, deux fois plus rapide mais karaoké moins précis). Le choix est gardé dans
  le projet (`whisper`); le changer fait recaler les paroles au prochain « Préparer ». Les projets existants ne sont
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
  refrain); ce couplet est avancé d'un bloc jusqu'au début indiqué.
- « Début du chant » : la réparation automatique ne déplace plus la 1re section calée sur ce début; les vers
  aspirés dans l'intro sont posés à partir de ce début à leur durée naturelle (plus étirés jusqu'au refrain).

## [1.3.3] - 2026-09-25

### Retiré
- Ancien menu console `Clip.bat` (remplacé par Clip Studio; la ligne de commande `python -m clip` reste disponible).
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
  - [docs/GUIDE.md](docs/GUIDE.md) pour l'utilisation (premiers pas, générateurs d'images, conseils, dépannage);
  - [docs/TECHNIQUE.md](docs/TECHNIQUE.md) pour le code (architecture, commandes, `projet.json`, conventions);
  - `AGENTS.md` réécrit pour l'assistant IA de n'importe quel utilisateur.
- README illustré (captures des étapes et image d'un clip); `scripts/captures.py` les régénère.
- Étape Vidéos : `?sel=p1_c3` dans l'adresse présélectionne une image.

### Modifié
- Les notes de chaque Release sont reprises de ce journal.

## [1.0.0] - 2026-09-24

Première version publiée.

### Ajouté
- **Clip Studio**, interface web locale en 8 étapes : Projet, Préparer, Descriptions, Planches, Vidéos, Options,
  Rendu, Publication.
- Calage automatique des paroles mot à mot (Whisper / stable-ts) et du rythme (beats, tempo automatique).
- Planches : 1 image par vers unique, rangées dans le minimum de générations; découpe et agrandissement ×4
  (Real-ESRGAN); retouche d'une seule case; détection du texte parasite (Windows).
- Vidéos (Flow, Veo…) à la place de n'importe quelle image.
- Une centaine de réglages : caméra, parallaxe 3D, looks, particules, fumée, flammes, éclairs, transitions, karaoké,
  formats 16:9 / 4K / 9:16 / 1:1, préréglages.
- Claude Code (abonnement) sur demande : descriptions, évaluation du storyboard, prompts de solos et de vidéos,
  publication YouTube avec chapitres et mention IA.
- Fiabilité : mp3, paroles ou début du chant modifiés détectés et analyses refaites, montage recalculé au besoin,
  historique des réglages, sauvegarde des projets, rendu adapté à la mémoire disponible.
- Windows (`Installer.bat`, sans droits administrateur) et Linux (`installer.sh`); zips séparés dans les Releases.
- 21 tests automatiques.
