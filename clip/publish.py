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
           "droits": "paroles et musique originales.", "droits_instru": "musique originale.",
           "droits_fan": "tous droits réservés à l'artiste et à ses ayants droit.", "consigne": "Consigne de l'utilisateur",
           "credits": "🎬 Crédits", "liens": "🔗 Liens", "officiel": "Chanson officielle",
           "fait_avec": "Clip réalisé avec Clip Studio",
           "roles": {"paroles": "Paroles", "musique": "Musique", "interpretation": "Interprétation", "clip": "Clip"}},
    "en": {"instrumental": "Instrumental", "partie": "Part", "fin": "End", "sans_titre": "Untitled",
           "artiste": "Artist", "aucun": "(none)", "non_precisee": "(not specified)",
           "a_propos": "⚠️ ABOUT THIS VERSION", "chapitres": "⏱️ Chapters", "paroles": "📝 Lyrics",
           "droits": "original lyrics and music.", "droits_instru": "original music.",
           "droits_fan": "all rights reserved to the artist and their rights holders.", "consigne": "User instruction",
           "credits": "🎬 Credits", "liens": "🔗 Links", "officiel": "Official song",
           "fait_avec": "Video made with Clip Studio",
           "roles": {"paroles": "Lyrics", "musique": "Music", "interpretation": "Performance", "clip": "Video"}},
}

CLIP_STUDIO_URL = "https://github.com/BandDiLondon/Clip-Studio"
# options de l'étape 8 (« publication » dans projet.json) et leurs valeurs par défaut
REGLAGES = {
    "credits": {"paroles": "", "musique": "", "interpretation": "", "clip": ""},
    "clip_studio": False, "liens": "", "lien_officiel": "",
    "ton": "auto", "accroche": "normale", "emojis": True,
    "blocs": {"accroche": True, "mention": True, "chapitres": True, "paroles": True,
              "credits": True, "liens": True, "hashtags": True},
    "vignette": None, "bandeau": "", "bandeau_couleur": "rouge", "formats": [],
}
TONS = {
    "fr": {"drole": "drôle et décalé", "serieux": "sérieux et sobre", "promo": "accrocheur, façon promo",
           "quebecois": "québécois familier"},
    "en": {"drole": "funny and quirky", "serieux": "serious and sober", "promo": "catchy, promotional",
           "quebecois": "casual and colloquial"},
}
COULEURS = {
    "fr": {"rouge": "rouge vif", "jaune": "jaune vif", "noir": "noir", "blanc": "blanc", "bleu": "bleu électrique"},
    "en": {"rouge": "bright red", "jaune": "bright yellow", "noir": "black", "blanc": "white", "bleu": "electric blue"},
}
FORMATS = {
    "fr": {"carre": "la même idée en miniature carrée 1:1 (Instagram, Facebook), même texte placé en haut, sujet centré",
           "vertical": "la même idée en format vertical 9:16 (Shorts, TikTok, Reels), même texte placé en haut, "
                       "sujet dans le tiers central"},
    "en": {"carre": "the same idea as a square 1:1 thumbnail (Instagram, Facebook), same text placed at the top, "
                    "subject centered",
           "vertical": "the same idea in vertical 9:16 format (Shorts, TikTok, Reels), same text placed at the top, "
                       "subject in the middle third"},
}


def reglages(cfg):
    """Options de publication du projet complétées par les valeurs par défaut."""
    pub = cfg.get("publication") or {}
    r = {**REGLAGES, **pub}
    for k in ("credits", "blocs"):
        r[k] = {**REGLAGES[k], **(pub.get(k) or {})}
    r["formats"] = [f for f in r.get("formats") or [] if f in FORMATS["fr"]]
    return r

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
        "fan": ("Fan-made",
                "Clip non officiel réalisé par un fan. Je ne possède aucun droit sur « {titre} » : la musique, les "
                "paroles et l'enregistrement appartiennent à {artiste} et à leurs ayants droit. Je suis simplement un "
                "fan qui aime cette chanson et qui prend plaisir à en faire un clip avec mon outil Clip Studio, sans "
                "but lucratif.\nLes images du clip ont été créées avec l'intelligence artificielle; les personnages "
                "sont fictifs et ne représentent aucune personne réelle. Si vous êtes ayant droit et souhaitez le "
                "retrait de cette vidéo, écrivez-moi : je la retirerai."),
        "fan_ia": ("Fan-made IA",
                   "Reprise non officielle réalisée par un fan. « {titre} » est une chanson de {artiste} : je ne "
                   "possède aucun droit sur les paroles ni sur la composition, qui appartiennent à leurs auteurs et "
                   "ayants droit. Je suis simplement un fan qui aime cette chanson et qui prend plaisir à travailler "
                   "avec mon outil Clip Studio, sans but lucratif.\nCette version a été réinterprétée avec "
                   "l'intelligence artificielle (Suno), et les images du clip ont été créées par IA; les personnages "
                   "sont fictifs et ne représentent aucune personne réelle. Si vous êtes ayant droit et souhaitez le "
                   "retrait de cette vidéo, écrivez-moi : je la retirerai."),
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
        "fan": ("Fan-made",
                "Unofficial video made by a fan. I do not own any rights to \"{titre}\": the music, the lyrics and "
                "the recording belong to {artiste} and their rights holders. I am just a fan who loves this song and "
                "enjoys making a video for it with my Clip Studio tool, with no profit intended.\nThe images of the "
                "video were created with artificial intelligence; the characters are fictional and do not depict any "
                "real person. If you are a rights holder and want this video removed, contact me: I will take it "
                "down."),
        "fan_ia": ("AI Fan-made",
                   "Unofficial cover made by a fan. \"{titre}\" is a song by {artiste}: I do not own any rights to "
                   "the lyrics or the music, which belong to their authors and rights holders. I am just a fan who "
                   "loves this song and enjoys working with my Clip Studio tool, with no profit intended.\nThis "
                   "version was reinterpreted with artificial intelligence (Suno), and the images of the video were "
                   "created with AI; the characters are fictional and do not depict any real person. If you are a "
                   "rights holder and want this video removed, contact me: I will take it down."),
    },
}

DEMANDE = {
    "fr": """Tu prépares la publication YouTube d'un clip musical.
Chanson : « {titre} » — artiste : {artiste}
Origine : {origine}
Style visuel du clip : {style}
Intention de l'auteur (ambiance, sens, contexte — à respecter) : {intention}
Personnages du clip (fictifs) : {pers}{reference}

Paroles :
{paroles}

Rédige en français{ton} :
- "titre" : titre YouTube de 90 caractères maximum, qui commence exactement par « {artiste} – {titre} ({mention}) »,
  suivi éventuellement de « | » et d'un complément court (ex. « Clip officiel avec paroles »).
- "accroche" : {accroche}
- "hashtags" : liste de 5 à 7 hashtags pertinents (avec #), dont #{artiste_tag} et #{mention_tag}.
- "miniatures" : 3 idées de miniature YouTube vraiment différentes (scène, cadrage ou angle), chacune
  {{"idee": "résumé en quelques mots", "avec_texte": "…", "sans_texte": "…"{formats_cles}}} :
  - "avec_texte" : prompt complet pour générer une miniature YouTube 16:9 photoréaliste : une scène marquante de
    l'univers du clip, personnages décrits précisément (fictifs, aucune personne réelle, aucune célébrité),
    contraste élevé ; moitié gauche plus sombre et dégagée pour le texte ; texte en lettres capitales épaisses,
    lisibles et correctement orthographiées, exactement : « {titre_maj} » énorme en haut à gauche, « {artiste_maj} »
    juste en dessous, « {bandeau} » dans un bandeau {couleur} en bas à gauche ; aucun autre texte, aucun logo,
    aucun filigrane.
  - "sans_texte" : le même prompt, mais sans aucun texte dans l'image (moitié gauche laissée libre).{formats}
Réponds UNIQUEMENT par un JSON {{"titre": "…", "accroche": "…", "hashtags": ["#…"],
"miniatures": [{{"idee": "…", "avec_texte": "…", "sans_texte": "…"{formats_cles}}}, …]}}.{consigne}""",
    "en": """You are preparing the YouTube release of a music video.
Song: "{titre}" — artist: {artiste}
Origin: {origine}
Visual style of the video: {style}
Author's intent (mood, meaning, context — to respect): {intention}
Characters in the video (fictional): {pers}{reference}

Lyrics:
{paroles}

Write in English{ton}:
- "titre": YouTube title of 90 characters maximum, starting exactly with "{artiste} – {titre} ({mention})",
  optionally followed by "|" and a short complement (e.g. "Official lyric video").
- "accroche": {accroche}
- "hashtags": list of 5 to 7 relevant hashtags (with #), including #{artiste_tag} and #{mention_tag}.
- "miniatures": 3 truly different YouTube thumbnail ideas (scene, framing or angle), each
  {{"idee": "summary in a few words", "avec_texte": "…", "sans_texte": "…"{formats_cles}}}:
  - "avec_texte": complete prompt to generate a photorealistic 16:9 YouTube thumbnail: a striking scene of the
    video's world, characters described precisely (fictional, no real person, no celebrity), high contrast; left
    half darker and clear for the text; text in thick capital letters, readable and correctly spelled, exactly:
    "{titre_maj}" huge at the top left, "{artiste_maj}" just below, "{bandeau}" in a {couleur} banner at the bottom
    left; no other text, no logo, no watermark.
  - "sans_texte": the same prompt, but without any text in the image (left half left clear).{formats}
Answer ONLY with a JSON {{"titre": "…", "accroche": "…", "hashtags": ["#…"],
"miniatures": [{{"idee": "…", "avec_texte": "…", "sans_texte": "…"{formats_cles}}}, …]}}.{consigne}""",
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


def demande(cfg, paroles, consigne="", reference=""):
    """Demande à Claude. reference : description de la vignette choisie comme base de la 1re miniature."""
    lg, m, titre, artiste, mention, origine = _base(cfg)
    r = reglages(cfg)
    pers = "; ".join(f"{k} = {v}" for k, v in (cfg.get("personnages") or {}).items()) or m["aucun"]
    tag = lambda s: "".join(w[:1].upper() + w[1:] for w in re.sub(r"[^\w\s]", "", s).split())
    fr = lg == "fr"
    ton = TONS[lg].get(r["ton"])
    ton = (f", sur un ton {ton}" if fr else f", in a {ton} tone") if ton else \
        (" (le québécois familier est bienvenu si la chanson l'est)" if fr else "")
    accroche = ({"courte": "1 phrase courte et percutante qui donne envie d'écouter, dans le ton de la chanson."}
                if fr else {"courte": "1 short, punchy sentence that makes people want to listen, in the tone of the song."}
                ).get(r["accroche"], "2 à 3 phrases qui donnent envie d'écouter, dans le ton de la chanson." if fr
                      else "2 to 3 sentences that make people want to listen, in the tone of the song.")
    accroche += (" Quelques emojis bienvenus." if fr else " A few emojis are welcome.") if r["emojis"] \
        else (" Aucun emoji." if fr else " No emoji.")
    if reference:
        reference = ("\nScène de référence pour la 1re idée de miniature (la reprendre, avec l'apparence exacte de ses "
                     f"personnages, qui prime sur la fiche ci-dessus) : {reference}" if fr else
                     "\nReference scene for the 1st thumbnail idea (reuse it, with the exact appearance of its "
                     f"characters, which takes precedence over the list above): {reference}")
    q = DEMANDE[lg].format(
        titre=titre, artiste=artiste, mention=mention, origine=origine,
        style=cfg.get("style", ""), pers=pers, paroles=paroles, reference=reference, ton=ton, accroche=accroche,
        intention=(cfg.get("intention") or m["non_precisee"]).strip(),
        artiste_tag=tag(artiste), mention_tag=tag(mention),
        titre_maj=titre.upper(), artiste_maj=artiste.upper(),
        bandeau=(r["bandeau"].strip() or mention).upper(),
        couleur=COULEURS[lg].get(r["bandeau_couleur"], COULEURS[lg]["rouge"]),
        formats_cles="".join(f', "{f}": "…"' for f in r["formats"]),
        formats="".join(f'\n  - "{f}" : {FORMATS[lg][f]}.' if fr else f'\n  - "{f}": {FORMATS[lg][f]}.'
                        for f in r["formats"]),
        consigne=f"\n{m['consigne']} : {consigne}" if consigne else "")
    if cfg.get("instrumental"):                  # images abstraites : pas de photo ni de personnages
        q = q.replace("miniature YouTube 16:9 photoréaliste : une scène marquante de\n    l'univers du clip, personnages "
                      "décrits précisément (fictifs, aucune personne réelle, aucune célébrité)",
                      "miniature YouTube 16:9 dans le style visuel du clip : une\n    composition abstraite marquante, "
                      "sans personne ni visage")
        q = q.replace("photorealistic 16:9 YouTube thumbnail: a striking scene of the\n    video's world, characters "
                      "described precisely (fictional, no real person, no celebrity)",
                      "16:9 YouTube thumbnail in the video's visual style: a striking\n    abstract composition, "
                      "with no person or face")
    return q


def miniatures(ia):
    """Idées de miniature de la réponse de Claude : [{idee, avec_texte, sans_texte, (carre, vertical)}]."""
    out = []
    for x in ia.get("miniatures") or []:
        if isinstance(x, dict) and (x.get("avec_texte") or "").strip():
            out.append({k: str(v).strip() for k, v in x.items()
                        if k in ("idee", "avec_texte", "sans_texte", *FORMATS["fr"]) and v})
    if not out and (ia.get("miniature") or "").strip():          # ancien format : une seule miniature
        out.append({"idee": "", "avec_texte": ia["miniature"].strip(),
                    "sans_texte": (ia.get("miniature_sans_texte") or "").strip()})
    return out[:3]


def description(cfg, ia, chaps, paroles):
    lg, m, titre, artiste, mention, origine = _base(cfg)
    r = reglages(cfg)
    b = r["blocs"]
    # sans emojis : en-têtes du code sans leur pictogramme (« 🎬 Crédits » → « Crédits »)
    h = (lambda s: s) if r["emojis"] else (lambda s: re.sub(r"^[^\w«\"(]+\s*", "", s))
    guill = f"« {titre} »" if lg == "fr" else f"\"{titre}\""
    parts = [h(f"🎵 {artiste} – {guill} ({mention})")]
    if b["accroche"] and ia.get("accroche", "").strip():
        parts += ["", ia["accroche"].strip()]
    o = cfg.get("origine", "suno")
    if b["mention"]:
        parts += ["", h(m["a_propos"]), origine]
        if o.startswith("fan") and r["lien_officiel"].strip():
            parts.append(f"{m['officiel']} : {r['lien_officiel'].strip()}" if lg == "fr"
                         else f"{m['officiel']}: {r['lien_officiel'].strip()}")
    if b["chapitres"] and chaps:
        parts += ["", h(m["chapitres"]), *chaps]
    if b["paroles"] and not cfg.get("instrumental"):
        parts += ["", h(f"{m['paroles']} ({artiste})"), paroles]
    sep = " : " if lg == "fr" else ": "
    credits = [f"{m['roles'][k]}{sep}{v.strip()}" for k, v in r["credits"].items() if v.strip()]
    if r["clip_studio"]:
        credits.append(f"{m['fait_avec']}{sep}{CLIP_STUDIO_URL}")
    if b["credits"] and credits:
        parts += ["", h(m["credits"]), *credits]
    liens = [l.strip() for l in r["liens"].splitlines() if l.strip()]
    if b["liens"] and liens:
        parts += ["", h(m["liens"]), *liens]
    if o != "complete":                          # fan-made : les droits restent à l'artiste
        d = "droits_fan" if o.startswith("fan") else "droits_instru" if cfg.get("instrumental") else "droits"
        parts += ["", f"© {artiste} — {m[d]}"]
    tags = ia.get("hashtags") or []
    if b["hashtags"] and tags:
        parts += ["", " ".join(t if t.startswith("#") else f"#{t}" for t in tags)]
    return "\n".join(parts).strip() + "\n"


def markdown(pub, langue="fr"):
    t = {"fr": ("Publication YouTube", "Titre", "Miniature", "avec texte", "sans texte", "carrée 1:1", "verticale 9:16"),
         "en": ("YouTube release", "Title", "Thumbnail", "with text", "without text", "square 1:1", "vertical 9:16")}[langue]
    out = f"# {t[0]}\n\n## {t[1]}\n```\n{pub['titre']}\n```\n\n## Description\n```\n{pub['description']}```\n"
    idees = pub.get("miniatures") or [{"idee": "", "avec_texte": pub.get("miniature", ""),
                                       "sans_texte": pub.get("miniature_sans_texte", "")}]
    for i, x in enumerate(idees, 1):
        for k, lib in (("avec_texte", t[3]), ("sans_texte", t[4]), ("carre", t[5]), ("vertical", t[6])):
            if x.get(k):
                idee = f" — {x['idee']}" if x.get("idee") else ""
                out += f"\n## {t[2]} {i}{idee} ({lib})\n```\n{x[k]}\n```\n"
    return out


def save(build_dir, pub, langue="fr"):
    (build_dir / "publication.json").write_text(json.dumps(pub, indent=1, ensure_ascii=False), encoding="utf-8")
    (build_dir / "publication.md").write_text(markdown(pub, langue), encoding="utf-8")
