"""Liste d'images (shotlist) : 1 image par vers unique, regroupées dans le minimum de planches.

Le but des planches est d'économiser les générations d'images : on calcule le nombre exact
d'images requises par le texte, puis on les range en grilles de vignettes 16:9.
"""
import json
import re
import unicodedata

# grille (colonnes, rangées) selon le nombre de vignettes de la planche → ratio de l'image complète
GRIDS = {6: (2, 3), 4: (2, 2), 2: (1, 2), 1: (1, 1)}
RATIOS = {(2, 3): "32:27 (2048×1728 ou 1536×1296)", (2, 2): "16:9 (2048×1152)",
          (1, 2): "8:9 (1536×1728)", (1, 1): "16:9 (2048×1152)"}


def key(text):
    """Clé de dédoublonnage : sans accents, casse, ponctuation ni espaces multiples."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^\w\s']", " ", t).split())


def _pack(n):
    """Tailles de planches pour n images : des 6, puis la plus petite grille qui contient le reste."""
    sizes = [6] * (n // 6)
    r = n % 6
    if r:
        sizes.append(6 if r == 5 else 4 if r >= 3 else r)
    return sizes


def build(lines, dedupe=True, ambiance=0):
    """lines : [(section, vers)] → {"planches": [...], "shots": [...]}.
    Chaque shot : id pN_cK, texte, sections, clé. `ambiance` images d'ambiance (passages
    instrumentaux) sont ajoutées après les vers ; les cases restantes de la dernière planche
    deviennent aussi des images d'ambiance plutôt que d'être perdues."""
    shots, seen = [], {}
    for section, text in lines:
        k = key(text)
        if dedupe and k in seen:
            seen[k]["sections"].append(section)
            continue
        shot = {"text": text, "key": k, "sections": [section]}
        shots.append(shot)
        seen[k] = shot
    shots += [{"text": None, "key": None, "sections": [], "ambiance": True} for _ in range(ambiance)]
    planches, i = [], 0
    for pn, size in enumerate(_pack(len(shots)), 1):
        cols, rows = GRIDS[size]
        planches.append({"id": f"p{pn}", "grid": [cols, rows], "ratio": RATIOS[(cols, rows)]})
        for c in range(1, size + 1):
            if i >= len(shots):
                shots.append({"text": None, "key": None, "sections": [], "ambiance": True})
            shots[i]["id"] = f"p{pn}_c{c}"
            i += 1
    return {"planches": planches, "shots": shots}


def save(sl, path):
    path.write_text(json.dumps(sl, indent=1, ensure_ascii=False), encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
