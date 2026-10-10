"""Évaluation du storyboard après « Préparer » : le code mesure (instrumentaux, temps d'écran, cases
libres), Claude recommande le nombre d'images d'ambiance, des idées de sujets et un préréglage."""
import json
import math

from .i18n import langue_projet
from .shots import _pack, key

GAP = 3.0            # trou sans paroles considéré comme instrumental
SEC_PAR_IMAGE = 6.0  # repère : une image fixe tient bien ~5-8 s à l'écran


def faits(segments, duree, lines, ambiance, solos, bpm):
    segs = [s for s in segments if s.get("start") is not None]
    trous, prev = [], 0.0
    for s in segs:
        if s["start"] - prev >= GAP:
            trous.append({"debut": round(prev, 1), "fin": round(s["start"], 1),
                          "duree": round(s["start"] - prev, 1), "type": "intro" if not trous and prev == 0 else "instrumental"})
        prev = s["end"]
    if duree - prev >= GAP:
        trous.append({"debut": round(prev, 1), "fin": round(duree, 1), "duree": round(duree - prev, 1), "type": "outro"})
    # temps d'écran par vers unique (vers affiché jusqu'au vers suivant, trous exclus)
    ecran = {}
    for i, s in enumerate(segs):
        fin = segs[i + 1]["start"] if i + 1 < len(segs) else s["end"] + 1
        fin = min(fin, s["end"] + GAP)
        k = key(s["text"])
        ecran.setdefault(k, {"vers": s["text"], "secondes": 0.0, "fois": 0})
        ecran[k]["secondes"] += fin - s["start"]
        ecran[k]["fois"] += 1
    uniques = len({key(t) for _, t in lines})
    instru = sum(t["duree"] for t in trous)
    total_actuel = uniques + ambiance
    planches = _pack(total_actuel)
    libres = sum(planches) - total_actuel
    return {
        "duree": round(duree, 1), "bpm": round(bpm, 1) if bpm else None,
        "vers": len(lines), "images_de_vers": uniques, "ambiance_actuelle": ambiance,
        "photos_de_solo": solos, "instrumental_total": round(instru, 1), "passages_sans_paroles": trous,
        "images_les_plus_longues": sorted(({"vers": v["vers"], "secondes": round(v["secondes"], 1),
                                            "fois": v["fois"]} for v in ecran.values()),
                                          key=lambda x: -x["secondes"])[:5],
        "planches_actuelles": len(planches), "cases_libres_derniere_planche": libres,
        "repere_images_instrumental": math.ceil(instru / SEC_PAR_IMAGE) if instru else 0,
    }


DEMANDE = {"fr": """Tu évalues le storyboard d'un clip musical avant la génération des images.
Principe : chaque vers unique a sa propre image ; les passages sans paroles (intro, instrumentaux, outro)
sont couverts par les photos de solo (travelling sur panoramique, si fournies) et par des images
d'« ambiance » que l'on ajoute au storyboard ; si les deux existent, elles alternent. Une photo de solo
tient ~8 s par passage ; avec assez de photos de solo, 0 image d'ambiance est une bonne réponse. Les images sont générées par planches de 6 : une planche
coûte une génération, donc remplir les cases libres de la dernière planche est gratuit, alors qu'en
dépasser une en coûte une de plus. La dernière planche s'adapte : 6 cases, ou 4, 2 ou 1 s'il en reste
moins (ex. 28 images = 4 planches de 6 + 1 planche de 4, sans case perdue ; 17 images = 3 planches, 1 case libre). Une image fixe tient bien environ 5 à 8 s à l'écran (avec mouvement de
caméra) ; au-delà de ~10 s elle lasse ; une image d'ambiance peut être réutilisée, mais pas trop souvent.

Chanson : « {titre} » — style visuel : {style}
Intention de l'auteur (ambiance, sens, contexte) : {intention}
Paroles :
{paroles}

Mesures (secondes) :
{faits}

Réponds UNIQUEMENT par un JSON :
{{"ambiance": <nombre TOTAL d'images d'ambiance que doit compter le storyboard, 0 à 12 (il remplace
   ambiance_actuelle, ce n'est pas un ajout) ; total d'images = images_de_vers + ambiance>,
 "raison": "<2-3 phrases : pourquoi ce nombre, en tenant compte des passages sans paroles, des photos de solo et des cases libres>",
 "idees_ambiance": ["<exactement une idée de scène courte par image d'ambiance (autant que le total), liée au thème de la chanson>", …],
 "preset": "<ballade | rock | sobre : l'énergie apparente de la chanson (tempo, paroles)>",
 "remarques": ["<0 à 3 remarques utiles pour le montage, ex. une image affichée trop longtemps>"]}}""",
           "en": """You evaluate the storyboard of a music video before the images are generated.
Principle: each unique lyric line has its own image; the parts without lyrics (intro, instrumentals, outro) are
covered by the solo photos (tracking shot over a panorama, if provided) and by "ambiance" images added to the
storyboard; if both exist, they alternate. A solo photo lasts ~8 s per part; with enough solo photos, 0 ambiance
image is a good answer. Images are generated in panels of 6: one panel costs one generation, so filling the free cells
of the last panel is free, while going past one costs one more. The last panel adapts: 6 cells, or 4, 2 or 1 if fewer
are left (e.g. 28 images = 4 panels of 6 + 1 panel of 4, no wasted cell; 17 images = 3 panels, 1 free cell). A still
image holds well for about 5 to 8 s on screen (with camera movement); beyond ~10 s it gets boring; an ambiance image
can be reused, but not too often.

Song: "{titre}" — visual style: {style}
Author's intent (mood, meaning, context): {intention}
Lyrics:
{paroles}

Measurements (seconds):
{faits}

Write the texts in English. Answer ONLY with a JSON:
{{"ambiance": <TOTAL number of ambiance images the storyboard must have, 0 to 12 (it replaces ambiance_actuelle,
   it is not an addition); total images = images_de_vers + ambiance>,
 "raison": "<2-3 sentences: why this number, considering the parts without lyrics, the solo photos and the free cells>",
 "idees_ambiance": ["<exactly one short scene idea per ambiance image (as many as the total), tied to the song's theme>", …],
 "preset": "<ballade | rock | sobre: the apparent energy of the song (tempo, lyrics)>",
 "remarques": ["<0 to 3 useful remarks for the edit, e.g. an image shown for too long>"]}}"""}


def demande(cfg, paroles, f):
    en = langue_projet(cfg) == "en"
    return DEMANDE[langue_projet(cfg)].format(
        titre=cfg.get("titre") or ("(untitled)" if en else "(sans titre)"), style=cfg.get("style", ""),
        intention=(cfg.get("intention") or ("(not specified)" if en else "(non précisée)")).strip(),
        paroles=paroles, faits=json.dumps(f, ensure_ascii=False, indent=1))
