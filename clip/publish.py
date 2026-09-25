"""Publication YouTube : titre, description (accroche, mention IA, chapitres, paroles), miniature.
Les chapitres, les paroles et la mention IA sont produits par le code (exacts) ; Claude ne rédige que
le titre, l'accroche, les hashtags et les prompts de miniature."""
import json
import re

from .lyrics import SECTION_RE

SECTIONS_FR = {"verse": "Couplet", "couplet": "Couplet", "chorus": "Refrain", "refrain": "Refrain",
               "bridge": "Pont", "pont": "Pont", "outro": "Outro", "intro": "Intro",
               "pre-chorus": "Pré-refrain", "prechorus": "Pré-refrain", "solo": "Solo"}

ORIGINES = {
    "suno": ("Version IA",
             "« {titre} » est une chanson originale de {artiste} : paroles et composition écrites par le groupe, "
             "sans IA.\nCette version-ci a été réinterprétée avec Suno (IA) à partir de la chanson originale, et "
             "toutes les images du clip ont été créées avec l'intelligence artificielle. Les personnages de la "
             "vidéo sont fictifs et ne représentent aucune personne réelle."),
    "images": ("Clip IA",
               "Musique et paroles originales de {artiste}, sans IA.\nLes images du clip ont été créées avec "
               "l'intelligence artificielle ; les personnages sont fictifs et ne représentent aucune personne réelle."),
    "complete": ("Version IA",
                 "La musique, la voix et les images de ce clip ont été créées avec l'intelligence artificielle. "
                 "Les personnages sont fictifs et ne représentent aucune personne réelle."),
}

DEMANDE = """Tu prépares la publication YouTube d'un clip musical.
Chanson : « {titre} » — artiste : {artiste}
Origine : {origine}
Style visuel du clip : {style}
Intention de l'auteur (ambiance, sens, contexte — à respecter) : {intention}
Personnages du clip (fictifs) : {pers}

Paroles :
{paroles}

Rédige en français (le québécois familier est bienvenu si la chanson l'est) :
- "titre" : titre YouTube de 90 caractères maximum, qui commence exactement par « {artiste} – {titre} ({mention}) »,
  suivi éventuellement de « | » et d'un complément court (ex. « Clip officiel avec paroles »).
- "accroche" : 2 à 3 phrases qui donnent envie d'écouter, dans le ton de la chanson.
- "hashtags" : liste de 5 à 7 hashtags pertinents (avec #), dont #{artiste_tag} et #{mention_tag}.
- "miniature" : prompt complet pour générer une miniature YouTube 16:9 photoréaliste : la scène la plus
  marquante de l'univers du clip, personnages décrits précisément (fictifs, aucune personne réelle, aucune
  célébrité), contraste élevé ; moitié gauche plus sombre et dégagée pour le texte ; texte en lettres capitales
  épaisses, lisibles et correctement orthographiées, exactement : « {titre_maj} » énorme en haut à gauche,
  « {artiste_maj} » juste en dessous, « {mention_maj} » dans un bandeau rouge vif en bas à gauche ;
  aucun autre texte, aucun logo, aucun filigrane.
- "miniature_sans_texte" : le même prompt, mais sans aucun texte dans l'image (moitié gauche laissée libre).
Réponds UNIQUEMENT par un JSON {{"titre": "…", "accroche": "…", "hashtags": ["#…"], "miniature": "…",
"miniature_sans_texte": "…"}}.{consigne}"""


def _ts(t):
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def chapitres(segments, duree, min_len=10.0):
    """Chapitres YouTube : 1er à 0:00, sections chantées + passages instrumentaux ≥ 10 s,
    chaque chapitre dure au moins 10 s (sinon fusionné avec le précédent)."""
    segs = [s for s in segments if s.get("start") is not None]
    marks, count = [], {}
    if not segs or segs[0]["start"] > min_len:
        marks.append([0.0, "Intro"])
    prev_sec, prev_end = None, 0.0
    for s in segs:
        sec = (s.get("section") or "").strip()
        # pause longue entre deux sections différentes = passage instrumental
        # (une pause au milieu d'une même section ne coupe pas le chapitre)
        if marks and s["start"] - prev_end >= min_len and prev_sec is not None and sec != prev_sec:
            marks.append([prev_end, "Instrumental"])
            prev_sec = None
        if sec != prev_sec:
            base = SECTIONS_FR.get(sec.split()[0].lower() if sec else "", sec or "Partie")
            if base == "Couplet":
                count[base] = count.get(base, 0) + 1
                name = f"Couplet {count[base]}"
            else:
                name = base
            marks.append([s["start"] if marks else 0.0, name])
            prev_sec = sec
        prev_end = s["end"]
    if duree - prev_end >= min_len:
        marks.append([prev_end, "Outro" if marks[-1][1] != "Outro" else "Fin"])
    marks[0][0] = 0.0
    out = []
    for t, name in marks:                              # durée minimale : fusion avec le précédent
        if out and t - out[-1][0] < min_len:
            continue
        out.append([t, name])
    while len(out) > 1 and duree - out[-1][0] < min_len:
        out.pop()
    return [f"{_ts(t)} {name}" for t, name in out] if len(out) >= 3 else []


def paroles_propres(texte):
    """Paroles sans en-têtes [Section], une seule ligne vide entre les blocs."""
    lines = [l.rstrip() for l in texte.splitlines() if not SECTION_RE.match(l)]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return re.sub(r"\s+,", ",", out)


def demande(cfg, paroles, consigne=""):
    titre, artiste = cfg.get("titre") or "Sans titre", cfg.get("artiste") or "Artiste"
    mention, origine = ORIGINES.get(cfg.get("origine", "suno"), ORIGINES["suno"])
    pers = "; ".join(f"{k} = {v}" for k, v in (cfg.get("personnages") or {}).items()) or "(aucun)"
    tag = lambda s: "".join(w[:1].upper() + w[1:] for w in re.sub(r"[^\w\s]", "", s).split())
    return DEMANDE.format(
        titre=titre, artiste=artiste, mention=mention, origine=origine.format(titre=titre, artiste=artiste),
        style=cfg.get("style", ""), pers=pers, paroles=paroles,
        intention=(cfg.get("intention") or "(non précisée)").strip(),
        artiste_tag=tag(artiste), mention_tag=tag(mention),
        titre_maj=titre.upper(), artiste_maj=artiste.upper(), mention_maj=mention.upper(),
        consigne=f"\nConsigne de l'utilisateur : {consigne}" if consigne else "")


def description(cfg, ia, chaps, paroles):
    titre, artiste = cfg.get("titre") or "Sans titre", cfg.get("artiste") or "Artiste"
    mention, origine = ORIGINES.get(cfg.get("origine", "suno"), ORIGINES["suno"])
    parts = [f"🎵 {artiste} – « {titre} » ({mention})", "", ia.get("accroche", "").strip(), "",
             "⚠️ À PROPOS DE CETTE VERSION", origine.format(titre=titre, artiste=artiste)]
    if chaps:
        parts += ["", "⏱️ Chapitres", *chaps]
    parts += ["", f"📝 Paroles ({artiste})", paroles]
    if cfg.get("origine", "suno") != "complete":
        parts += ["", f"© {artiste} — paroles et musique originales."]
    tags = ia.get("hashtags") or []
    if tags:
        parts += ["", " ".join(t if t.startswith("#") else f"#{t}" for t in tags)]
    return "\n".join(parts).strip() + "\n"


def markdown(pub):
    return (f"# Publication YouTube\n\n## Titre\n```\n{pub['titre']}\n```\n\n## Description\n```\n"
            f"{pub['description']}```\n\n## Miniature (avec texte)\n```\n{pub['miniature']}\n```\n\n"
            f"## Miniature (sans texte)\n```\n{pub['miniature_sans_texte']}\n```\n")


def save(build_dir, pub):
    (build_dir / "publication.json").write_text(json.dumps(pub, indent=1, ensure_ascii=False), encoding="utf-8")
    (build_dir / "publication.md").write_text(markdown(pub), encoding="utf-8")
