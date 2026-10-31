"""Textes des demandes envoyées à Claude (Claude Code, abonnement) par les commandes de clip/cli.py, dans la langue du
projet (« langue » : fr | en). Les autres demandes sont dans clip/evaluate.py (évaluation) et clip/publish.py
(publication)."""

A_DECRIRE = {
    "fr": """Rédige une description de scène pour chaque image ci-dessous (clip musical, 1 image = 1 vers).
Format : Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …
- Action = illustration LITTÉRALE du vers, une seule action lisible ; pas de texte, document, écran ni pancarte.
- Nommer les personnages récurrents exactement comme ci-dessous.{pers_todo}
Réponds UNIQUEMENT par un JSON {{"id": "description", …}} à enregistrer dans build/descriptions.json.

Style : {style}
Personnages : {pers}

{items}
""",
    "en": """Write a scene description for each image below (music video, 1 image = 1 lyric line).
Format: Shot: … ; Subject: … ; Action: … ; Setting: … ; Lighting: …
- Action = LITERAL illustration of the line, one single readable action; no text, document, screen or sign.
- Name the recurring characters exactly as below.{pers_todo}
Answer ONLY with a JSON {{"id": "description", …}} to be saved in build/descriptions.json.

Style: {style}
Characters: {pers}

{items}
""",
}


A_DECRIRE_INSTRU = {
    "fr": """Rédige une description pour chaque image abstraite ci-dessous (clip d'une pièce instrumentale : les images
changent sur le beat, plus vite dans les passages intenses).
Format : Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …
(Plan = cadrage et échelle ; Sujet = formes et matières ; Action = mouvement figé ; Décor = fond et profondeur ;
Lumière = couleurs et éclairage.)
- Images ABSTRAITES seulement : aucune personne, aucun visage, aucun animal, aucun objet reconnaissable, aucun texte.
- Une seule direction visuelle pour tout le clip (même famille de matières et de formes), qui varie avec l'énergie :
  calme = formes lentes, beaucoup d'espace, couleurs sourdes ou froides ; modéré = formes en mouvement, contrastes
  moyens ; intense = formes éclatées, contrastes forts, couleurs saturées, impression d'explosion ou de vitesse.
- Toutes les images nettement différentes (formes, cadrage, couleur dominante) : les coupes doivent se voir.{style_todo}{consigne}
Réponds UNIQUEMENT par un JSON {{"id": "description", …}} à enregistrer dans build/descriptions.json.

Style : {style}

{items}
""",
    "en": """Write a description for each abstract image below (video for an instrumental piece: the images change on
the beat, faster in the intense parts).
Format: Shot: … ; Subject: … ; Action: … ; Setting: … ; Lighting: …
(Shot = framing and scale; Subject = shapes and materials; Action = frozen motion; Setting = background and depth;
Lighting = colors and lighting.)
- ABSTRACT images only: no person, no face, no animal, no recognizable object, no text.
- One single visual direction for the whole video (same family of materials and shapes), varying with the energy:
  calm = slow shapes, lots of space, muted or cold colors; moderate = moving shapes, medium contrast; intense =
  bursting shapes, strong contrast, saturated colors, a sense of explosion or speed.
- All images clearly different (shapes, framing, dominant color): the cuts must show.{style_todo}{consigne}
Answer ONLY with a JSON {{"id": "description", …}} to be saved in build/descriptions.json.

Style: {style}

{items}
""",
}

REFAIRE_INSTRU = {
    "fr": """Réécris la description de certaines images abstraites d'un clip instrumental (les images changent sur le beat).
Format : Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …
- Images ABSTRAITES seulement : aucune personne, aucun visage, aucun animal, aucun objet reconnaissable, aucun texte.
- Garder la direction visuelle du clip et l'énergie indiquée; proposer une composition nettement différente de la
  description actuelle.{consigne}
Réponds UNIQUEMENT par un JSON {{"id": "description", …}}.

Style : {style}

{items}
""",
    "en": """Rewrite the description of some abstract images of an instrumental video (the images change on the beat).
Format: Shot: … ; Subject: … ; Action: … ; Setting: … ; Lighting: …
- ABSTRACT images only: no person, no face, no animal, no recognizable object, no text.
- Keep the video's visual direction and the given energy; propose a composition clearly different from the current
  description.{consigne}
Answer ONLY with a JSON {{"id": "description", …}}.

Style: {style}

{items}
""",
}

REFAIRE = {
    "fr": """Réécris la description de scène de certaines images d'un clip musical (1 image = 1 vers).
Format : Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …
- Action = illustration LITTÉRALE du vers, une seule action lisible ; pas de texte, document, écran ni pancarte ;
  aucune célébrité ni personne réelle.
- Nommer les personnages récurrents exactement comme ci-dessous.
- Proposer une scène nettement différente de la description actuelle.{consigne}
Réponds UNIQUEMENT par un JSON {{"id": "description", …}}.

Style : {style}
Personnages : {pers}

{items}
""",
    "en": """Rewrite the scene description of some images of a music video (1 image = 1 lyric line).
Format: Shot: … ; Subject: … ; Action: … ; Setting: … ; Lighting: …
- Action = LITERAL illustration of the line, one single readable action; no text, document, screen or sign;
  no celebrity or real person.
- Name the recurring characters exactly as below.
- Propose a scene clearly different from the current description.{consigne}
Answer ONLY with a JSON {{"id": "description", …}}.

Style: {style}
Characters: {pers}

{items}
""",
}


SOLOS = {
    "fr": """Tu écris des prompts pour générer des images PANORAMIQUES destinées aux passages instrumentaux
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
Réponds UNIQUEMENT par un JSON {{"solos": [{{"titre": "<3 à 6 mots>", "prompt": "<prompt complet>"}}, …]}}""",
    "en": """You write prompts to generate PANORAMIC images for the instrumental parts of a music video: the camera
slowly glides from left to right across each image (tracking shot).
Song: "{titre}" — artist: {artiste}
Visual style: {style}
Recurring characters: {pers}
Parts without lyrics: {passages}
Lyrics:
{paroles}

Write {n} prompts, one per image, all different, tied to the world of the song (e.g. musicians in the middle of a solo,
the stage seen from the crowd, a place mentioned in the lyrics, a key moment of the story).{consigne}
Each prompt must state: very wide 21:9 panoramic format (e.g. 2016×864); composition spread across the whole width,
with interesting elements from left to right (not a single subject in the center); horizon and subjects in the
middle third vertically; photorealistic, in the visual style above; recurring characters described identically if
they appear; no text, no letters, no logo, no readable sign, no celebrity or real person, no watermark.
Answer ONLY with a JSON {{"solos": [{{"titre": "<3 to 6 words>", "prompt": "<complete prompt>"}}, …]}}""",
}


VIDEOS = {
    "fr": """Tu écris des prompts pour générer de courtes vidéos (image vers vidéo, ~10 s, Google Flow / Veo)
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
Réponds UNIQUEMENT par un JSON {{"videos": [{{"id": "<id>", "titre": "<3 à 6 mots en français>", "prompt": "<prompt>"}}, …]}}""",
    "en": """You write prompts to generate short videos (image to video, ~10 s, Google Flow / Veo) that will replace
still images in a music video. Each video starts from the given image (starting image).
Song: "{titre}" — artist: {artiste}
Visual style: {style}
Recurring characters: {pers}

Images to animate (id — screen time — image description):
{items}

For EACH image, write a prompt IN ENGLISH that starts with "Image-to-video, 10 seconds, 16:9.", briefly describes the
scene, then specifies:
- Camera: one single clear and slow camera move (dolly, lateral tracking, push-in, crane, handheld…);
- Action: 3 to 5 concrete, visible movements of the subjects and the setting, faithful to the description and image;
- Atmosphere: moving light, smoke, weather.
End each prompt with: "Keep every character, costume and element exactly as in the starting image; photorealistic,
cinematic film grain. No text, no titles, no subtitles, no logos, no watermark. No dialogue, no music (ambient sound only)."
No celebrity or real person.{consigne}
Answer ONLY with a JSON {{"videos": [{{"id": "<id>", "titre": "<3 to 6 words>", "prompt": "<prompt>"}}, …]}}""",
}
