# Plan d'amélioration du pipeline de clips

Hypothèses : images générées par l'utilisateur (Qwen/Seedream), paroles exactes fournies,
Windows 11, validation à chaque étape. GPU : AMD RX 9070 XT → encodeur `h264_amf`.

## Phase 0 — Environnement
- Python 3.12 + `numpy`, `Pillow`, `librosa`, `stable-ts` (alignement), ffmpeg dans le PATH.
- `requirements.txt` + `python -m clip check`.
- Arborescence :
```
clip/            module commun (audio, lyrics, panels, render, cli)
legacy/          anciens scripts (référence)
projets/<nom>/   chanson.mp3, paroles.txt, projet.json, planches/, cases/, solos/, build/
```
Critère : `python -m clip check` tout vert.

## Phase 1 — Documentation
- AGENTS.md aligné sur le vrai projet (Windows, 30 fps, lien METHODE).
- METHODE nettoyée (contexte ancien AI retiré, étapes manquantes ajoutées, planches sans numéros).

## Phase 2 — Port Windows + fichier projet
- Chemins relatifs (`pathlib`), police Arial Bold / police fournie.
- PLAN/EVENTS/TRAVEL/DUR → `projet.json`.
Critère : refaire « Aveuglement involontaire » sans toucher au code.

## Phase 3 — Analyse audio & paroles
- `clip beats` : mp3 direct, tracker corrigé → `beats.npy`.
- `clip align` : alignement forcé paroles connues → `words.json` (+ rapport mots douteux).
- `clip plan` : `projet.json` auto (1 vers = 1 case, refrains, solos), coupes calées au beat.

## Phase 4 — Images
- `clip prompts` : prompts de planches sans numéros.
- Grille 3×2 à cases 16:9 (planche 8:3, ex. 2400×900) ; upscale optionnel.
- `clip cut` : découpe auto (détection des gouttières) → `cases/` + planche-contact.

## Phase 5 — Rendu unifié
- Moteur frame-à-frame : zoom, pulse/flash, travelling ping-pong, crossfade court.
- Karaoké ASS `\k` incrusté par ffmpeg, surlignage par index.
- Audio muxé dans la même commande, `+faststart`.
- `bisect` beats, `imap` chunksize, `h264_amf` si dispo.
- `clip preview` (960×540, 15 fps) / `clip render`.
Critère : ≥2× plus rapide, synchro ±1 frame.

## Phase 6 — Livrables
- `clip thumb`, `clip vertical` (9:16), `clip upload` (catbox, sur demande).

## Flux cible
```
clip new → beats → align → plan (validation) → prompts → [planches] → cut (validation)
→ preview (validation) → render → thumb / vertical
```

## Avancement
- [x] Phase 0 — env, `clip check`, `clip new`
- [x] Phase 1 — AGENTS.md, METHODE
- [x] Phase 2 — projet.json, chemins Windows ; « Aveuglement » refait sans toucher au code
- [x] Phase 3 — `beats` (a priori de tempo), `align` (stable-ts + réparation), `plan`
- [x] Phase 4 — `cut` (grille configurable) + Real-ESRGAN, `prompts` ; format retenu : grille 2×3
      en 32:27 (vignettes 16:9 ~1024×576) plutôt que 3×2 en 8:3 (trop large pour les générateurs)
- [x] Phase 5 — rendu unifié, ASS, audio, AMF, xfade, fondu de fin, `preview` (31 s / 2:24 en 1080p)
- [x] Autonomie — `Clip.bat`, `prepare` / `build`, `verify`, retouches/, ajustements conservés,
      intro/outro_image, nettoyage des cases, zone paroles dans les prompts, a_decrire.md → descriptions.json
- [ ] Phase 6 — thumb, vertical, upload
- [ ] Idées : fiche personnage (image de référence), mouvements de caméra selon le plan,
      feuille de montage HTML, préréglage d'export web, git
