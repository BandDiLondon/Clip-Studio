# MÉTHODE DE CRÉATION DE CLIP — Runbook
Chansons traitées : Paye le Super, Mafia du fromage, Quatre ans au même endroit (ancienne méthode), puis dans
Clip Studio : aveuglement, Star, Henry, J_ai_chier_sul_bord, Rouge_ecarlate, Ca_se_fais_tu_des_pogos.
Environnement et standards : [AGENTS.md](AGENTS.md). Avancement : [PLAN_AMELIORATION.md](PLAN_AMELIORATION.md).

Résultat visé : chaque vers illustré LITTÉRALEMENT par une image, karaoké mot à mot, montage calé sur
les beats, travelling sur des photos panoramiques pendant les solos, effets au choix, audio muxé.

---

## 0. Installation et lancement
- Nouveau PC : double-clic sur **`Installer.bat`** (copie GitHub), sans droits administrateur, winget ni redémarrage.
  Au besoin, il installe :
  - Python 3.12 (python.org, par utilisateur) ;
  - `.venv` avec torch CPU et `requirements.txt` (versions figées ; `requirements-complet.txt` = environnement complet testé) ;
  - ffmpeg (gyan.dev → `tools/ffmpeg/bin`, ajouté au PATH par les `.bat`) ;
  - Real-ESRGAN (`tools/realesrgan/`).
  Puis il lance `python -m clip check`.
  Test sur un Windows vierge : `Tester dans Windows Sandbox.wsb` (copie GitHub, non publié).
- **Linux** (Ubuntu 24.04, Debian et dérivés, WSL compris) : `bash installer.sh` (paquets `python3-venv`, `ffmpeg`, `curl`,
  `fonts-liberation` via `sudo apt`, puis `.venv` et Real-ESRGAN Linux). Ensuite `./clip-studio.sh` et
  `./sauvegarder-projets.sh`. Différences :
  - pas d'OCR (l'avertissement de texte parasite est absent) ;
  - encodage libx264 ;
  - karaoké en Liberation Sans (mêmes dimensions qu'Arial) ;
  - les boutons Ouvrir / Dossier passent par `xdg-open`.
  Validé dans un conteneur Docker `ubuntu:24.04` vierge : installation, tests, découpe, aperçu avec karaoké.
  Test : conteneur Docker `ubuntu:24.04` (le WSL de ce PC n'a pas de réseau et il est limité à 2 Go de mémoire par
  `.wslconfig`, alors que Whisper medium en demande environ 5).
- **`Clip Studio.bat`** ouvre l'interface web locale (`http://127.0.0.1:8765`, 127.0.0.1 uniquement ; garder la fenêtre
  noire ouverte). `Clip.bat` = menu texte, `python -m clip <commande>` = ligne de commande (§2).
- Claude (optionnel) = **Claude Code + abonnement Claude Pro/Max**, sans API (`clip/ai.py`). Il est cherché dans le PATH,
  dans l'installation autonome ou dans l'extension VS Code, et lancé depuis un dossier temporaire : il ne lit pas le projet.
  **Claude n'est appelé que sur clic d'un bouton** (sauf l'évaluation, lancée par « Préparer »). Sans Claude,
  le copier-coller reste possible (`build/a_decrire.md` → `build/descriptions.json`).
- Modèles téléchargés une seule fois : Whisper « medium » (~1,5 Go, `~/.cache/whisper`), Depth Anything V2 Small
  (parallaxe / profondeur, `~/.cache/huggingface`).
- Bandeau « mise à jour » dans Clip Studio : le serveur tourne sur un code périmé → fermer la fenêtre noire et relancer.
  Relancer `Clip Studio.bat` pendant qu'il tourne ouvre simplement la page (avec un avertissement si le code est périmé).
  Si le port 8765 est pris par un autre programme, Clip Studio prend le suivant (jusqu'à 8774).
- **Sauvegarde des projets** : `Sauvegarder les projets.bat`. Il copie `projets/` vers OneDrive
  (`Sauvegardes\Clip Studio projets`) ou vers un autre dossier (retenu dans `projets/.sauvegarde`). Il ne supprime jamais
  rien dans la sauvegarde et laisse de côté ce qui se recalcule (rendus .mp4 de `build/`, `video_frames`, `depth`) ;
  les vidéos Flow de `videos/` sont copiées.
- **Historique** : chaque modification de `projet.json` garde l'ancienne version dans `build/historique/` (30 max, au plus une
  par minute). Restauration : étape 1, « 🕘 Historique des réglages ».

## 1. Clip Studio, étape par étape
### 1. Projet
Nom du projet (lettres, chiffres, `-`, `_`) → `projets/<nom>/`. Déposer le **mp3** et les **paroles** (fichier .txt ou
texte collé). Paroles : texte exact, un vers par ligne, ligne vide entre les blocs ; en-têtes `[Verse 1]`, `[Chorus]`
facultatifs. Sans en-tête, un bloc répété à l'identique devient un refrain.
Titre, artiste et logo servent au titre d'ouverture, au générique et à la publication.

### 2. Préparer
- **Intention de la chanson** (`"intention"`, 1500 car. max) : sens, degré (ironie, hommage…), contexte, époque,
  références, choses à éviter. Transmise à Claude (évaluation, descriptions, solos, vidéos, publication), jamais au
  générateur d'images, qui ne reçoit que **`"style"`** (modifiable au même endroit).
- **Préparer** (`clip prepare`) enchaîne :
  1. les beats → `build/beats.npy` (tempo estimé automatiquement, `bpm_detecte`) ;
  2. l'alignement mot à mot → `build/words.json` ;
  3. l'évaluation par Claude ;
  4. la shotlist et les prompts.
  Beats et alignement sont refaits s'ils manquent, avec « Refaire » (`--force`), ou **automatiquement si le mp3, les
  paroles, le tempo imposé ou le début du chant ont changé** (empreintes `beats_sig` / `paroles_sig` dans projet.json ;
  les paroles sont comparées par contenu, donc recoller le même texte ne déclenche rien). Clip Studio l'affiche
  (« ⚠ Le mp3 a changé… »), et tout rendu refait ces analyses avant de monter.
- **Début du chant** (`"debut_chant"`, s) : si le karaoké démarre trop tôt, les vers placés avant ce temps sont recalés
  (appliqué avant la réparation automatique). Le bouton recale aussitôt (`align --repair-only`), sans refaire l'alignement.
- **Évaluation par Claude** (`clip evaluate`) : le code mesure les passages sans paroles, le temps d'écran des images
  et les cases libres. Claude recommande le nombre TOTAL d'images d'ambiance (une idée de scène par image) et un
  préréglage. La recommandation est appliquée d'office tant qu'aucune planche n'est générée. Sinon, bouton « Appliquer »
  (`evaluate --appliquer`) : les planches existantes restent identiques si la dernière était pleine, et seules les
  nouvelles sont à générer.
- **Photos de solo** : « ✨ Créer les prompts avec Claude » (`clip solos --nombre N`) → prompts panoramiques
  21:9 pensés pour le travelling, dans `build/prompts_solos.md`. Un emplacement par photo (`solo1`, `solo2`…), dépôt ou Ctrl+V.

### 3. Descriptions
Une description par image, format **Plan ; Sujet ; Action ; Décor ; Lumière**. Bouton « ✨ Rédiger avec Claude »
(`clip describe`), ↻ par image (`--ids p1_c2 --consigne "…"`), `--tout` pour tout réécrire.
Stockées dans `build/descriptions.json`. `"descriptions"` de projet.json est prioritaire.

### 4. Planches
Copier le prompt de chaque planche, générer (**nouvelle génération vierge**, format indiqué), déposer P1…Pn
(glisser-déposer, 📋 Coller, ou Ctrl+V sur la planche survolée). Ensuite :
- **Vérifier** (`clip verify`) : format, grille et taille contrôlés. Un ratio de vignette à plus de 25 % du 16:9 bloque ;
  entre 8 et 25 %, simple note.
- **Découper** (`clip cut`) : cases dans `cases/pN_cK.png` (×4 Real-ESRGAN), planche-contact
  `build/planche_contact.jpg`, cases obsolètes supprimées. Fait aussi automatiquement au rendu. Sans carte graphique
  Vulkan (ou sans Real-ESRGAN), agrandissement classique (Lanczos), moins net, avec un avertissement : jamais de blocage.
- **Texte parasite** : après la découpe, l'OCR intégré à Windows (`clip/ocr.ps1`, sans installation) lit chaque case.
  Les légendes, enseignes ou numéros lisibles sont signalés à l'étape 4 et dans `build/texte_detecte.json` → retoucher la case.
  C'est un avertissement, jamais un blocage ; les bribes de moins de 3 lettres sont ignorées.
- « ✨ Refaire avec Claude » : réécrit les descriptions d'une planche (il faudra la régénérer).
- **Retoucher une case** : image 16:9 seule déposée dans `retouches/p1_c2.png`. Elle remplace la case au
  prochain rendu, sans refaire la planche.

### 5. Vidéos (optionnel)
`videos/<id>.mp4` (ex. `solo1.mp4`, `p4_c4.mp4`) **remplace l'image `<id>`** au montage, partout où elle apparaît ;
effets et karaoké restent par-dessus. Si le plan est plus long que la vidéo, elle est étirée ; les images de la
vidéo sont extraites une fois dans `build/video_frames/`.
Galerie de toutes les images → clic sur une image → « ✨ Écrire le prompt vidéo avec Claude » (cette image seule,
`clip videos --ids p1_c2`), copier le prompt, dans Flow : « Images vers vidéo », 16:9, image de départ = l'image,
puis déposer la vidéo ou la retirer.
Les prompts vidéo ne sont **jamais créés automatiquement**. `clip videos --nombre N` : Claude choisit les images
qui restent le plus longtemps à l'écran (nécessite un aperçu ou un rendu). Résultat : `build/videos.json`,
`build/prompts_videos.md`.

### 6. Options
Préréglages 🎻 Ballade / 🎸 Rock / 📼 VHS rétro / ▫️ Sobre, puis ~90 réglages en 11 groupes (détail §4).

### 7. Rendu
- **Aperçu rapide** (`clip build-preview`, 960×540 à 15 fps) et **Rendu final** (`clip build`, 1080p30) :
  vérification, découpe, plan, puis rendu.
- **Aperçu d'un passage** (`clip preview --start s --duration s`) et **Variante** sous un autre nom
  (`clip render --out nom.mp4`) : rendu seul.
- Le **montage** (`"timeline"`) est **recalculé automatiquement** à chaque rendu si le mp3, `words.json`,
  `beats.npy`, la shotlist, les solos ou les images d'intro / d'outro ont changé (empreinte `"timeline_sig"`).
- Liste des vidéos : ▶ lecteur intégré, 📂 Ouvrir, Dossier, 🗑 Supprimer (fichiers de `build/` seulement).

### 8. Publication
`clip publish [--consigne]` → `build/publication.md` : titre, description YouTube, hashtags, 2 prompts de miniature
(avec et sans texte). Claude rédige, et le code ajoute :
- les chapitres (depuis `words.json`, ≥ 10 s, jamais au milieu d'une section) ;
- les paroles telles quelles ;
- la mention IA selon `"origine"` : `suno` (composition originale, interprétation Suno, images IA) | `images` | `complete`.
Groupe **KPR** : compositions originales (paroles et musique sans IA), réinterprétées par Suno → mention « VERSION IA » obligatoire.

---

## 2. Commandes (`python -m clip <commande> <nom>`)
| Commande | Rôle | Sortie |
|---|---|---|
| `check` | vérifie l'environnement | — |
| `web` / `list` / `new` | Clip Studio / liste / nouveau projet | `projets/<nom>/` |
| `prepare [--force]` | beats + alignement + évaluation + prompts | `build/` |
| `beats` | beats et tempo | `build/beats.npy` |
| `align [--repair-only]` | alignement stable-ts + réparation | `build/words.json` |
| `evaluate [--appliquer]` | évaluation du storyboard (Claude) | `build/evaluation.json` |
| `prompts` | shotlist + prompts de planches | `build/shotlist.json`, `prompts_planches.md` |
| `describe [--ids --consigne --tout]` | descriptions (Claude) | `build/descriptions.json` |
| `solos [--nombre --consigne]` | prompts de photos de solo (Claude) | `build/solos.json`, `prompts_solos.md` |
| `videos [--ids / --nombre, --consigne]` | prompts vidéo, à la demande (Claude) | `build/videos.json`, `prompts_videos.md` |
| `verify` / `cut [--scale 1]` | contrôle / découpe + upscale | `cases/`, `build/planche_contact.jpg` |
| `plan [--force]` | montage | `projet.json` → `"timeline"` |
| `preview [--start --duration]` / `render [--out]` | aperçu / rendu seul | `build/preview.mp4`, `build/<nom>.mp4` |
| `build-preview` / `build [--force]` | vérif + découpe + plan + aperçu / rendu | idem |
| `publish [--consigne]` | publication YouTube (Claude) | `build/publication.md` |

## 3. Storyboard — planches = économie de générations
⚠️ **RÈGLE D'OR** : les planches servent à **limiter le nombre de générations d'images**. On calcule le nombre
exact d'images requis par le texte, puis on les range dans le minimum de planches. On ne génère jamais une grande
image unique pour la découper ensuite (approche refusée).

- **1 image par vers unique.** Un vers répété (à la casse, aux accents et à la ponctuation près) réutilise la même image
  (`"dedupe": false` pour désactiver). S'ajoutent les images d'**ambiance** (`"ambiance": N`, nombre TOTAL), et les
  cases libres de la dernière planche deviennent aussi de l'ambiance.
- **Rangement** : planches de 6 (grille 2×3, image **32:27**, 2048×1728). La dernière planche prend la plus petite grille
  suffisante : 4 → 2×2 en 16:9, 2 → 1×2 en 8:9, 1 → image 16:9 seule. Vignettes toujours **16:9**.
- Ids `p1_c1 … pN_cK` (rangée 1 de gauche à droite, puis rangée 2…). Table vignette ↔ vers dans `build/shotlist.json`.
- Passages sans paroles : **photos de solo et images d'ambiance alternent** (répartition régulière, en commençant par un
  solo). Avec assez de photos de solo, 0 image d'ambiance suffit. `"intro_image"` / `"outro_image"` imposent une image fixe.

### Prompt de planche (`clip/prompts.py`)
- En-tête : « Une seule image composée de EXACTEMENT N photographies de cinéma… AUCUNE légende… ». Pas le mot
  « storyboard » (un storyboard a des légendes, que le générateur écrit alors).
- Chaque case = « Photo i (position) : … ». La description est convertie en phrase **sans les étiquettes** Plan/Sujet/…,
  qui finiraient écrites en légende.
- Le quart inférieur de chaque vignette reste libre (zone des paroles). Pied de prompt et négatif : texte, légende,
  sous-titre, numéros, enseigne lisible, vignettes carrées ou verticales, vignette supplémentaire.
- Descriptions : **Action** = illustration LITTÉRALE du vers, une seule action lisible. Plans larges de préférence.
  Personnages récurrents décrits une fois (`"personnages"`) et nommés à l'identique. **Jamais les paroles dans le
  prompt.** Éviter documents, écrans, pancartes (faux texte).
- Vérifier chaque planche : bon nombre de vignettes, aucun texte, chaque case = son vers.

## 4. Réglages (`projet.json`, étape 6)
Conservés d'un rendu à l'autre ; tous les effets sont désactivés par défaut.
- **Cadrage** : `"fit"` (`cover` plein cadre | `contain` sur fond flou), `"cy"` (ancrage vertical : 0 = haut, 1 = bas).
  Par image : `"ajustements": {"p1_c2": {"cy": 0.1, "fit": "contain", "camera": "…", "particules": "…", "fumee": "…",
  "parallaxe": false}}`.
- **Rythme** : `pulse` (0 = rien au beat), `pulse_mesure` (1er temps seulement), `fondu` (durée des transitions),
  `transition` (fondu | coupe | noir | flash | glissement | zoom), `duree_max_image`, `bpm_hint` (`"auto"` ou BPM imposé).
- **Caméra** : `camera` (`zoom` | `auto` = selon le « Plan » : large → travelling, gros plan → zoom avant, moyen →
  zoom arrière), `camera_intensite`, `parallaxe` (true ou amplitude, caméra 3D selon la profondeur `build/depth/`).
- **Look** : `look` (aucun | cinema | nb | sepia | vhs | neon | froid), `grain`, `vignettage`, `luminosite`, `contraste`,
  `letterbox` (2,39:1), `harmonisation`, `variantes` (image répétée : sens et miroir alternés, dernière en N&B),
  `look_sections` (refrain lumineux, couplets sombres, pont désaturé).
- **Atmosphère** : `particules` (auto | neige | poussiere | braises | pluie | confettis | bokeh | etincelles),
  `particules_densite`, `particules_sections` ({"refrain": "braises"}), `fumee` (auto | fumee | brouillard) +
  `fumee_densite`, `flammes` (auto | partout) + `flammes_hauteur` / `flammes_intensite`, `eclairs`, `rayons` +
  `rayons_intensite`, `flou_fond`, `brume_profondeur`. « auto » = selon les mots de la description.
  Les effets s'appliquent aussi aux travellings et aux vidéos.
- **Lumière et beat** : `fuites_lumiere`, `projecteurs`, `tremblement` + `tremblement_zone`, `rvb_beat`,
  `glitch` (beats | transitions | les_deux) + `glitch_intensite`, `vieux_film`, `visualiseur` (barres | onde) +
  `visualiseur_zone` / `_couleur` / `_hauteur`.
- **Karaoké** : `karaoke_mode` (mot | ligne | aucun), `font`, `karaoke_taille`, `karaoke_couleur`, `karaoke_texte`,
  `karaoke_position` (bas | haut | centre), `karaoke_animation` (aucune | grossir | remplir), `karaoke_suivante`,
  `karaoke_majuscules`, `karaoke_decalage` (s, + = plus tard), `bar_alpha` (dégradé sous les paroles).
- **Textes** : `titre` / `artiste` (titre d'ouverture), `generique` (titre — artiste sur les 7 dernières s), `logo` +
  `logo_position`, `mention_ia_ecran` / `_texte` / `_position`.
- **Format et son** : `format` (16:9 | 4k | 9:16 | 1:1 ; suffixes `_4k`, `_vertical`, `_carre` ; texte ×1,4 en vertical),
  `volume_normalise` (-14 LUFS), `debut` / `fin` (s), `fade_out`, `encoder` (auto → h264_amf si disponible).
- Préréglages : **Ballade** `pulse 0`, `fondu 1.2`, look cinéma, variantes… ; **Rock** `pulse 1`, `pulse_mesure`,
  `fondu 0.15`… (définis dans `clip/web/index.html`, `PRESETS`).

## 5. Technique
- **Beats** (`clip/audio.py`) : tempo estimé par tempogramme, « famille d'octaves » ramenée entre 72 et 144 BPM, puis
  suivi par programmation dynamique à période locale. Refaire à chaque changement de chanson.
- **Alignement** (`clip/lyrics.py`) : alignement forcé stable-ts (Whisper medium, CPU) sur les paroles connues,
  jamais une transcription libre. Réparation : mots isolés d'un solo recollés au vers, vers perdu dans l'intro recalé
  avant le suivant de la même section (rythme du même vers chanté ailleurs), `force_start` pour `debut_chant`.
  Format de `words.json` : `{"segments": [{"section", "text", "start", "end", "words": [{"w", "s", "e"}]}]}`.
- **Découpe** (`clip/panels.py`) : gouttières détectées au 90e percentile (seuil strict 12 puis 30), marge de 1,5 %,
  Real-ESRGAN ×4 plafonné à 2560 px de large. Retouches ≥ 1400 px non agrandies.
- **Montage** (`clip/plan.py`) : 1 vers = son image, coupes calées au beat, passages sans paroles remplis (§3).
  `"timeline"` : `[{"t": 20.13, "img": "p1_c1"}, {"t": 35.5, "travel": "solo4.png"}]`, chaque événement durant jusqu'au suivant.
- **Rendu** (`clip/render.py`, effets purs dans `clip/effects.py`) : images PIL calculées en multiprocess (file bornée,
  démarrage « spawn » sur tous les systèmes ; ≤ 12 workers, autant que la mémoire disponible le permet, ~450 Mo chacun), pipées en rawvideo dans ffmpeg. Karaoké en sous-titres ASS incrustés (`build/karaoke.ass`), audio
  AAC 192k muxé, `+faststart`. Débit plafonné à ~12 Mb/s (le grain ferait sinon exploser la taille).
- **Encodage** : h264_amf (GPU AMD) ou libx264 preset `fast` CRF 20, `yuv420p`, 30 fps.
- Audio pour une vidéo produite hors pipeline :
  `ffmpeg -i video.mp4 -i chanson.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart final.mp4`
- Hébergement (catbox) uniquement sur demande explicite.

## 6. Leçons apprises
1. Nouveau mp3 ou paroles modifiées : détecté tout seul. Beats, alignement et montage sont refaits au prochain
   « Préparer » ou au prochain rendu (dont « Variante » et « Aperçu d'un passage »).
2. Planches : 1 image par vers unique, minimum de planches, prompts sans étiquettes ni paroles. Sinon le générateur
   écrit des légendes.
3. Tempo doublé (ex. 192 BPM au lieu de 96) : estimation par famille d'octaves, ou `bpm_hint` imposé.
4. Karaoké trop tôt sur le 1er vers : `debut_chant`.
5. Case ratée : `retouches/`, pas toute la planche.
6. Ballade : pas d'effet au beat, fondus longs.
7. Garder une copie locale de toute image ou vidéo générée (les liens des générateurs expirent).
8. Code modifié : relancer Clip Studio (le bandeau de mise à jour le signale), et lancer les tests :
   `.venv\Scripts\python.exe -m unittest` (20 tests, < 1 s, dans `tests/`).

## 7. Fichiers
| Fichier | Rôle |
|---|---|
| `Clip Studio.bat` / `Clip.bat` / `Installer.bat` | interface web / menu texte / installation (copie GitHub) |
| `clip-studio.sh` / `installer.sh` / `sauvegarder-projets.sh` | équivalents Linux |
| `Sauvegarder les projets.bat` | copie de `projets/` vers OneDrive ou un autre dossier |
| `clip/cli.py` | commandes, modèle de `projet.json`, empreintes (périmé ?), historique |
| `clip/demandes.py` | textes des demandes à Claude (descriptions, solos, vidéos) |
| `clip/web.py` | serveur local (liste blanche de commandes et d'arguments) |
| `clip/web/index.html` + `style.css` + `app.js` | interface Clip Studio (page, style, logique des étapes) |
| `clip/ocr.py` + `clip/ocr.ps1` | détection de texte dans les cases (OCR Windows) |
| `tests/test_clip.py` | tests rapides (`python -m unittest`) |
| `clip/ai.py` | appel de Claude Code (`claude -p`) |
| `clip/audio.py` / `clip/lyrics.py` | beats / paroles et alignement |
| `clip/shots.py` / `clip/prompts.py` | shotlist et planches / prompts de planches |
| `clip/evaluate.py` / `clip/publish.py` | évaluation du storyboard / publication YouTube |
| `clip/panels.py` / `clip/depth.py` | vérification, découpe, upscale / cartes de profondeur |
| `clip/plan.py` / `clip/render.py` / `clip/effects.py` | montage / rendu / effets |
| `legacy/` | anciens scripts Linux (référence, ne pas exécuter) |
| `projets/<nom>/` | `projet.json`, mp3, paroles, `planches/`, `cases/`, `solos/`, `retouches/`, `videos/`, `build/` |
