"""Évaluation du storyboard après « Préparer » : le code mesure (instrumentaux, temps d'écran, cases
libres), Claude recommande le nombre d'images d'ambiance, des idées de sujets et un préréglage."""
import json
import math

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


DEMANDE = """Tu évalues le storyboard d'un clip musical avant la génération des images.
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
 "remarques": ["<0 à 3 remarques utiles pour le montage, ex. une image affichée trop longtemps>"]}}"""


def demande(cfg, paroles, f):
    return DEMANDE.format(titre=cfg.get("titre") or "(sans titre)", style=cfg.get("style", ""),
                          intention=(cfg.get("intention") or "(non précisée)").strip(),
                          paroles=paroles, faits=json.dumps(f, ensure_ascii=False, indent=1))
