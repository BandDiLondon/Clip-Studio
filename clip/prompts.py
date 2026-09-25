"""Prompts de planches à partir de la shotlist : chaque case décrite strictement, 1 case = 1 vers."""
from .lyrics import read_lyrics
from . import shots as shotlist

COL_NAMES = {1: ["centre"], 2: ["gauche", "droite"], 3: ["gauche", "centre", "droite"]}

HEADER = (
    # pas le mot « storyboard » : un storyboard a des légendes, et le générateur les écrit
    "Une seule image composée de EXACTEMENT {n} photographies de cinéma distinctes (ni plus ni moins), "
    "disposées en grille de {cols} colonne{cs} × {rows} rangée{rs}, séparées par une fine bordure noire "
    "uniforme. Image complète au format {ratio}.\n"
    "Chaque photo occupe toute sa case, bord à bord : AUCUNE légende, AUCUN sous-titre, AUCUNE bande de "
    "texte sous ou sur les photos. Les descriptions ci-dessous sont des instructions de mise en scène à "
    "illustrer, jamais du texte à écrire dans l'image.\n"
    "Chaque vignette est un plan de cinéma PAYSAGE 16:9 (plus large que haute), cadré pour le 16:9 : "
    "sujet principal centré, têtes et visages entiers avec de l'air au-dessus ; le quart inférieur "
    "de chaque vignette ne contient aucun élément important (zone réservée aux paroles).\n"
    "Chaque vignette montre UNIQUEMENT la scène décrite pour elle, rien d'autre ; aucune vignette ne "
    "répète une autre.\n"
    "Style : {style}. Même style et même grain dans toutes les vignettes."
)
FOOTER = ("Aucun texte, aucune lettre, aucun chiffre, aucun numéro de vignette, aucune légende, aucun "
          "logo, aucune enseigne ou affiche lisible, aucune célébrité, aucun filigrane, aucune bulle.\n"
          "Négatif : texte, lettres, mots, chiffres, numéros, légende, sous-titre, texte sous l'image, "
          "bandeau de texte, storyboard annoté, étiquette, inscription, filigrane, logo, vignettes carrées, "
          "vignettes verticales, vignette supplémentaire, bordures épaisses, cadre blanc.")

# « Plan : large ; Sujet : … » → phrase sans étiquettes (les étiquettes finissent écrites en légende)
LABELS = ("Plan", "Sujet", "Action", "Décor", "Decor", "Lumière", "Lumiere")


def prose(desc):
    import re
    parts = [p.strip() for p in re.split(r"\s*;\s*", desc or "") if p.strip()]
    out = []
    for p in parts:
        m = re.match(r"^(%s)\s*:\s*(.*)$" % "|".join(LABELS), p, re.I)
        label, txt = (m.group(1).lower(), m.group(2)) if m else ("", p)
        if not txt:
            continue
        if label.startswith("plan"):
            txt = txt if txt.lower().startswith(("plan", "gros", "très")) else f"plan {txt}"
        elif label.startswith("d"):
            txt = f"dans {txt[0].lower() + txt[1:]}" if not txt.lower().startswith(("dans", "sur", "au ", "en ")) else txt
        elif label.startswith("lumi"):
            txt = f"éclairage {txt[0].lower() + txt[1:]}"
        out.append(txt)
    s = ", ".join(out)
    return (s[:1].upper() + s[1:] + ".") if s else ""
FIELDS = "Plan : [DÉCRIRE] ; Sujet : [DÉCRIRE] ; Action : [DÉCRIRE] ; Décor : [DÉCRIRE] ; Lumière : [DÉCRIRE]"


def position(i, cols, rows):
    r, c = divmod(i, cols)
    col = COL_NAMES.get(cols, [str(k + 1) for k in range(cols)])[c]
    return col if rows == 1 else f"rangée {r + 1}, {col}"


def characters_block(cfg):
    pers = cfg.get("personnages") or {}
    if not pers:
        return ""
    lines = ["Personnages récurrents (apparence identique partout où ils apparaissent) :"]
    lines += [f"- {nom} : {desc}" for nom, desc in pers.items()]
    return "\n".join(lines)


def render_prompt(planche, cells, cfg):
    """cells : [(shot, description|None)] dans l'ordre des vignettes."""
    cols, rows = planche["grid"]
    n = cols * rows
    out = [HEADER.format(n=n, cols=cols, rows=rows, cs="s" if cols > 1 else "",
                         rs="s" if rows > 1 else "", ratio=planche["ratio"],
                         style=cfg.get("style", "photoréaliste, grain cinéma, contraste élevé"))]
    cb = characters_block(cfg)
    if cb:
        out.append(cb)
    # les paroles ne sont PAS citées : un texte entre guillemets pousse le générateur à l'écrire
    # dans l'image ; la correspondance vignette ↔ vers est dans le tableau du fichier
    for i, (shot, desc) in enumerate(cells):
        todo = FIELDS if shot.get("text") else "plan d'ambiance, " + FIELDS
        out.append(f"Photo {i + 1} ({position(i, cols, rows)}) : {prose(desc) if desc else todo}")
    out.append(FOOTER)
    return "\n".join(out)


def skeleton(cfg, lyrics_path, descriptions=None):
    """Retourne (shotlist, markdown). descriptions : {shot_id: texte} déjà rédigées."""
    sl = shotlist.build(read_lyrics(lyrics_path), dedupe=cfg.get("dedupe", True),
                        ambiance=cfg.get("ambiance", 0))
    descriptions = descriptions or {}
    md = [f"# Prompts de planches — {len(sl['shots'])} images, {len(sl['planches'])} planche(s)\n",
          "Enregistrer chaque planche sous `<planches>/P1.png`, `P2.png`… puis `python -m clip cut <nom>`.\n",
          "| Planche | Vignette | Image | Vers | Utilisé dans |", "|---|---|---|---|---|"]
    for s in sl["shots"]:
        pid, c = s["id"].split("_c")
        pl = next(p for p in sl["planches"] if p["id"] == pid)
        md.append(f"| {pid.upper()} | {c} ({position(int(c) - 1, *pl['grid'])}) | {s['id']} | "
                  f"{s['text'] or '(ambiance instrumentale)'} | {', '.join(x for x in s['sections'] if x) or '—'} |")
    for p in sl["planches"]:
        cells = [(s, descriptions.get(s["id"])) for s in sl["shots"] if s["id"].startswith(p["id"] + "_")]
        md += ["\n---\n", f"## {p['id'].upper()} — grille {p['grid'][0]}×{p['grid'][1]}, format {p['ratio']}\n",
               "```", render_prompt(p, cells, cfg), "```"]
    return sl, "\n".join(md) + "\n"
