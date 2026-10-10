# Documentation technique de Clip Studio

Pour qui veut comprendre, modifier ou dépanner le code (humain ou IA). L'utilisation est décrite dans
[GUIDE.md](GUIDE.md), les règles de travail pour une IA dans [AGENTS.md](../AGENTS.md).

- [Architecture](#architecture)
- [Commandes](#commandes)
- [Fichiers d'un projet](#fichiers-dun-projet)
- [Storyboard et planches](#storyboard-et-planches)
- [Réglages de projetjson](#réglages-de-projetjson)
- [Traitements](#traitements)
- [Détection des changements](#détection-des-changements)
- [Claude](#claude)
- [Portabilité Windows / Linux](#portabilité-windows--linux)
- [Tests, captures, versions](#tests-captures-versions)

---

## Architecture

```
Clip Studio.bat / clip-studio.sh ──► python -m clip web ──► clip/web.py (serveur local 127.0.0.1)
                                                             │  page : clip/web/index.html + style.css + app.js
                                                             │  chaque action = une commande de la liste blanche,
                                                             ▼  lancée en sous-processus (journal diffusé à la page)
                                                        python -m clip <commande> <projet>   (clip/cli.py)
```

| Module | Rôle |
|---|---|
| `clip/cli.py` | commandes, modèle de `projet.json` (`PROJET_TEMPLATE`), empreintes (périmé ?), historique |
| `clip/web.py` | serveur local : état d'un projet (`status`), liste blanche de commandes et d'arguments, dépôts de fichiers ; refuse les requêtes dont `Host` ou `Origin` n'est pas 127.0.0.1 / localhost (`_etranger`) |
| `clip/web/app.js` | interface : une fonction de rendu par étape (`V.<étape>`), préréglages (`PRESETS`), options |
| `clip/audio.py` | tempo et beats |
| `clip/lyrics.py` | lecture des paroles, alignement mot à mot (stable-ts), réparation |
| `clip/shots.py` | shotlist : 1 image par vers unique, rangement en planches |
| `clip/prompts.py` | prompts de planches |
| `clip/panels.py` | vérification des planches, découpe, Real-ESRGAN, planche-contact |
| `clip/plan.py` | montage (timeline) calé sur les beats |
| `clip/render.py` + `clip/effects.py` | rendu image par image, effets (fonctions pures), karaoké ASS, encodage |
| `clip/depth.py` | cartes de profondeur (parallaxe, flou de fond) |
| `clip/ai.py` + `clip/demandes.py` | appel de Claude Code ; textes des demandes (descriptions, solos, vidéos) |
| `clip/evaluate.py` / `clip/publish.py` | évaluation du storyboard / publication YouTube (demandes incluses) |
| `clip/ocr.py` | texte lisible dans les cases (RapidOCR, Windows et Linux) |
| `tests/test_clip.py` | tests rapides |
| `scripts/captures.py` | captures d'écran du README |

---

## Commandes
`python -m clip <commande> <projet> [options]` (`.venv\Scripts\python.exe` sous Windows, `.venv/bin/python` sous Linux).

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
| `verify` / `cut [--scale 1]` | contrôle / découpe + agrandissement + OCR | `cases/`, `build/planche_contact.jpg` |
| `plan [--force]` | montage | `projet.json` → `"timeline"` |
| `preview [--start --duration]` / `render [--out]` | aperçu / rendu seul | `build/preview.mp4`, `build/<nom>.mp4` |
| `build-preview` / `build [--force]` | vérif + découpe + plan + aperçu / rendu | idem |
| `publish [--consigne]` | publication YouTube (Claude) | `build/publication.md` |

Une commande ajoutée à l'interface doit aussi l'être dans `COMMANDS` (et ses arguments dans `ARG_VALUES`) de `clip/web.py`.

---

## Fichiers d'un projet
```
projets/<nom>/
  projet.json          réglages + montage (timeline) + empreintes
  <chanson>.mp3, <paroles>.txt
  planches/P1.png…     images générées (grilles)
  cases/p1_c1.png…     cases découpées et agrandies (recalculables)
  retouches/p1_c2.png  remplace une case (prioritaire sur la découpe)
  solos/solo1.png…     panoramiques des passages instrumentaux
  videos/p1_c3.mp4…    remplace une image au montage
  build/               words.json, beats.npy, shotlist.json, descriptions.json, prompts_*.md, evaluation.json,
                       videos.json, publication.md, texte_detecte.json, karaoke.ass, historique/, rendus .mp4
```
- `words.json` : `{"segments": [{"section", "text", "start", "end", "words": [{"w", "s", "e"}]}]}`.
- `timeline` : `[{"t": 20.13, "img": "p1_c1"}, {"t": 35.5, "travel": "solo4.png"}]`, chaque événement dure jusqu'au suivant.
- `build/descriptions.json` : `{"p1_c1": "Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …"}`. La clé
  `"descriptions"` de `projet.json` est prioritaire.

---

## Storyboard et planches
**Règle d'or : les planches servent à limiter le nombre de générations d'images.** On calcule le nombre exact d'images
requis par le texte, puis on les range dans le minimum de planches.
- **1 image par vers unique** (clé normalisée : casse, accents, ponctuation), `"dedupe": false` pour désactiver. S'y
  ajoutent les images d'**ambiance** (`"ambiance": N`, nombre total) ; les cases libres de la dernière planche deviennent
  aussi de l'ambiance.
- **Rangement** (`shots._pack`) : planches de 6 (grille 2×3, image 32:27) ; la dernière prend la plus petite grille
  suffisante : 4 → 2×2 (16:9), 2 → 1×2 (8:9), 1 → image seule. Vignettes toujours 16:9. Ajouter de l'ambiance ne change
  pas les planches déjà pleines.
- Ids `p1_c1 … pN_cK` : rangée 1 de gauche à droite, puis rangée 2…
- Passages sans paroles : photos de solo et images d'ambiance **alternent** (`plan._Filler`), en commençant par un solo.

**Prompt de planche** (`clip/prompts.py`) :
- En-tête « Une seule image composée de EXACTEMENT N photographies de cinéma… AUCUNE légende… ». Jamais le mot
  « storyboard » : un storyboard a des légendes, que le générateur écrit alors.
- Chaque case = « Photo i (position) : … ». La description est convertie en phrase **sans les étiquettes**
  Plan / Sujet / Action…, qui finiraient écrites en légende (`prose`).
- Quart inférieur de chaque vignette laissé libre (zone des paroles). Négatif : texte, légende, sous-titre, numéros,
  enseigne lisible, vignettes carrées ou verticales, vignette supplémentaire.
- **Jamais les paroles dans un prompt** : un texte entre guillemets finit écrit dans l'image.

---

## Réglages de `projet.json`
Tous présents dans `PROJET_TEMPLATE` (`clip/cli.py`, avec commentaires) et modifiables à l'étape 6 (`app.js`).
Conservés d'un rendu à l'autre ; tous les effets sont désactivés par défaut.
- **Cadrage** : `fit` (`cover` | `contain` sur fond flou), `cy` (0 = haut, 1 = bas). Par image :
  `"ajustements": {"p1_c2": {"cy": 0.1, "fit": "contain", "camera": "…", "particules": "…", "fumee": "…", "parallaxe": false}}`.
- **Rythme** : `pulse`, `pulse_mesure`, `fondu`, `transition` (fondu | coupe | noir | flash | glissement | zoom),
  `duree_max_image`, `bpm_hint` (`"auto"` ou BPM imposé).
- **Caméra** : `camera` (`zoom` | `auto` selon le « Plan »), `camera_intensite`, `parallaxe`.
- **Look** : `look` (aucun | cinema | nb | sepia | vhs | neon | froid), `grain`, `vignettage`, `luminosite`, `contraste`,
  `letterbox`, `harmonisation`, `variantes`, `look_sections`.
- **Atmosphère** : `particules` (auto | neige | poussiere | braises | pluie | confettis | bokeh | etincelles),
  `particules_densite`, `particules_sections`, `fumee` + `fumee_densite`, `flammes` + `flammes_hauteur` /
  `flammes_intensite`, `eclairs`, `rayons` + `rayons_intensite`, `flou_fond`, `brume_profondeur`.
  « auto » = selon les mots de la description.
- **Lumière et beat** : `fuites_lumiere`, `projecteurs`, `tremblement` + `tremblement_zone`, `rvb_beat`, `glitch` +
  `glitch_intensite`, `vieux_film`, `visualiseur` + `visualiseur_zone` / `_couleur` / `_hauteur`.
- **Karaoké** : `karaoke_mode` (mot | ligne | aucun), `font`, `karaoke_taille`, `karaoke_couleur`, `karaoke_texte`,
  `karaoke_position`, `karaoke_animation`, `karaoke_suivante`, `karaoke_majuscules`, `karaoke_decalage`, `bar_alpha`.
- **Textes** : `titre`, `artiste`, `generique`, `logo` + `logo_position`, `mention_ia_ecran` / `_texte` / `_position`,
  `origine` (`suno` | `images` | `complete`, pour la mention IA de la publication).
- **Paroles** : `debut_chant` (s), `intention`, `style`, `personnages`.
- **Format et son** : `format` (16:9 | 4k | 9:16 | 1:1), `volume_normalise` (-14 LUFS), `debut` / `fin`, `fade_out`,
  `fps`, `encoder` (auto | amf | x264).
- **Gérés par le code** (ne pas éditer) : `timeline`, `timeline_sig`, `beats_sig`, `paroles_sig`, `bpm_detecte`,
  `solos_list`.

---

## Traitements
- **Beats** (`audio.py`) : tempo estimé par tempogramme, « famille d'octaves » ramenée entre 72 et 144 BPM, puis suivi
  par programmation dynamique à période locale.
- **Alignement** (`lyrics.py`) : alignement forcé stable-ts (Whisper medium, CPU, ~4,7 Go de mémoire au maximum) sur les
  paroles connues, jamais une transcription libre. Réparation : mots isolés recollés au vers, vers perdu dans l'intro
  recalé avant le suivant de la même section (rythme du même vers chanté ailleurs), `force_start` pour `debut_chant`.
- **Découpe** (`panels.py`) : gouttières détectées au 90e percentile (seuil strict 12, puis 30), marge de 1,5 %,
  Real-ESRGAN ×4 plafonné à 2560 px. Sans Vulkan ou sans binaire : agrandissement Lanczos avec avertissement
  (jamais bloquant). Retouches ≥ 1400 px non agrandies.
- **Détection de texte** (`ocr.py`) : RapidOCR (modèles PaddleOCR via onnxruntime), image réduite à 1280 px, lignes de
  confiance ≥ 0,5 et d'au moins 3 lettres ; résultat dans `build/texte_detecte.json`, jamais bloquant. Comparaison sur
  165 cases : 14 textes réels trouvés (t-shirts, néons, enseignes) contre 3 pour l'OCR intégré à Windows utilisé avant,
  1 fausse alerte ; Tesseract écarté (25 fausses alertes). Télémétrie d'onnxruntime coupée (`ORT_DISABLE_TELEMETRY=1`
  avant l'import : sinon, sous Linux, identifiant d'appareil dans `~/.cache/Microsoft` et envois possibles).
  RapidOCR s'installe avec `--no-deps` : il exige `opencv-python`, en conflit avec `opencv-python-headless`.
- **Montage** (`plan.py`) : 1 vers = son image, coupes calées au beat, passages sans paroles remplis.
- **Rendu** (`render.py`) : images PIL calculées en parallèle (processus démarrés en « spawn » sur tous les systèmes,
  file bornée, ≤ 12 processus selon la mémoire disponible, ~450 Mo chacun ; threads numpy / OpenCV par processus =
  cœurs ÷ processus, arrondi au-dessus, sinon les processus se gênent et le rendu est 2× plus lent), envoyées en rawvideo à ffmpeg. Karaoké en
  sous-titres ASS incrustés, audio AAC 192k muxé, `+faststart`. H.264 `yuv420p` 30 fps : h264_amf (GPU AMD) si
  disponible, sinon libx264 `fast` CRF 20 ; débit plafonné à ~12 Mb/s. Aperçu 960×540 à 15 fps, `ultrafast`.
- Ajouter l'audio à une vidéo produite hors de Clip Studio :
  `ffmpeg -i video.mp4 -i chanson.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart final.mp4`
- **Vidéos** : `videos/<id>.mp4` remplace l'image `<id>` ; images extraites une fois dans `build/video_frames/`,
  étirées si le plan est plus long.

---

## Détection des changements
- **Beats / alignement** : empreintes `beats_sig` et `paroles_sig` (mp3 : nom + taille + date ; paroles : contenu
  normalisé ; tempo imposé ; début du chant). `perimes()` compare ; `prepare`, `build` et `render` refont ce qui est périmé.
  Sans empreinte (ancien projet), comparaison des dates.
- **Montage** : `timeline_sig` (mp3, `words.json`, `beats.npy`, shotlist, solos, images d'intro / d'outro). Recalculé
  avant chaque rendu si différent.
- **Historique** : `_save()` garde l'ancienne version de `projet.json` dans `build/historique/` (30 max, au plus une par
  minute ; toujours lors d'une restauration).
- **Serveur** : `code_perime()` signale à la page que le code a changé depuis le lancement (bandeau orange).

---

## Claude
- `clip/ai.py` appelle **Claude Code** (`claude -p`, sortie JSON) avec la demande sur l'entrée standard, depuis un dossier
  temporaire : aucun contexte du projet n'est chargé. Recherche : PATH, `~/.local/bin`, npm, extension VS Code / Cursor.
- Appel « nu » (`OPTIONS` dans `ai.py`) : sans outils, connecteurs MCP, réglages de l'utilisateur ni consignes
  de Claude Code (`--tools ""`, `--strict-mcp-config`, `--setting-sources ""`, `--system-prompt` d'une ligne). Le
  surcoût fixe passe de ~34 500 à ~700 tokens par appel (mesuré), réponse identique. `--bare` est exclu : il ignore la
  connexion par abonnement.
- **Appelé uniquement sur action de l'utilisateur**, sauf l'évaluation lancée par `prepare`. Ne jamais ajouter d'appel
  automatique.
- Textes des demandes : `clip/demandes.py`, `clip/evaluate.py`, `clip/publish.py`. Réponses en JSON strict.
- Sans Claude : `build/a_decrire.md` à coller dans un assistant, réponse JSON dans `build/descriptions.json`.

---

## Portabilité Windows / Linux
Le même code tourne sur les deux systèmes :
- ouvrir un fichier : `_ouvrir()` (`web.py`) ;
- polices : `_font()` (`panels.py`) et `FONT_CANDIDATES` (`cli.py`) ;
- binaire Real-ESRGAN selon `sys.platform` ;
- rendu en « spawn ».

À proscrire : `os.startfile`, `explorer`, chemins `.exe` ou polices Windows sans repli, `/tmp` codé en dur. Lanceurs :
`.bat` (CRLF) et `.sh` (LF, exécutables), voir `.gitattributes`.

---

## Tests, captures, versions
- **Tests** : `python -m unittest` (dans `tests/`, moins de 1 s). À lancer après toute modification ; ajouter un test pour
  tout bug de logique corrigé (shotlist, paroles, montage, empreintes, découpe). Sur GitHub, l'action « Tests » les
  lance sous Windows et Linux à chaque envoi sur `main` et à chaque pull request.
- **Captures du README** : `python scripts/captures.py [projet]`. Le script travaille sur une copie temporaire du projet ;
  `?sel=p1_c3` dans l'adresse présélectionne une image à l'étape Vidéos.
- **Versions** :
  1. noter les changements dans [CHANGELOG.md](../CHANGELOG.md), sous un titre `## [x.y.z] - AAAA-MM-JJ` ;
  2. `git tag vx.y.z && git push origin vx.y.z`.

  L'action `.github/workflows/release.yml` crée alors la Release avec deux zips (`…-Windows.zip` sans les `.sh`,
  `…-Linux.zip` sans les `.bat`) et reprend la section du CHANGELOG comme notes.
- **Performances** : temps mesurés dans [GUIDE.md](GUIDE.md#temps-de-calcul) (chanson de 3 min 14, 16 cœurs et 4 cœurs
  simulés). Le rendu dépend surtout du processeur : l'encodeur GPU (h264_amf) ne gagne qu'environ 10 % sur libx264.
  Pour mesurer, `CLIP_WORKERS` et `CLIP_THREADS` forcent le nombre de processus de rendu et de threads par processus
  (12 processus étaient optimaux sur 32 threads ; 16 → +10 %, 24 → +25 %). Un script qui lance le rendu doit protéger
  son code par `if __name__ == "__main__":` (démarrage « spawn »).
- **Provenance du code** : le code a été écrit en grande partie avec un assistant IA (Claude, Anthropic), sous la
  direction de l'auteur (voir le README). Les contributions faites avec une IA sont bienvenues, à condition d'être
  relues, testées (`python -m unittest`) et signalées comme telles.
- **Dépendances** : versions figées dans `requirements.txt` (environnement complet testé : `requirements-complet.txt`) ;
  torch CPU et `rapidocr` (`--no-deps`) installés à part par les installateurs. Sans RapidOCR, la détection de texte
  est simplement désactivée (`textes()` renvoie `None`).
