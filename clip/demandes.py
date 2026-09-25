"""Textes des demandes envoyées à Claude (Claude Code, abonnement) par les commandes de clip/cli.py.
Les autres demandes sont dans clip/evaluate.py (évaluation) et clip/publish.py (publication)."""

A_DECRIRE = """Rédige une description de scène pour chaque image ci-dessous (clip musical, 1 image = 1 vers).
Format : Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …
- Action = illustration LITTÉRALE du vers, une seule action lisible ; pas de texte, document, écran ni pancarte.
- Nommer les personnages récurrents exactement comme ci-dessous.{pers_todo}
Réponds UNIQUEMENT par un JSON {{"id": "description", …}} à enregistrer dans build/descriptions.json.

Style : {style}
Personnages : {pers}

{items}
"""


REFAIRE = """Réécris la description de scène de certaines images d'un clip musical (1 image = 1 vers).
Format : Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …
- Action = illustration LITTÉRALE du vers, une seule action lisible ; pas de texte, document, écran ni pancarte ;
  aucune célébrité ni personne réelle.
- Nommer les personnages récurrents exactement comme ci-dessous.
- Proposer une scène nettement différente de la description actuelle.{consigne}
Réponds UNIQUEMENT par un JSON {{"id": "description", …}}.

Style : {style}
Personnages : {pers}

{items}
"""


SOLOS = """Tu écris des prompts pour générer des images PANORAMIQUES destinées aux passages instrumentaux
d'un clip musical : la caméra glisse lentement de gauche à droite sur chaque image (travelling).
Chanson : « {titre} » — artiste : {artiste}
Style visuel : {style}
Personnages récurrents : {pers}
Passages sans paroles : {passages}
Paroles :
{paroles}

Écris {n} prompts, un par image, tous différents, liés à l'univers de la chanson (ex. musiciens en plein solo,
la scène vue de la foule, un lieu évoqué par les paroles, un moment clé de l'histoire).{consigne}
Chaque prompt doit préciser : format panoramique 21:9 très large (ex. 2016×864) ; composition étalée sur toute
la largeur, avec des éléments intéressants de gauche à droite (pas un seul sujet au centre) ; horizon et sujets
dans le tiers central en hauteur ; photoréaliste, dans le style visuel ci-dessus ; personnages récurrents décrits
à l'identique s'ils apparaissent ; aucun texte, aucune lettre, aucun logo, aucune enseigne lisible, aucune
célébrité ni personne réelle, aucun filigrane.
Réponds UNIQUEMENT par un JSON {{"solos": [{{"titre": "<3 à 6 mots>", "prompt": "<prompt complet>"}}, …]}}"""


VIDEOS = """Tu écris des prompts pour générer de courtes vidéos (image vers vidéo, ~10 s, Google Flow / Veo)
qui remplaceront des images fixes dans un clip musical. Chaque vidéo part de l'image indiquée (image de départ).
Chanson : « {titre} » — artiste : {artiste}
Style visuel : {style}
Personnages récurrents : {pers}

Images à animer (id — temps à l'écran — description de l'image) :
{items}

Pour CHAQUE image, écris un prompt EN ANGLAIS (Veo suit mieux l'anglais), qui commence par
« Image-to-video, 10 seconds, 16:9. », décrit brièvement la scène, puis précise :
- Camera : un seul mouvement de caméra clair et lent (dolly, travelling latéral, push-in, grue, caméra à l'épaule…) ;
- Action : 3 à 5 mouvements concrets et visibles des sujets et du décor, fidèles à la description et à l'image ;
- Atmosphère : lumière, fumée, météo qui bougent.
Termine chaque prompt par : « Keep every character, costume and element exactly as in the starting image; photorealistic,
cinematic film grain. No text, no titles, no subtitles, no logos, no watermark. No dialogue, no music (ambient sound only). »
Aucune célébrité ni personne réelle.{consigne}
Réponds UNIQUEMENT par un JSON {{"videos": [{{"id": "<id>", "titre": "<3 à 6 mots en français>", "prompt": "<prompt>"}}, …]}}"""
