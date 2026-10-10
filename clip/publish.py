"""Publication YouTube : titre, description (accroche, mention IA, chapitres, paroles), miniature.
Les chapitres, les paroles et la mention IA sont produits par le code (exacts) ; Claude ne rédige que
le titre, l'accroche, les hashtags et les prompts de miniature. Tout est dans la langue du projet (fr | en)."""
import json
import re

from .i18n import langue_projet
from .lyrics import SECTION_RE

SECTIONS = {
    "fr": {"verse": "Couplet", "couplet": "Couplet", "chorus": "Refrain", "refrain": "Refrain",
           "bridge": "Pont", "pont": "Pont", "outro": "Outro", "intro": "Intro",
           "pre-chorus": "Pré-refrain", "prechorus": "Pré-refrain", "solo": "Solo"},
    "en": {"verse": "Verse", "couplet": "Verse", "chorus": "Chorus", "refrain": "Chorus",
           "bridge": "Bridge", "pont": "Bridge", "outro": "Outro", "intro": "Intro",
           "pre-chorus": "Pre-chorus", "prechorus": "Pre-chorus", "solo": "Solo"},
}
MOTS = {  # libellés produits par le code
    "fr": {"instrumental": "Instrumental", "partie": "Partie", "fin": "Fin", "sans_titre": "Sans titre",
           "artiste": "Artiste", "aucun": "(aucun)", "non_precisee": "(non précisée)",
           "a_propos": "⚠️ À PROPOS DE CETTE VERSION", "chapitres": "⏱️ Chapitres", "paroles": "📝 Paroles",
           "droits": "paroles et musique originales.", "consigne": "Consigne de l'utilisateur"},
    "en": {"instrumental": "Instrumental", "partie": "Part", "fin": "End", "sans_titre": "Untitled",
           "artiste": "Artist", "aucun": "(none)", "non_precisee": "(not specified)",
           "a_propos": "⚠️ ABOUT THIS VERSION", "chapitres": "⏱️ Chapters", "paroles": "📝 Lyrics",
           "droits": "original lyrics and music.", "consigne": "User instruction"},
}

ORIGINES = {
    "fr": {
        "suno": ("Version IA",
                 "« {titre} » est une chanson originale de {artiste} : paroles et composition écrites par le groupe, "
                 "sans IA.\nCette version-ci a été réinterprétée avec Suno (IA) à partir de la chanson originale, et "
                 "toutes les images du clip ont été créées avec l'intelligence artificielle. Les personnages de la "
                 "vidéo sont fictifs et ne représentent aucune personne réelle."),
        "images": ("Clip IA",
                   "Musique et paroles originales de {artiste}, sans IA.\nLes images du clip ont été créées avec "
                   "l'intelligence artificielle; les personnages sont fictifs et ne représentent aucune personne "
                   "réelle."),
        "complete": ("Version IA",
                     "La musique, la voix et les images de ce clip ont été créées avec l'intelligence artificielle. "
                     "Les personnages sont fictifs et ne représentent aucune personne réelle."),
    },
    "en": {
        "suno": ("AI Version",
                 "\"{titre}\" is an original song by {artiste}: lyrics and music written by the band, without AI.\n"
                 "This version was reinterpreted with Suno (AI) from the original song, and all the images of the "
                 "video were created with artificial intelligence. The characters in the video are fictional and do "
                 "not depict any real person."),
        "images": ("AI Video",
                   "Original music and lyrics by {artiste}, without AI.\nThe images of the video were created with "
                   "artificial intelligence; the characters are fictional and do not depict any real person."),
        "complete": ("AI Version",
                     "The music, the vocals and the images of this video were created with artificial intelligence. "
                     "The characters are fictional and do not depict any real person."),
    },
}

DEMANDE = {
    "fr": """Tu prépares la publication YouTube d'un clip musical.
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
"miniature_sans_texte": "…"}}.{consigne}""",
    "en": """You are preparing the YouTube release of a music video.
Song: "{titre}" — artist: {artiste}
Origin: {origine}
Visual style of the video: {style}
Author's intent (mood, meaning, context — to respect): {intention}
Characters in the video (fictional): {pers}

Lyrics:
{paroles}

Write in English:
- "titre": YouTube title of 90 characters maximum, starting exactly with "{artiste} – {titre} ({mention})",
  optionally followed by "|" and a short complement (e.g. "Official lyric video").
- "accroche": 2 to 3 sentences that make people want to listen, in the tone of the song.
- "hashtags": list of 5 to 7 relevant hashtags (with #), including #{artiste_tag} and #{mention_tag}.
- "miniature": complete prompt to generate a photorealistic 16:9 YouTube thumbnail: the most striking scene of the
  video's world, characters described precisely (fictional, no real person, no celebrity), high contrast; left half
  darker and clear for the text; text in thick capital letters, readable and correctly spelled, exactly:
  "{titre_maj}" huge at the top left, "{artiste_maj}" just below, "{mention_maj}" in a bright red banner at the bottom
  left; no other text, no logo, no watermark.
- "miniature_sans_texte": the same prompt, but without any text in the image (left half left clear).
Answer ONLY with a JSON {{"titre": "…", "accroche": "…", "hashtags": ["#…"], "miniature": "…",
"miniature_sans_texte": "…"}}.{consigne}""",
}


def _ts(t):
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def chapitres(segments, duree, min_len=10.0, langue="fr"):
    """Chapitres YouTube : 1er à 0:00, sections chantées + passages instrumentaux ≥ 10 s,
    chaque chapitre dure au moins 10 s (sinon fusionné avec le précédent)."""
    noms, mots = SECTIONS[langue], MOTS[langue]
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
            marks.append([prev_end, mots["instrumental"]])
            prev_sec = None
        if sec != prev_sec:
            base = noms.get(sec.split()[0].lower() if sec else "", sec or mots["partie"])
            if base == noms["verse"]:
                count[base] = count.get(base, 0) + 1
                name = f"{base} {count[base]}"
            else:
                name = base
            marks.append([s["start"] if marks else 0.0, name])
            prev_sec = sec
        prev_end = s["end"]
    if duree - prev_end >= min_len:
        marks.append([prev_end, "Outro" if marks[-1][1] != "Outro" else mots["fin"]])
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


def _base(cfg):
    lg = langue_projet(cfg)
    m = MOTS[lg]
    titre, artiste = cfg.get("titre") or m["sans_titre"], cfg.get("artiste") or m["artiste"]
    mention, origine = ORIGINES[lg].get(cfg.get("origine", "suno"), ORIGINES[lg]["suno"])
    return lg, m, titre, artiste, mention, origine.format(titre=titre, artiste=artiste)


def demande(cfg, paroles, consigne=""):
    lg, m, titre, artiste, mention, origine = _base(cfg)
    pers = "; ".join(f"{k} = {v}" for k, v in (cfg.get("personnages") or {}).items()) or m["aucun"]
    tag = lambda s: "".join(w[:1].upper() + w[1:] for w in re.sub(r"[^\w\s]", "", s).split())
    return DEMANDE[lg].format(
        titre=titre, artiste=artiste, mention=mention, origine=origine,
        style=cfg.get("style", ""), pers=pers, paroles=paroles,
        intention=(cfg.get("intention") or m["non_precisee"]).strip(),
        artiste_tag=tag(artiste), mention_tag=tag(mention),
        titre_maj=titre.upper(), artiste_maj=artiste.upper(), mention_maj=mention.upper(),
        consigne=f"\n{m['consigne']} : {consigne}" if consigne else "")


def description(cfg, ia, chaps, paroles):
    lg, m, titre, artiste, mention, origine = _base(cfg)
    guill = f"« {titre} »" if lg == "fr" else f"\"{titre}\""
    parts = [f"🎵 {artiste} – {guill} ({mention})", "", ia.get("accroche", "").strip(), "", m["a_propos"], origine]
    if chaps:
        parts += ["", m["chapitres"], *chaps]
    parts += ["", f"{m['paroles']} ({artiste})", paroles]
    if cfg.get("origine", "suno") != "complete":
        parts += ["", f"© {artiste} — {m['droits']}"]
    tags = ia.get("hashtags") or []
    if tags:
        parts += ["", " ".join(t if t.startswith("#") else f"#{t}" for t in tags)]
    return "\n".join(parts).strip() + "\n"


def markdown(pub, langue="fr"):
    t = {"fr": ("Publication YouTube", "Titre", "Miniature (avec texte)", "Miniature (sans texte)"),
         "en": ("YouTube release", "Title", "Thumbnail (with text)", "Thumbnail (without text)")}[langue]
    return (f"# {t[0]}\n\n## {t[1]}\n```\n{pub['titre']}\n```\n\n## Description\n```\n"
            f"{pub['description']}```\n\n## {t[2]}\n```\n{pub['miniature']}\n```\n\n"
            f"## {t[3]}\n```\n{pub['miniature_sans_texte']}\n```\n")


def save(build_dir, pub, langue="fr"):
    (build_dir / "publication.json").write_text(json.dumps(pub, indent=1, ensure_ascii=False), encoding="utf-8")
    (build_dir / "publication.md").write_text(markdown(pub, langue), encoding="utf-8")
