# Instructions pour les assistants IA (Claude Code, Codex, Cursor…)

Clip Studio fabrique des clips musicaux illustrés : chaque vers d'une chanson a son image, les paroles s'affichent en
karaoké mot à mot, le montage suit les beats. L'utilisateur génère lui-même les images à partir des prompts préparés
par Clip Studio.

**À lire** : [docs/GUIDE.md](docs/GUIDE.md) (utilisation, dépannage) et [docs/TECHNIQUE.md](docs/TECHNIQUE.md)
(architecture, commandes, `projet.json`, conventions). Ne pas supposer un système : Clip Studio tourne sous
Windows, sous Linux et sous macOS (expérimental) ; vérifier avec l'utilisateur ou dans l'environnement.

## Aider l'utilisateur
- Il travaille surtout dans l'interface (`Clip Studio.bat` / `./clip-studio.sh`). Indique-lui l'étape et le bouton
  plutôt qu'une commande, sauf s'il préfère la ligne de commande (`python -m clip <commande> <projet>`, depuis le `.venv`).
- **Ne lance pas les étapes à sa place** (préparation, rendu, publication) sans qu'il le demande : il valide à chaque
  étape (descriptions → planches → aperçu → rendu final).
- Problème : commence par `python -m clip check`, puis le tableau « Dépannage » de GUIDE.md et le journal de la commande.
- S'il colle le contenu de `build/a_decrire.md`, réponds **uniquement** par le JSON demandé (`{"p1_c1": "Plan : … ;
  Sujet : … ; Action : … ; Décor : … ; Lumière : …", …}`), à enregistrer dans `build/descriptions.json`.
- Réponds dans la langue de l'utilisateur. L'interface et la documentation sont en français.

## Règles des planches (à respecter dans toute description ou prompt)
- Les planches servent à **limiter le nombre de générations** : 1 image par vers unique, rangées dans le minimum de
  planches (grilles 2×3 en 32:27), vignettes 16:9.
- Chaque description : **Plan ; Sujet ; Action ; Décor ; Lumière**. L'action illustre **littéralement** le vers, une
  seule action lisible. Personnages récurrents nommés à l'identique.
- **Jamais les paroles dans un prompt**, ni documents, écrans ou pancartes (faux texte). Aucune célébrité ni personne réelle.

## Modifier le code
- Python 3.10+ (testé en 3.12), dans `.venv`. Dépendances figées dans `requirements.txt`.
- **Après toute modification : `python -m unittest`** (tests dans `tests/`, moins de 1 s). Ajouter un test pour tout
  bug de logique corrigé.
- **Garder le code portable** Windows / Linux / macOS : pas de `os.startfile`, `explorer`, chemins `.exe` ou polices Windows
  sans repli, ni `/tmp` codé en dur ; chemins avec `pathlib`, relatifs au projet (voir TECHNIQUE.md, « Portabilité »).
- **Claude n'est appelé que sur action de l'utilisateur** (sauf l'évaluation dans « Préparer ») : ne jamais ajouter
  d'appel automatique.
- Nouvelle commande utilisable depuis l'interface : l'ajouter à `COMMANDS` / `ARG_VALUES` dans `clip/web.py`.
- Sortie vidéo : H.264 `yuv420p`, 30 fps, 1920×1080, audio AAC 192k muxé, `-movflags +faststart`, dimensions paires.
- Toute fonction nouvelle ou modifiée : mettre à jour GUIDE.md (si visible pour l'utilisateur), TECHNIQUE.md et la
  section « Non publié » de [CHANGELOG.md](CHANGELOG.md).
- Le serveur garde l'ancien code en mémoire : après une modification Python, relancer Clip Studio.
