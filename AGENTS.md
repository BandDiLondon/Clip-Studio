# Instructions pour Claude — Pipeline de clips musicaux illustrés

## Projet
Création de clips musicaux : chaque vers illustré par une case d'image, karaoké mot-à-mot,
zoom lent + pulse/flash au beat, travelling sur panoramique pendant les solos.
Méthode complète : [METHODE_CREATION_CLIP.md](METHODE_CREATION_CLIP.md).
Feuille de route : [PLAN_AMELIORATION.md](PLAN_AMELIORATION.md).

## Environnement
- Windows 11, PowerShell. Python 3.12 dans `.venv` → `.\.venv\Scripts\python.exe`.
- Point d'entrée : `Clip Studio.bat` (interface web locale, `clip/web.py` + `clip/web/index.html`),
  `Clip.bat` (menu texte) ou `python -m clip <commande>`
  (liste complète : METHODE §2). Installation sur un autre PC : `Installer.bat`.
- Clip Studio appelle Claude Code (`clip/ai.py`, abonnement, sans API) pour les descriptions, l'évaluation,
  les solos, les vidéos et la publication, **uniquement sur clic** (sauf l'évaluation dans « Préparer »).
  Ne jamais ajouter d'appel automatique à Claude sans demande. Rôle de Claude en
  session : seulement si l'utilisateur colle `build/a_decrire.md` (répondre par le JSON) ou en cas de problème. Ne pas lancer les étapes à la place
  de l'utilisateur ni inspecter les images sans demande (économie de tokens).
- ffmpeg 8 (build gyan, dans le PATH) : libx264, h264_amf (GPU AMD RX 9070 XT), filtres `ass`, `xfade`.
- Police karaoké par défaut : `C:\Windows\Fonts\arialbd.ttf`.
- `legacy/` = anciens scripts Linux (référence seulement, ne pas exécuter tels quels).
- Un projet = `projets/<nom>/` (chanson.mp3, paroles.txt, projet.json, planches/, cases/, solos/, retouches/,
  videos/, build/).
- Chemins toujours relatifs au projet (`pathlib`), jamais `/tmp` ni chemins absolus Linux.

## Standards de sortie (sauf indication contraire)
- 1920×1080, **30 fps**, H.264 `yuv420p`, CRF 20 (libx264 preset `fast`) ou h264_amf.
- Audio AAC 192k **muxé dans le rendu** + `-movflags +faststart`.
- Dimensions paires : `scale=trunc(iw/2)*2:trunc(ih/2)*2`.
- Aperçu : 960×540, 15 fps, preset `ultrafast`.

## Règles de rédaction
- **Toujours répondre en français**, y compris les messages intermédiaires.
- Pas de civilités, introduction ni conclusion. Réponses courtes.
- Pour une commande ou un script demandé : le code seul, 1 ligne d'explication max.
- Pour une analyse, un plan ou un choix de méthode : répondre normalement, de façon structurée.
- Données manquantes (chemins, durées) : variables claires (`input.jpg`, `output.mp4`), ne pas deviner.

## Règles de travail
- Validation de l'utilisateur à chaque étape : plan → planches → aperçu → rendu final.
- Planches = économie de générations : **1 image par vers unique**, minimum de planches (2×3 en 32:27),
  vignettes **16:9**, chaque vignette décrite strictement (Plan ; Sujet ; Action ; Décor ; Lumière),
  paroles jamais citées dans le prompt, aucun texte ni numéro (modèle : METHODE §3).
- Vérifier (analyse d'image) chaque planche et miniature avant de continuer.
- Hébergement (catbox) uniquement sur demande explicite.
- Après toute modification du code : `.\.venv\Scripts\python.exe -m unittest` (tests dans `tests/`), et ajouter un
  test quand on corrige un bug de logique (shotlist, paroles, montage, empreintes).
- Toute nouvelle fonction : mettre à jour METHODE (et PLAN si c'est une étape). Après une modification du code,
  rappeler que la copie GitHub (`../Clip-Studio-GitHub`) se synchronise avec `Mettre a jour depuis Clip FFMPEG.bat`.
