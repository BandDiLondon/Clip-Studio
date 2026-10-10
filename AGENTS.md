# Instructions pour les assistants IA / Instructions for AI assistants (Claude Code, Codex, Cursor…)

[Français](#français) | [English](#english) — les deux parties disent la même chose; les modifier ensemble.
Both parts say the same thing; change them together.

## Français

Clip Studio fabrique des clips musicaux illustrés : chaque vers d'une chanson a son image, les paroles s'affichent en
karaoké mot à mot, le montage suit les beats. L'utilisateur génère lui-même les images à partir des prompts préparés
par Clip Studio.

**À lire** : [docs/GUIDE.md](docs/GUIDE.md) (utilisation, dépannage) et [docs/TECHNIQUE.md](docs/TECHNIQUE.md)
(architecture, commandes, `projet.json`, conventions), ou leurs versions anglaises (`*.en.md`). Ne pas supposer un
système : Clip Studio tourne sous Windows, sous Linux et sous macOS (expérimental); vérifier avec l'utilisateur ou dans
l'environnement.

### Aider l'utilisateur
- Il travaille surtout dans l'interface (`Clip Studio.bat` / `./clip-studio.sh` / `Clip Studio.command`). Indique-lui
  l'étape et le bouton plutôt qu'une commande, sauf s'il préfère la ligne de commande (`python -m clip <commande>
  <projet>`, depuis le `.venv`).
- **Ne lance pas les étapes à sa place** (préparation, rendu, publication) sans qu'il le demande : il valide à chaque
  étape (descriptions → planches → aperçu → rendu final).
- Problème : commence par `python -m clip check`, puis le tableau « Dépannage » de GUIDE.md et le journal de la commande.
- S'il colle le contenu de `build/a_decrire.md`, réponds **uniquement** par le JSON demandé (`{"p1_c1": "Plan : … ;
  Sujet : … ; Action : … ; Décor : … ; Lumière : …", …}`, ou `Shot: … ; Subject: … ; Action: … ; Setting: … ;
  Lighting: …` pour un projet en anglais), à enregistrer dans `build/descriptions.json`.
- Réponds dans la langue de l'utilisateur. L'interface et la documentation existent en français et en anglais.

### Règles des planches (à respecter dans toute description ou prompt)
- Les planches servent à **limiter le nombre de générations** : 1 image par vers unique, rangées dans le minimum de
  planches (grilles 2×3 en 32:27), vignettes 16:9.
- Chaque description : **Plan; Sujet; Action; Décor; Lumière**. L'action illustre **littéralement** le vers, une seule
  action lisible. Personnages récurrents nommés à l'identique. Langue : celle du projet (`"langue"` de `projet.json`).
- **Jamais les paroles dans un prompt**, ni documents, écrans ou pancartes (faux texte). Aucune célébrité ni personne
  réelle.

### Modifier le code
- Python 3.10+ (testé en 3.12), dans `.venv`. Dépendances figées dans `requirements.txt`.
- **Après toute modification : `python -m unittest`** (tests dans `tests/`, moins de 2 s). Ajouter un test pour tout
  bug de logique corrigé.
- **Bilingue** : tout texte visible existe en français et en anglais : `tr("français", "English")` (Python, `app.js`),
  `tp(cfg, …)` pour ce qui dépend de la langue du projet, `call :msg "…" "…"` (`.bat`), `m "…" "…"` (`.sh`). Toute
  page de documentation existe en `.md` (français) et `.en.md` (anglais) : **modifier les deux**. Voir TECHNIQUE.md,
  « Langues ». Français : typographie québécoise (pas d'espace avant `;` `?` `!`).
- **Garder le code portable** Windows / Linux / macOS : pas de `os.startfile`, `explorer`, chemins `.exe` ou polices
  Windows sans repli, ni `/tmp` codé en dur; chemins avec `pathlib`, relatifs au projet (voir TECHNIQUE.md,
  « Portabilité »).
- **Claude n'est appelé que sur action de l'utilisateur** (sauf l'évaluation dans « Préparer ») : ne jamais ajouter
  d'appel automatique.
- Nouvelle commande utilisable depuis l'interface : l'ajouter à `COMMANDS` / `ARG_VALUES` dans `clip/web.py`.
- Sortie vidéo : H.264 `yuv420p`, 30 fps, 1920×1080, audio AAC 192k muxé, `-movflags +faststart`, dimensions paires.
- Toute fonction nouvelle ou modifiée : mettre à jour GUIDE.md (si visible pour l'utilisateur), TECHNIQUE.md et la
  section « Non publié » de [CHANGELOG.md](CHANGELOG.md), ainsi que leurs versions anglaises.
- Le serveur garde l'ancien code en mémoire : après une modification Python, relancer Clip Studio.

## English

Clip Studio makes illustrated music videos: each line of a song gets its image, the lyrics are shown as word-by-word
karaoke, the edit follows the beats. The user generates the images themselves from the prompts prepared by Clip
Studio.

**To read**: [docs/GUIDE.en.md](docs/GUIDE.en.md) (usage, troubleshooting) and
[docs/TECHNIQUE.en.md](docs/TECHNIQUE.en.md) (architecture, commands, `projet.json`, conventions). The code (names,
`projet.json` keys, comments) is in French. Don't assume a system: Clip Studio runs on Windows, Linux and macOS
(experimental); check with the user or in the environment.

### Helping the user
- They work mostly in the interface (`Clip Studio.bat` / `./clip-studio.sh` / `Clip Studio.command`). Point them to the
  step and the button rather than a command, unless they prefer the command line (`python -m clip <command>
  <project>`, from the `.venv`).
- **Don't run the steps for them** (prepare, render, publishing) unless they ask: they validate each step
  (descriptions → panels → preview → final render).
- Problem: start with `python -m clip check`, then the "Troubleshooting" table of GUIDE.en.md and the command's log.
- If they paste the content of `build/a_decrire.md`, answer **only** with the requested JSON (`{"p1_c1": "Shot: … ;
  Subject: … ; Action: … ; Setting: … ; Lighting: …", …}`, or `Plan : … ; Sujet : … ; Action : … ; Décor : … ;
  Lumière : …` for a project in French), to be saved in `build/descriptions.json`.
- Answer in the user's language. The interface and the documentation exist in French and English.

### Panel rules (to follow in any description or prompt)
- Panels exist to **limit the number of generations**: 1 image per unique lyric line, packed into the fewest panels
  (2×3 grids in 32:27), 16:9 cells.
- Each description: **Shot; Subject; Action; Setting; Lighting**. The action **literally** illustrates the line, one
  single readable action. Recurring characters named identically. Language: the project's (`"langue"` in
  `projet.json`).
- **Never the lyrics in a prompt**, nor documents, screens or signs (fake text). No celebrity or real person.

### Changing the code
- Python 3.10+ (tested with 3.12), in `.venv`. Dependencies pinned in `requirements.txt`.
- **After any change: `python -m unittest`** (tests in `tests/`, under 2 s). Add a test for every logic bug fixed.
- **Bilingual**: every visible text exists in French and English: `tr("français", "English")` (Python, `app.js`),
  `tp(cfg, …)` for what depends on the project language, `call :msg "…" "…"` (`.bat`), `m "…" "…"` (`.sh`). Every
  documentation page exists as `.md` (French) and `.en.md` (English): **change both**. See TECHNIQUE.en.md,
  "Languages". French: Quebec typography (no space before `;` `?` `!`).
- **Keep the code portable** Windows / Linux / macOS: no `os.startfile`, `explorer`, `.exe` paths or Windows fonts
  without a fallback, no hard-coded `/tmp`; paths with `pathlib`, relative to the project (see TECHNIQUE.en.md,
  "Portability").
- **Claude is only called on user action** (except the evaluation in "Prepare"): never add an automatic call.
- New command usable from the interface: add it to `COMMANDS` / `ARG_VALUES` in `clip/web.py`.
- Video output: H.264 `yuv420p`, 30 fps, 1920×1080, AAC 192k audio muxed, `-movflags +faststart`, even dimensions.
- Any new or changed feature: update GUIDE (if visible to the user), TECHNIQUE and the "Unreleased" section of the
  changelog, in both languages.
- The server keeps the old code in memory: after a Python change, restart Clip Studio.
