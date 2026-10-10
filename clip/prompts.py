"""Prompts de planches à partir de la shotlist : chaque case décrite strictement, 1 case = 1 vers.
Rédigés dans la langue du projet (« langue » : fr | en)."""
import re

from .i18n import langue_projet
from .lyrics import read_lyrics
from . import shots as shotlist

COL_NAMES = {"fr": {1: ["centre"], 2: ["gauche", "droite"], 3: ["gauche", "centre", "droite"]},
             "en": {1: ["center"], 2: ["left", "right"], 3: ["left", "center", "right"]}}

HEADER = {
    # pas le mot « storyboard » : un storyboard a des légendes, et le générateur les écrit
    "fr": (
        "Une seule image composée de EXACTEMENT {n} photographies de cinéma distinctes (ni plus ni moins), "
        "disposées en grille de {cols} colonne{cs} × {rows} rangée{rs}, séparées par une fine bordure noire "
        "uniforme. Image complète au format {ratio}.\n"
        "Chaque photo occupe toute sa case, bord à bord : AUCUNE légende, AUCUN sous-titre, AUCUNE bande de "
        "texte sous ou sur les photos. Les descriptions ci-dessous sont des instructions de mise en scène à "
        "illustrer, jamais du texte à écrire dans l'image.\n"
        "Chaque vignette est un plan de cinéma PAYSAGE 16:9 (plus large que haute), cadré pour le 16:9 : "
        "sujet principal centré, têtes et visages entiers avec de l'air au-dessus; le quart inférieur "
        "de chaque vignette ne contient aucun élément important (zone réservée aux paroles).\n"
        "Chaque vignette montre UNIQUEMENT la scène décrite pour elle, rien d'autre; aucune vignette ne "
        "répète une autre.\n"
        "Style : {style}. Même style et même grain dans toutes les vignettes."),
    "en": (
        "One single image made of EXACTLY {n} distinct cinematic photographs (no more, no less), arranged in a "
        "grid of {cols} column{cs} × {rows} row{rs}, separated by a thin uniform black border. Full image in "
        "{ratio} format.\n"
        "Each photo fills its whole cell, edge to edge: NO caption, NO subtitle, NO text band under or over the "
        "photos. The descriptions below are staging instructions to illustrate, never text to write in the "
        "image.\n"
        "Each cell is a 16:9 LANDSCAPE film shot (wider than tall), framed for 16:9: main subject centered, "
        "heads and faces whole with headroom above; the bottom quarter of each cell contains nothing important "
        "(area reserved for the lyrics).\n"
        "Each cell shows ONLY the scene described for it, nothing else; no cell repeats another.\n"
        "Style: {style}. Same style and same grain in every cell."),
}
FOOTER = {
    "fr": ("Aucun texte, aucune lettre, aucun chiffre, aucun numéro de vignette, aucune légende, aucun "
           "logo, aucune enseigne ou affiche lisible, aucune célébrité, aucun filigrane, aucune bulle.\n"
           "Négatif : texte, lettres, mots, chiffres, numéros, légende, sous-titre, texte sous l'image, "
           "bandeau de texte, storyboard annoté, étiquette, inscription, filigrane, logo, vignettes carrées, "
           "vignettes verticales, vignette supplémentaire, bordures épaisses, cadre blanc."),
    "en": ("No text, no letters, no digits, no cell numbers, no caption, no logo, no readable sign or poster, "
           "no celebrity, no watermark, no speech bubble.\n"
           "Negative: text, letters, words, digits, numbers, caption, subtitle, text under the image, text "
           "banner, annotated storyboard, label, inscription, watermark, logo, square cells, vertical cells, "
           "extra cell, thick borders, white frame."),
}
DEFAULT_STYLE = {"fr": "photoréaliste, grain cinéma, contraste élevé",
                 "en": "photorealistic, cinematic film grain, high contrast"}

# « Plan : large ; Sujet : … » → phrase sans étiquettes (les étiquettes finissent écrites en légende).
# Étiquettes reconnues dans les deux langues, quelle que soit la langue du projet.
LABELS = ("Plan", "Sujet", "Action", "Décor", "Decor", "Lumière", "Lumiere",
          "Shot", "Subject", "Setting", "Lighting")


def prose(desc, langue="fr"):
    parts = [p.strip() for p in re.split(r"\s*;\s*", desc or "") if p.strip()]
    out = []
    for p in parts:
        m = re.match(r"^(%s)\s*:\s*(.*)$" % "|".join(LABELS), p, re.I)
        label, txt = (m.group(1).lower(), m.group(2)) if m else ("", p)
        if not txt:
            continue
        low = txt[0].lower() + txt[1:]
        if langue == "en":
            if label in ("plan", "shot"):
                txt = txt if "shot" in txt.lower() else f"{low} shot"
            elif label in ("décor", "decor", "setting"):
                txt = txt if txt.lower().startswith(("in ", "on ", "at ", "inside", "outside")) else f"in {low}"
            elif label.startswith(("lumi", "light")):
                txt = txt if "light" in txt.lower() else f"{low} lighting"
        else:
            if label in ("plan", "shot"):
                txt = txt if txt.lower().startswith(("plan", "gros", "très")) else f"plan {txt}"
            elif label in ("décor", "decor", "setting"):
                txt = f"dans {low}" if not txt.lower().startswith(("dans", "sur", "au ", "en ")) else txt
            elif label.startswith(("lumi", "light")):
                txt = f"éclairage {low}"
        out.append(txt)
    s = ", ".join(out)
    return (s[:1].upper() + s[1:] + ".") if s else ""


FIELDS = {"fr": "Plan : [DÉCRIRE] ; Sujet : [DÉCRIRE] ; Action : [DÉCRIRE] ; Décor : [DÉCRIRE] ; Lumière : [DÉCRIRE]",
          "en": "Shot: [DESCRIBE] ; Subject: [DESCRIBE] ; Action: [DESCRIBE] ; Setting: [DESCRIBE] ; "
                "Lighting: [DESCRIBE]"}


def position(i, cols, rows, langue="fr"):
    r, c = divmod(i, cols)
    col = COL_NAMES[langue].get(cols, [str(k + 1) for k in range(cols)])[c]
    return col if rows == 1 else (f"row {r + 1}, {col}" if langue == "en" else f"rangée {r + 1}, {col}")


def characters_block(cfg):
    pers = cfg.get("personnages") or {}
    if not pers:
        return ""
    en = langue_projet(cfg) == "en"
    lines = ["Recurring characters (identical appearance wherever they appear):" if en
             else "Personnages récurrents (apparence identique partout où ils apparaissent) :"]
    lines += [f"- {nom}{':' if en else ' :'} {desc}" for nom, desc in pers.items()]
    return "\n".join(lines)


def render_prompt(planche, cells, cfg):
    """cells : [(shot, description|None)] dans l'ordre des vignettes."""
    lg = langue_projet(cfg)
    cols, rows = planche["grid"]
    n = cols * rows
    out = [HEADER[lg].format(n=n, cols=cols, rows=rows, cs="s" if cols > 1 else "",
                             rs="s" if rows > 1 else "", ratio=planche["ratio"],
                             style=cfg.get("style") or DEFAULT_STYLE[lg])]
    cb = characters_block(cfg)
    if cb:
        out.append(cb)
    # les paroles ne sont PAS citées : un texte entre guillemets pousse le générateur à l'écrire
    # dans l'image ; la correspondance vignette ↔ vers est dans le tableau du fichier
    for i, (shot, desc) in enumerate(cells):
        todo = FIELDS[lg] if shot.get("text") else ("ambiance shot, " if lg == "en" else "plan d'ambiance, ") + FIELDS[lg]
        out.append(f"Photo {i + 1} ({position(i, cols, rows, lg)}){':' if lg == 'en' else ' :'} "
                   f"{prose(desc, lg) if desc else todo}")
    out.append(FOOTER[lg])
    return "\n".join(out)


def skeleton(cfg, lyrics_path, descriptions=None):
    """Retourne (shotlist, markdown). descriptions : {shot_id: texte} déjà rédigées."""
    lg = langue_projet(cfg)
    en = lg == "en"
    sl = shotlist.build(read_lyrics(lyrics_path), dedupe=cfg.get("dedupe", True),
                        ambiance=cfg.get("ambiance", 0))
    descriptions = descriptions or {}
    if en:
        md = [f"# Panel prompts — {len(sl['shots'])} images, {len(sl['planches'])} panel(s)\n",
              "Save each panel as `<planches>/P1.png`, `P2.png`… then `python -m clip cut <name>`.\n",
              "| Panel | Cell | Image | Line | Used in |", "|---|---|---|---|---|"]
    else:
        md = [f"# Prompts de planches — {len(sl['shots'])} images, {len(sl['planches'])} planche(s)\n",
              "Enregistrer chaque planche sous `<planches>/P1.png`, `P2.png`… puis `python -m clip cut <nom>`.\n",
              "| Planche | Vignette | Image | Vers | Utilisé dans |", "|---|---|---|---|---|"]
    for s in sl["shots"]:
        pid, c = s["id"].split("_c")
        pl = next(p for p in sl["planches"] if p["id"] == pid)
        md.append(f"| {pid.upper()} | {c} ({position(int(c) - 1, *pl['grid'], lg)}) | {s['id']} | "
                  f"{s['text'] or ('(instrumental ambiance)' if en else '(ambiance instrumentale)')} | "
                  f"{', '.join(x for x in s['sections'] if x) or '—'} |")
    for p in sl["planches"]:
        cells = [(s, descriptions.get(s["id"])) for s in sl["shots"] if s["id"].startswith(p["id"] + "_")]
        titre = (f"## {p['id'].upper()} — grid {p['grid'][0]}×{p['grid'][1]}, format {p['ratio']}\n" if en
                 else f"## {p['id'].upper()} — grille {p['grid'][0]}×{p['grid'][1]}, format {p['ratio']}\n")
        md += ["\n---\n", titre, "```", render_prompt(p, cells, cfg), "```"]
    return sl, "\n".join(md) + "\n"
