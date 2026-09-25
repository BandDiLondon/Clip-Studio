# MÉTHODE DE CRÉATION DE CLIP — Runbook
Workflows validés : Paye le Super, Mafia du fromage, Quatre ans au même endroit, Aveuglement involontaire.
Environnement et standards : voir [AGENTS.md](AGENTS.md). Commandes `clip` à venir : voir
[PLAN_AMELIORATION.md](PLAN_AMELIORATION.md) (marquées *(phase N)* ci-dessous).

---

## 0. Utilisation courante : Clip Studio (sans IA)
Double-clic sur **`Clip Studio.bat`** → interface dans le navigateur (locale, 127.0.0.1 uniquement ;
garder la fenêtre noire ouverte). 6 étapes guidées : Projet (dépôt mp3 / paroles / solos) → Préparer →
Descriptions (copier la demande pour Claude, coller sa réponse) → Planches (copier chaque prompt,
déposer P1…Pn, vérifier, découper, retoucher une case) → Options (préréglages Ballade / Rock / Sobre
et tous les effets) → Rendu (aperçu, final, variante sous un autre nom, lecteur intégré).

Descriptions : bouton **« ✨ Rédiger avec Claude »** (Claude Code + abonnement Claude Pro/Max, sans API ;
`python -m clip describe <nom> [--ids p1_c2 --consigne "…" | --tout]`), bouton ↻ par image pour en
refaire une. Claude Code est cherché dans le PATH, l'installation autonome ou l'extension VS Code, et
lancé depuis un dossier temporaire (il ne lit pas le projet). Le copier-coller reste possible.

Étape 2 **Intention de la chanson** (`"intention"`, 1500 car. max) : sens, degré (ironie, hommage…), contexte,
époque, genre, références, choses à éviter. Transmise à Claude pour l'évaluation, les descriptions et la
publication — pas au générateur d'images (qui ne reçoit que `"style"`, modifiable au même endroit).

Étape 2 **Évaluation par Claude** (automatique dans « Préparer », ou `python -m clip evaluate <nom>`) :
le code mesure les passages sans paroles, le temps d'écran des images et les cases libres ; Claude
recommande le nombre TOTAL d'images d'ambiance, une idée de scène par image (reprise ensuite par la
rédaction des descriptions) et un préréglage (ballade / rock / sobre). Appliquée d'office tant qu'aucune
planche n'est générée ; sinon bouton « Appliquer » (`evaluate --appliquer` réutilise l'évaluation affichée).

Étape 2 **Photos de solo** : « ✨ Créer les prompts avec Claude » (`python -m clip solos <nom> --nombre N`)
→ N prompts panoramiques 21:9 pensés pour le travelling (intérêt réparti sur la largeur), dans
`build/prompts_solos.md` ; un emplacement par photo (solo1, solo2… dans le dossier des solos), dépôt ou Ctrl+V.
Photos de solo et images d'ambiance **alternent** dans les passages sans paroles (répartition régulière,
en commençant par un solo) : avec assez de photos de solo, 0 image d'ambiance suffit.

Étape 7 **Publication** : titre, description YouTube et 2 prompts de miniature (avec / sans texte).
Claude rédige titre, accroche, hashtags et miniature ; le code ajoute les chapitres (calculés depuis
`build/words.json`, ≥ 10 s chacun), les paroles telles quelles et la mention IA selon `"origine"`
(`suno` | `images` | `complete`). Résultat : `build/publication.md`. CLI : `python -m clip publish <nom>`.

Alternative en mode texte : `Clip.bat` (menu).
Double-clic sur `Clip.bat` → choix du projet → menu :
1. **Préparer** (beats + paroles + prompts). Si des images restent à décrire, `build/a_decrire.md`
   s'ouvre : le coller à Claude, enregistrer sa réponse JSON dans `build/descriptions.json`,
   relancer « Préparer » → `build/prompts_planches.md` s'ouvre.
2. Générer les planches, les enregistrer en `P1.png`, `P2.png`… dans le dossier des planches.
3. **Vérifier les planches** (format, grille, taille) — optionnel, fait aussi par 4 et 5.
4. **Aperçu rapide** / 5. **Rendu final** : vérif + découpe + plan + rendu, ouvre la vidéo.
6. **Rendu seul** après modification de `projet.json` (ajustements).

Claude n'intervient que pour rédiger les descriptions (1 échange par chanson) ou en cas de problème.

Réglages conservés d'un rendu à l'autre (`projet.json`) :
- `"ajustements": {"p1_c2": {"cy": 0.1}, "p2_c4": {"fit": "contain"}}` : cadrage par image.
- `"intro_image"` / `"outro_image"` : image fixe sur l'intro / l'outro instrumental au lieu des solos.
- `"ambiance": N` : ajoute N images d'ambiance au storyboard (les cases libres de la dernière planche
  en deviennent aussi). Sans photos de solo, elles remplissent les passages instrumentaux.
- Vers mal placé par l'alignement (ex. 1er vers trop tôt) : corriger ses temps dans `build/words.json`.
- `"bar_alpha"` : opacité du dégradé sous les paroles.
- **Effets visuels** (tous désactivés par défaut) :
  - `"camera": "auto"` : mouvement selon le « Plan » de la description (large → travelling latéral,
    gros plan / rapproché → zoom avant, moyen → zoom arrière) ; forçable par image dans `ajustements`.
  - `"look": "cinema"` : étalonnage (ombres froides, hautes lumières chaudes) + grain + vignettage.
  - `"letterbox": true` : bandes noires 2,39:1, image cadrée dans la zone centrale, paroles dans la bande.
  - `"harmonisation": true` : couleurs des planches rapprochées entre elles.
  - `"variantes": true` : image répétée (refrain) → sens et miroir alternés, dernière fois en quasi N&B.
  - `"titre"` / `"artiste"` : titre d'ouverture en fondu sur l'intro ; `"generique": true` (défaut)
    ajoute « titre — artiste » sur les 7 dernières secondes.
  - `"look_sections": true` : refrain plus lumineux et saturé, couplets plus sombres, pont désaturé.
  - `"particules": "auto"` : neige (neige, hiver…) ou poussière lumineuse (bar, scène, fumée…) selon
    la description ; forçable : `"particules": "neige"`, ou par image dans `ajustements`.
  - `"pulse_mesure": true` (rock) : effet beat seulement sur le 1er temps de chaque mesure.
  - `"parallaxe": true` (ou une amplitude, ex. `0.05`) : caméra 3D selon la profondeur estimée de
    chaque image (build/depth/, calculée une fois). Désactivable par image : `ajustements` → `"parallaxe": false`.
  - Karaoké : `karaoke_mode` (mot | ligne | aucun), `font`, `karaoke_taille`, `karaoke_couleur` / `karaoke_texte`,
    `karaoke_position` (bas | haut | centre), `karaoke_animation` (aucune | grossir | remplir), `karaoke_suivante`,
    `karaoke_majuscules`, `karaoke_decalage` (s).
  - Signature : `logo` (+ `logo_position`), `mention_ia_ecran` / `mention_ia_texte` / `mention_ia_position`.
  - Montage : `transition` (fondu | coupe | noir | flash | glissement | zoom, durée = `fondu`), `duree_max_image`.
  - Look : `look` (aucun | cinema | nb | sepia | vhs | neon | froid), `grain`, `vignettage`, `luminosite`, `contraste`,
    `camera_intensite`, `particules_densite`, `particules_sections` ({"refrain": "braises", …}).
  - Fumée : `fumee` (None | auto | fumee | brouillard) + `fumee_densite` ; se combine avec les particules ;
    auto selon la description (fumée, brume, brouillard, feu…) ; par image : `ajustements` → `"fumee"`.
  - Particules supplémentaires : `pluie`, `confettis`, `bokeh`, `etincelles` (auto selon la description).
  - Lumière : `fuites_lumiere` (0-1), `projecteurs` (0-1, au beat), `eclairs` / `rayons` (auto | partout,
    + `rayons_intensite`).
  - Rythme : `tremblement` (0-1) + `tremblement_zone` (partout | refrains), `rvb_beat` (0-1),
    `glitch` (beats | transitions | les_deux) + `glitch_intensite`.
  - Pellicule et son : `vieux_film` (0-1), `visualiseur` (barres | onde) + `visualiseur_zone`
    (instrumentaux | partout), `visualiseur_couleur`, `visualiseur_hauteur`.
  - Profondeur : `flou_fond`, `brume_profondeur` (0-1, cartes de profondeur calculées une fois).
  - Code des effets : `clip/effects.py` (fonctions pures), branchés dans `clip/render.py`.
  - Format et son : `format` (16:9 | 4k | 9:16 | 1:1 ; suffixe _4k / _vertical / _carre), `volume_normalise`
    (-14 LUFS), `debut` / `fin` (s). Aperçu d'un passage : étape 6 ou `clip preview <nom> --start s --duration s`.
  - Rendu sous un autre nom : `python -m clip render <nom> --out fichier.mp4`.
  - Débit plafonné à ~12 Mb/s (le grain ferait sinon exploser la taille du fichier).
- **Ballade** : `"pulse": 0` (aucun gonflement ni flash au beat) + `"fondu": 1.2` (fondu enchaîné
  de 1,2 s centré sur chaque changement de vers). Rock : `"pulse": 1`, `"fondu": 0.15`.
- Une case ratée → générer une image 16:9 seule, la déposer dans `retouches/p1_c2.png` : elle
  remplace la case au prochain rendu (pas besoin de refaire la planche).

## 0 bis. Pipeline (commandes)

```
python -m clip <commande> <nom>
1. Projet        new               → projets/<nom>/ (+ déposer mp3, paroles .txt, planches, solos)
2. Découpe       cut               → cases/pN_cK.png (Real-ESRGAN ×4) + build/planche_contact.jpg ✔
3. Beats         beats             → build/beats.npy          (tempo estimé auto ; bpm_hint = nombre pour l'imposer)
4. Paroles       align             → build/words.json         (--repair-only pour re-réparer)
5. Plan          plan [--force]    → projet.json "timeline"   ✔ validation / retouche manuelle
6. Aperçu        preview [--start s --duration s] → build/preview.mp4 (960×540@15)  ✔ validation
7. Rendu final   render            → build/<nom>.mp4 (1080p30, karaoké, audio, fondu de fin)
0. Prompts      prompts           → build/shotlist.json + prompts (avant de générer les planches)
À venir : thumb / vertical / upload (phase 6)
```

### projet.json
```json
{ "audio": "chanson.mp3", "paroles": "paroles.txt",
  "planches": "images", "solos": "images", "solos_list": ["solo1.png", "solo2.png"],
  "planches_map": {"Verse 1": "p1", "Chorus": "p2"},
  "bpm_hint": 100, "fps": 30, "size": [1920, 1080],
  "fit": "cover", "cy": 0.4, "fade_out": 2.5, "encoder": "auto",
  "timeline": [ {"t": 0.0, "travel": "solo1.png"},
                {"t": 20.13, "img": "p1_c1", "cy": 0.1, "note": "vers"} ] }
```
- `timeline` : chaque événement dure jusqu'au suivant. `img` = case, `travel` = solo panoramique.
- Par événement : `fit` (`cover` plein cadre | `contain` case entière sur fond flou),
  `cy` (ancrage vertical du recadrage 16:9 : 0 = haut, 1 = bas) — à baisser si une tête est coupée.
- `clip plan` fait 1 vers = 1 case ; les coupes au mot près et les cases en trop (c5, c6) se
  placent à la main (temps des mots dans `build/words.json`).

Résultat : clip où chaque case illustre LITTÉRALEMENT le vers chanté, karaoké mot-à-mot,
léger zoom, pulse + flash au beat, travelling sur les solos.

---

## 1. Entrées
- `chanson.mp3` + `paroles.txt` (texte exact, un vers par ligne, lignes vides entre sections).
- Format mot-à-mot utilisé par le rendu (`build/words.json`) :
```json
{ "segments": [ { "start": 0.0, "end": 2.3, "text": "vers",
                  "words": [ {"w": "mot", "s": 0.0, "e": 0.4} ] } ] }
```
Whisper sort `word/start/end` → convertir en `w/s/e`. Préférer l'**alignement forcé** sur les
paroles connues (stable-ts) à une transcription libre : moins de corrections manuelles.

## 2. Beats
Tempo non constant → tracker **adaptatif** (autocorrélation glissante + DP à période variable),
pas un métronome. Référence : `legacy/beat_detect_adapt.py` (attend un PCM float32 mono) :
```
ffmpeg -i chanson.mp3 -ac 1 -ar 44100 -f f32le beats.raw
```
Utilisation : **pulse** (zoom qui gonfle au beat) et **flash** blanc bref si pulse > 0.5.
```python
pulse = 0.0
for b in beats:                       # (phase 5 : bisect sur les beats voisins)
    d = t - b
    if -0.10 < d < 0.30:
        pulse = max(pulse, math.exp(d / -0.09))
```
Régénérer les beats à chaque changement de chanson.

## 3. Storyboard — planches = économie de générations
⚠️ **RÈGLE D'OR** : les planches servent à **limiter le nombre de générations d'images**.
On calcule le nombre exact d'images requis par le texte, puis on les range dans le minimum de
planches. Jamais une grande image unique découpée ensuite (approche refusée).

- **1 image par vers unique.** Un vers répété (refrain, vers identique ailleurs, à l'accent près)
  réutilise la même image. Désactivable : `"dedupe": false` dans projet.json.
- **Rangement** : planches de 6 (grille 2×3, image **32:27**, 2048×1728 ou 1536×1296) ; la dernière
  prend la plus petite grille qui suffit : 4 → 2×2 en 16:9, 2 → 1×2 en 8:9, 1 → image 16:9 seule.
  Toutes les vignettes sont en **16:9** (~1024×576). `clip cut` signale un ratio ≠ 16:9.
- Ids : `p1_c1 … pN_cK`, ordre rangée 1 gauche→droite, puis rangée 2… La table vignette ↔ vers est
  dans `build/shotlist.json` et en tête du fichier de prompts. `clip plan` s'en sert : chaque vers
  (répétitions comprises) retrouve son image automatiquement.
- ⚠️ Ancien format 3×2 en 3:2 (1168×784) = vignettes carrées de 385 px, 44 % coupé en 16:9 → abandonné.

### Rédaction stricte de chaque vignette
`python -m clip prompts <nom>` → `build/prompts_squelette.md` (sans descriptions) puis, une fois les
descriptions écrites dans projet.json `"descriptions": {"p1_c1": "…"}`, → `build/prompts_planches.md`.
Chaque vignette : **Plan ; Sujet ; Action ; Décor ; Lumière**, tous remplis :
- **Action** = l'illustration LITTÉRALE du vers, une seule action lisible.
- **Plan** : large / moyen / rapproché / gros plan (les plans larges supportent le mieux le 16:9).
- Personnages récurrents décrits une fois dans `"personnages"` et nommés à l'identique dans les
  vignettes (« le Québécois ») → même visage, mêmes vêtements d'une planche à l'autre.
- **Ne pas citer les paroles dans le prompt** : un texte entre guillemets finit écrit dans l'image.
- Éviter documents, factures, écrans, pancartes : ils génèrent du faux texte.
- En-tête imposé : « EXACTEMENT N vignettes (ni plus ni moins) », « chaque vignette montre UNIQUEMENT
  la scène décrite », + négatif (texte, numéros, vignettes carrées/verticales, vignette supplémentaire).
Exemple complet : `projets/aveuglement/build/prompts_planches.md` (18 images → 3 planches au lieu de 6).
Vérifier chaque planche : bon nombre de vignettes, pas de texte parasite, chaque case = son vers.

## 4. Images de solo
Passages instrumentaux : image **panoramique 21:9 ou plus large** (ex. montage photos de concert
N/B + rouge/bleu) dans `solos/`. Pas de karaoké, pas de grille.

### Vidéos animées (optionnel, Flow / Veo)
`videos/<id>.mp4` (ex. `solo1.mp4`, `p4_c4.mp4`) remplace l'image `<id>` au montage, effets par-dessus.
Onglet **5. Vidéos** de Clip Studio : clic sur une image → « ✨ Écrire le prompt vidéo avec Claude » (cette image seule),
copier le prompt, déposer la vidéo, ou la retirer pour revenir à l'image.
Les prompts vidéo ne sont **jamais créés automatiquement**, seulement sur demande
(`python -m clip videos <nom> --ids p1_c2` ; sans `--ids` : `--nombre N`, Claude choisit les images qui restent le plus
longtemps à l'écran, ce qui exige un aperçu ou un rendu).
Le résultat va dans `build/videos.json` et `build/prompts_videos.md`.

## 5. Découpe
Découper chaque planche en 6 cases en retirant les gouttières noires + ~3 % de marge,
écrire directement dans `cases/`. ⚠️ Toute nouvelle image doit être dans `cases/` avant le rendu.

## 6. Rendu
`clip/render.py` (frame-à-frame PIL multiprocess, pipé en rawvideo dans ffmpeg, file bornée ;
karaoké en sous-titres ASS incrustés ; audio muxé ; h264_amf si dispo). ~30 s pour 2:24 en 1080p.
- Case active selon le plan, redimensionnée « cover » (scale max + crop centre).
- `zoom = 1.0 + 0.05*sin(t*0.6) + 0.05*pulse` ; flash `blend(frame, blanc, (pulse-0.5)*0.22)`.
- Karaoké : bandeau noir translucide en bas, mots centrés, mot courant `(255,220,80)`, autres blancs,
  contour noir. Mot courant repéré **par index**, pas par comparaison de texte.
- Solos (`render_travel_frame`) : pano suréchantillonnée, fenêtre 16:9 qui glisse gauche→droite
  (ease in-out), `zoom = 1.0 + 0.06*ease` + pulse.
- Transitions : coupe franche calée au beat ou crossfade court ; pas de fondu au noir par vers.

`legacy/karaoke_render.py` (zoompan ffmpeg par segment + concat) est abandonné : dérive de synchro
à la concaténation et fondu au noir entre chaque vers.

## 7. Audio (IMPORTANT)
`clip render` / `clip preview` incluent l'audio. Pour une vidéo produite hors pipeline :
```
ffmpeg -i video.mp4 -i chanson.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart final.mp4
```

## 8. Encodage + hébergement
- libx264 preset `fast` CRF 20 `yuv420p`, ou `h264_amf` (GPU). 1920×1080, 30 fps.
- Hébergement sur demande uniquement : catbox (`https://catbox.moe/user/api.php`).

## 9. Miniature YouTube
- Seedream 16:9 (2560×1440) → `1280×720`.
- Style : collage photos de concert N/B + rouge/bleu, grain.
- Mention « **VERSION AI** » : discrète bas-droite, ou dominante avec titre en petit en bas.
- Vérifier l'orthographe par analyse d'image.

---

## 10. Leçons apprises
0. Nouveau mp3 → « Préparer » avec « Refaire » (beats + paroles). Le montage des images (`timeline`) est
   recalculé automatiquement à chaque rendu dès que le mp3, les paroles calées, les beats, les planches ou les
   solos ont changé (empreinte `timeline_sig` dans projet.json).
1. Toute nouvelle image doit être dans `cases/` avant le rendu.
2. Toujours inclure l'audio (sinon clip muet).
3. 1 image par vers unique, rangées dans le minimum de planches (2×3 en 32:27), vignettes 16:9,
   chaque vignette décrite strictement, paroles jamais citées dans le prompt.
4. Régénérer les beats si la chanson change.
5. Solos : travelling sur panoramique, pas de karaoké.
6. Karaoké mot-à-mot = JSON avec `words` ; sinon texte plein.
7. Garder une copie locale de toute image générée (les liens des générateurs expirent).

## 11. Fichiers
| Fichier | Rôle |
|---|---|
| `clip/` | Module du pipeline (`python -m clip …`) |
| `projets/<nom>/projet.json` | Plan de montage de la chanson |
| `legacy/beat_detect_adapt.py` | Tracker de beats adaptatif (référence) |
| `legacy/render_av3.py` | Rendu frame-à-frame + karaoké + travelling (référence) |
| `legacy/karaoke_render.py` | Ancienne variante zoompan (abandonnée) |
| `legacy/travelling_demo.py` | Démo travelling (remplacée par `render_travel_frame`) |
