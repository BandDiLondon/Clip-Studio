"""Planches : vérification, découpe en cases (grille configurable), retouches, upscale Real-ESRGAN."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import ROOT
from .i18n import tr

ESRGAN = ROOT / "tools" / "realesrgan" / ("realesrgan-ncnn-vulkan.exe" if sys.platform == "win32" else "realesrgan-ncnn-vulkan")
DARK = 30        # luminance (90e percentile) max d'une ligne/colonne de gouttière
SEARCH = 0.06    # zone de recherche autour de la position théorique (fraction)
INSET = 0.015    # marge retirée à l'intérieur de chaque case
MAX_W = 2560     # largeur max d'une case après upscale
BIG = 1400       # une retouche plus large que ça n'est pas upscalée
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
PLANCHE_RE = re.compile(r"^p\d+$", re.I)
CASE_RE = re.compile(r"^p\d+_c\d+$", re.I)


def _runs(mask):
    """Plages [a, b] consécutives où mask est vrai."""
    runs, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


def _gutters(profile, n):
    """Positions des n-1 gouttières internes (plage sombre la plus proche de k/n)
    et nombre de gouttières réellement trouvées."""
    size = len(profile)

    def runs_at(threshold, max_w):
        runs = []
        for r in _runs(profile < threshold):     # fusionne les plages séparées de ≤ 3 px
            if runs and r[0] - runs[-1][1] <= 4:
                runs[-1] = (runs[-1][0], r[1])
            else:
                runs.append(r)
        return [r for r in runs if r[1] - r[0] <= size * max_w]

    # seuil strict d'abord (gouttière = noir pur, épaisse tolérée jusqu'à 8 %), puis large mais
    # fine (3 %) : une image très sombre collée à la gouttière fusionne avec elle au seuil large
    levels = [runs_at(12, 0.08), runs_at(DARK, 0.03)]
    cuts, found = [], 0
    for k in range(1, n):
        target = size * k / n
        best = None
        for runs in levels:
            near = [r for r in runs if abs((r[0] + r[1]) / 2 - target) < size * SEARCH]
            if near:
                best = min(near, key=lambda r: abs((r[0] + r[1]) / 2 - target))
                break
        if best:
            a, b = best
            found += 1
        else:
            a = b = int(target)
        cuts.append((a, b))
    return cuts, found


def _edges(profile, n):
    """Bornes [début, fin[ de chaque case le long d'un axe + gouttières trouvées."""
    size = len(profile)
    border = size // 100                     # cadre extérieur : 1 % max
    lo = next((i for i in range(border) if profile[i] >= DARK), border)
    hi = next((i for i in range(size - 1, size - 1 - border, -1) if profile[i] >= DARK), size - 1 - border) + 1
    cuts, found = _gutters(profile, n)
    bounds, prev = [], lo
    for a, b in cuts:
        bounds.append((prev, a))
        prev = b + 1
    bounds.append((prev, hi))
    return bounds, found


def _grid(im, cols, rows):
    g = np.asarray(im.convert("L"), dtype=np.float32)
    # 90e percentile : une gouttière est noire sur toute sa longueur, une zone sombre d'image non
    xs, fx = _edges(np.percentile(g, 90, axis=0), cols)
    ys, fy = _edges(np.percentile(g, 90, axis=1), rows)
    return xs, ys, fx + fy


def split(planche, cols=2, rows=3):
    """Retourne les cases (PIL) d'une planche, ordre gauche→droite, haut→bas."""
    im = Image.open(planche).convert("RGB")
    xs, ys, _ = _grid(im, cols, rows)
    cells = []
    for y0, y1 in ys:
        for x0, x1 in xs:
            mx, my = int((x1 - x0) * INSET), int((y1 - y0) * INSET)
            cells.append(im.crop((x0 + mx, y0 + my, x1 - mx, y1 - my)))
    return cells


def find_planches(src):
    return sorted((p for p in Path(src).iterdir() if p.suffix.lower() in IMG_EXT and PLANCHE_RE.match(p.stem)),
                  key=lambda p: int(p.stem[1:]))


def verify(projet_dir, planches_dir, shotlist):
    """Contrôle les planches avant découpe. Retourne la liste des problèmes (vide = OK)."""
    src = Path(projet_dir) / planches_dir
    files = {p.stem.lower(): p for p in find_planches(src)}
    problems = []
    for pl in shotlist["planches"]:
        cols, rows = pl["grid"]
        f = files.pop(pl["id"], None)
        if f is None:
            problems.append(tr(f"{pl['id'].upper()} : fichier absent ({src.name}/{pl['id'].upper()}.png attendu)",
                               f"{pl['id'].upper()}: missing file ({src.name}/{pl['id'].upper()}.png expected)"))
            print(tr(f"  [XX] {pl['id'].upper()} absent", f"  [XX] {pl['id'].upper()} missing"))
            continue
        im = Image.open(f).convert("RGB")
        want = cols * 16 / (rows * 9)
        got = im.width / im.height
        xs, ys, found = _grid(im, cols, rows)
        cw = np.median([b - a for a, b in xs])
        ch = np.median([b - a for a, b in ys])
        cell_ratio = cw / ch
        msgs = []
        if abs(got / want - 1) > 0.08:
            msgs.append(tr(f"format {im.width}×{im.height} ({got:.2f}) au lieu de {pl['ratio']}",
                           f"format {im.width}×{im.height} ({got:.2f}) instead of {pl['ratio']}"))
        if found < (cols - 1) + (rows - 1):
            msgs.append(tr(f"{found}/{(cols - 1) + (rows - 1)} séparations trouvées : grille {cols}×{rows} non respectée?",
                           f"{found}/{(cols - 1) + (rows - 1)} separations found: {cols}×{rows} grid not respected?"))
        notes = []
        dev = cell_ratio / (16 / 9) - 1
        if abs(dev) > 0.25:                   # vraiment hors format : têtes ou côtés fortement coupés
            msgs.append(tr(f"vignettes {cell_ratio:.2f}:1 au lieu de 16:9 (1.78) : recadrage important",
                           f"cells {cell_ratio:.2f}:1 instead of 16:9 (1.78): heavy cropping"))
        elif abs(dev) > 0.08:                 # écart modéré : simple note, pas de blocage
            perte = round(100 * (1 - min(cell_ratio, 16 / 9) / max(cell_ratio, 16 / 9)) / 2)
            cote = tr("de chaque côté", "on each side") if dev > 0 else tr("en haut et en bas", "at the top and bottom")
            notes.append(tr(f"vignettes {cell_ratio:.2f}:1 (16:9 = 1.78) : ~{perte} % recadré {cote}, sans gravité",
                            f"cells {cell_ratio:.2f}:1 (16:9 = 1.78): ~{perte} % cropped {cote}, harmless"))
        if im.width / cols < 400:
            msgs.append(tr(f"vignettes étroites ({int(cw)} px) : image générée trop petite",
                           f"narrow cells ({int(cw)} px): generated image too small"))
        state = "OK" if not msgs else "⚠ "
        print(tr(f"  [{state}] {f.name} {im.width}×{im.height}, grille {cols}×{rows}, vignettes ~{int(cw)}×{int(ch)}",
                 f"  [{state}] {f.name} {im.width}×{im.height}, grid {cols}×{rows}, cells ~{int(cw)}×{int(ch)}"))
        for m in msgs:
            print(f"        - {m}")
        for m in notes:
            print(f"        · note : {m}")
        problems += [f"{f.name} : {m}" for m in msgs]
    for extra in files.values():
        print(tr(f"  [--] {extra.name} ignorée (pas dans la shotlist)", f"  [--] {extra.name} ignored (not in the shotlist)"))
    return problems


def upscale(src_dir, dst_dir, scale=4, model="realesrgan-x4plus"):
    if not ESRGAN.exists():
        raise FileNotFoundError(tr(f"Real-ESRGAN absent : {ESRGAN}", f"Real-ESRGAN missing: {ESRGAN}"))
    r = subprocess.run([str(ESRGAN), "-i", str(src_dir), "-o", str(dst_dir),
                        "-s", str(scale), "-n", model, "-f", "png"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])


def _font(size):
    """Arial gras (Windows, macOS), sinon DejaVu / Liberation (Linux), sinon la police intégrée de Pillow."""
    for f in ("arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def contact_sheet(cases_dir, out, planches=None, thumb=320):
    files = sorted(Path(cases_dir).glob("p*_c*.png"))
    planches = planches or sorted({f.stem.split("_")[0] for f in files})
    font = _font(22)
    th = thumb * 9 // 16 if all(                       # vignettes 16:9 → cellules 16:9
        Image.open(f).width > Image.open(f).height for f in files
        if f.stem.split("_")[0] in planches) else thumb
    sheet = Image.new("RGB", (thumb * 6, (th + 30) * len(planches)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for r, p in enumerate(planches):
        for c in range(6):
            f = Path(cases_dir) / f"{p}_c{c + 1}.png"
            if not f.exists():
                continue
            im = Image.open(f).convert("RGB")
            size = im.size
            im.thumbnail((thumb, th))
            x, y = c * thumb, r * (th + 30)
            sheet.paste(im, (x, y + 30))
            d.text((x + 6, y + 4), f"{p}_c{c + 1}  {size[0]}×{size[1]}", font=font, fill=(255, 220, 80))
    sheet.save(out, quality=88)


def _cap(f):
    im = Image.open(f)
    if im.width > MAX_W:
        im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS).save(f)


def cut_all(projet_dir, planches_dir="planches", scale=4, grid=(2, 3), grids=None):
    """Découpe les planches P*.jpg|png → cases/pN_cK.png (upscalées).
    grids = {"p1": (2, 3), …} depuis la shotlist (seules ces planches sont découpées si fourni).
    retouches/pN_cK.* remplace la case découpée correspondante.
    Les cases obsolètes (planches disparues) sont supprimées."""
    grids = grids or {}
    projet_dir = Path(projet_dir)
    cases = projet_dir / "cases"
    cases.mkdir(exist_ok=True)
    (projet_dir / "build").mkdir(exist_ok=True)
    planches = [p for p in find_planches(projet_dir / planches_dir) if not grids or p.stem.lower() in grids]
    retouches = {f.stem.lower(): f for f in (projet_dir / "retouches").glob("*")
                 if f.suffix.lower() in IMG_EXT and CASE_RE.match(f.stem)} \
        if (projet_dir / "retouches").is_dir() else {}
    expected = set()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for p in planches:
            cells = split(p, *grids.get(p.stem.lower(), grid))
            for i, cell in enumerate(cells, 1):
                name = f"{p.stem.lower()}_c{i}"
                expected.add(name)
                if name not in retouches:
                    cell.save(tmp / f"{name}.png")
            w, h = cells[0].size
            warn = "" if abs(w / h - 16 / 9) < 0.15 else f"  ⚠ ratio {w / h:.2f} ≠ 16:9 (1.78)"
            print(tr(f"  {p.name} → {len(cells)} cases {w}×{h}{warn}", f"  {p.name} → {len(cells)} cells {w}×{h}{warn}"))
        big = []
        for name, f in retouches.items():
            im = Image.open(f).convert("RGB")
            expected.add(name)
            if im.width >= BIG or scale <= 1:
                big.append((name, im))
            else:
                im.save(tmp / f"{name}.png")
            print(tr(f"  retouche {f.name} ({im.width}×{im.height}) → {name}", f"  retouch {f.name} ({im.width}×{im.height}) → {name}"))
        if scale > 1 and any(tmp.iterdir()):
            print(f"  Real-ESRGAN ×{scale} …")
            import time
            t0, err = time.time() - 1, ""
            try:
                upscale(tmp, cases, scale)
            except (RuntimeError, OSError) as e:          # pas de GPU Vulkan, binaire absent…
                err = (str(e).strip().splitlines() or [""])[-1][:120]
            ratees = [f for f in tmp.iterdir()
                      if not (cases / f.name).exists() or (cases / f.name).stat().st_mtime < t0]
            if ratees:
                print(tr(f"  ⚠ Real-ESRGAN indisponible{f' ({err})' if err else ''} : agrandissement classique "
                         f"de {len(ratees)} case(s), moins net",
                         f"  ⚠ Real-ESRGAN unavailable{f' ({err})' if err else ''}: classic upscaling "
                         f"of {len(ratees)} cell(s), less sharp"))
                for f in ratees:
                    im = Image.open(f)
                    w = min(im.width * scale, MAX_W)
                    im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(cases / f.name)
            for f in tmp.iterdir():
                _cap(cases / f.name)
        else:
            for f in tmp.iterdir():
                shutil.copy(f, cases / f.name)
        for name, im in big:
            im.save(cases / f"{name}.png")
            _cap(cases / f"{name}.png")
    # nettoyage : cases d'anciennes planches
    stale = [f for f in cases.glob("p*_c*.png") if f.stem.lower() not in expected]
    for f in stale:
        f.unlink()
    if stale:
        print(tr(f"  {len(stale)} case(s) obsolète(s) supprimée(s)", f"  {len(stale)} obsolete cell(s) deleted"))
    contact_sheet(cases, projet_dir / "build" / "planche_contact.jpg", [p.stem.lower() for p in planches])
    print(tr(f"  Planche-contact : {projet_dir / 'build' / 'planche_contact.jpg'}",
             f"  Contact sheet: {projet_dir / 'build' / 'planche_contact.jpg'}"))
