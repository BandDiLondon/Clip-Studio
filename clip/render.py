"""Rendu unifié : cases (zoom + pulse + flash), travelling sur solos, karaoké ASS, audio muxé."""
import bisect
import json
import math
import os
import re
import subprocess
from collections import deque
import multiprocessing
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from . import effects as FX

XFADE = 0.15          # durée du fondu enchaîné entre deux plans (s)
YELLOW_ASS = "&H0050DCFF&"   # (255,220,80) en BGR ASS
WHITE_ASS = "&H00FFFFFF&"

# ---------------------------------------------------------------- timeline

def camera_from_plan(desc):
    """Mouvement de caméra déduit du champ « Plan : … » d'une description de vignette."""
    m = re.search(r"Plan\s*:\s*([^;]+)", desc or "", re.I)
    plan = (m.group(1) if m else "").lower()
    if "large" in plan:
        return "pan"          # plan large / très large : travelling latéral
    if "gros" in plan or "rapproch" in plan:
        return "push"         # gros plan / rapproché : zoom avant
    if "moyen" in plan:
        return "pull"         # plan moyen : zoom arrière
    return "push"


PARTICULES = [
    # (type, mots-clés cherchés dans la description de la vignette) — le premier qui correspond gagne
    ("etincelles", ("étincelle", "etincelle", "feu d'artifice", "feux d'artifice", "soudure", "meuleuse")),
    ("pluie", ("pluie", "pleut", "pleuvoir", "averse", "orage", "trempé", "parapluie")),
    ("confettis", ("confetti", "paillette", "fête", "célébr", "victoire", "trophée", "disque d'or", "remise de prix")),
    ("braises", ("feu", "flamme", "braise", "tison", "incendi", "enfer", "brûl", "brasier", "forge", "bûcher", "cendre")),
    ("neige", ("neige", "enneig", "flocon", "hiver", "blizzard")),
    ("bokeh", ("luciole", "guirlande", "bokeh", "lanterne", "bougie", "chandelle")),
    ("poussiere", ("bar", "taverne", "enfum", "fumée", "sous-sol", "grange", "scène", "salle")),
]

# (luminosité, saturation) par section quand "look_sections" est actif
SECTION_TONES = {
    "chorus": (1.08, 1.12), "refrain": (1.08, 1.12),
    "verse": (0.95, 0.95), "couplet": (0.95, 0.95),
    "bridge": (0.96, 0.80), "pont": (0.96, 0.80),
    "outro": (0.94, 0.88), "intro": (1.0, 1.0), "instrumental": (1.0, 1.0),
}


FUMEES = [
    # (type, mots-clés) — le premier qui correspond gagne
    ("brouillard", ("brouillard", "brume", "brumeu")),
    ("fumee", ("fumée", "fumee", "enfum", "fumig", "vapeur", "incendi", "brasier", "flamme", "cigare", "smoke")),
]


LUMIERES = {
    "flammes": ("flamme", "incendi", "brasier", "bûcher", "bucher", "en feu", "enfer", "brûl", "brul", "feu de camp"),
    "eclairs": ("orage", "éclair", "eclair", "tempête", "tempete", "foudre"),
    "rayons": ("église", "eglise", "cathédrale", "vitrail", "faisceau", "rayon de lumière", "rayons de lumière",
               "projecteur", "lumière divine", "grenier"),
}


def light_from_desc(kind, desc):
    d = (desc or "").lower()
    return any(w in d for w in LUMIERES[kind])


def smoke_from_desc(desc):
    d = (desc or "").lower()
    for kind, words in FUMEES:
        if any(w in d for w in words):
            return kind
    return None


def _noise_texture(kind, w, h):
    """Texture de fumée : bruit « nuageux » en 1/f² obtenu par filtrage fréquentiel d'un bruit blanc.
    Une texture issue de la FFT est périodique : répétée 2×2, elle défile sans aucune couture."""
    key = ("fumee_tex", kind, w, h)
    if key not in S["cache"]:
        rng = np.random.default_rng(7 if kind == "fumee" else 11)
        spec = np.fft.fft2(rng.standard_normal((h, w)))
        fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
        f = np.sqrt(fx ** 2 + fy ** 2)
        f[0, 0] = 1.0
        acc = np.real(np.fft.ifft2(spec / (f + 3.0 / max(w, h)) ** 2.1)).astype(np.float32)
        acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)
        S["cache"][key] = np.tile(acc, (2, 2))            # répété : défilement sans couture
    return S["cache"][key]


def _smoke(frame, kind, t):
    """Fumée (volutes grises qui montent) ou brouillard (nappe basse qui dérive), en surimpression douce."""
    W, H = frame.size
    q = 4                                                 # calcul à 1/4 de résolution puis agrandi
    w, h = max(8, W // q), max(8, H // q)
    tex = _noise_texture(kind, w, h)
    dens = S.get("fumee_densite", 1.0)
    if kind == "fumee":
        ox1, oy1 = int(t * 6) % w, int(t * 14) % h        # couche lente qui monte
        ox2, oy2 = int(t * -9 + w / 3) % w, int(t * 22 + h / 2) % h
        l1 = tex[oy1:oy1 + h, ox1:ox1 + w]
        l2 = tex[oy2:oy2 + h, ox2:ox2 + w]
        m = np.clip((l1 * 0.6 + l2 * 0.4 - 0.35) * 2.2, 0, 1) ** 1.3
        grad = np.linspace(0.25, 1.0, h, dtype=np.float32)[:, None]     # plus dense en bas
        alpha = m * grad * 0.55 * dens
        color = (205, 205, 210)
    else:
        ox1, ox2 = int(t * 10) % w, int(t * -6 + w / 2) % w
        l1, l2 = tex[h // 3:h // 3 + h, ox1:ox1 + w], tex[h // 2:h // 2 + h, ox2:ox2 + w]
        m = np.clip((l1 * 0.5 + l2 * 0.5 - 0.25) * 1.8, 0, 1)
        y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        band = np.clip((y - 0.35) / 0.4, 0, 1)                           # nappe dans le bas
        alpha = (0.25 + 0.75 * m) * band * 0.6 * dens
        color = (228, 230, 236)
    a = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8), "L").resize((W, H), Image.BILINEAR)
    a = a.filter(ImageFilter.GaussianBlur(2))
    return Image.composite(Image.new("RGB", (W, H), color), frame, a)


def particles_from_desc(desc):
    d = (desc or "").lower()
    for kind, words in PARTICULES:
        if any(w in d for w in words):
            return kind
    return None


def section_at(segments):
    """[(début, section)] : section chantée à partir de chaque vers, « instrumental » dans les trous."""
    out = []
    segs = [s for s in segments if s["start"] is not None]
    for i, s in enumerate(segs):
        out.append((s["start"] - 0.5, (s["section"] or "").split()[0].lower() if s["section"] else ""))
        nxt = segs[i + 1]["start"] if i + 1 < len(segs) else None
        if nxt is None or nxt - s["end"] > 3.0:
            out.append((s["end"] + 1.0, "instrumental"))
    return out


def load_timeline(cfg, duration, descriptions=None):
    """cfg["timeline"] : [{"t": s, "img": "p1_c1"} | {"t": s, "travel": "solo1.png"}]
    Options : "fit" (cover|contain), "cy" (ancrage vertical 0=haut, 1=bas),
    "camera" (auto|zoom|pan|push|pull).
    Priorité : événement > cfg["ajustements"][image] > valeurs globales.
    Les ajustements par image survivent à « clip plan --force ».
    Variantes (cfg["variantes"]) : une image répétée change de sens de mouvement et est retournée
    une fois sur deux ; sa dernière apparition (si ≥ 3) passe presque en noir et blanc.
    → liste de plans (start, end, kind, src, opts)."""
    ev = sorted(cfg["timeline"], key=lambda e: e["t"])
    base = {"fit": cfg.get("fit", "cover"), "cy": cfg.get("cy", 0.4), "camera": cfg.get("camera", "zoom")}
    adj = cfg.get("ajustements") or {}
    descriptions = descriptions or {}
    variantes = cfg.get("variantes", False)
    total = {}
    for e in ev:
        if "img" in e:
            total[e["img"]] = total.get(e["img"], 0) + 1
    seen = {}
    shots = []
    for i, e in enumerate(ev):
        end = ev[i + 1]["t"] if i + 1 < len(ev) else duration
        if end <= e["t"]:
            continue
        src = e.get("img") or e.get("travel")
        a = adj.get(src, adj.get(Path(src).stem, {}))
        opts = {k: e.get(k, a.get(k, v)) for k, v in base.items()}
        # description de l'image : case (descriptions) ou photo de solo (son prompt, clé = nom sans extension)
        desc = descriptions.get(src) or descriptions.get(Path(src).stem.lower())
        if cfg.get("particules") == "auto":
            opts["fx"] = a.get("particules", particles_from_desc(desc))
        elif cfg.get("particules"):
            opts["fx"] = a.get("particules", cfg["particules"])
        elif "particules" in a:
            opts["fx"] = a["particules"]
        opts["fx_adj"] = "particules" in a
        fm = cfg.get("fumee")
        if "fumee" in a:                               # réglage par image prioritaire
            opts["smoke"] = a["fumee"]
        elif fm == "auto":
            opts["smoke"] = smoke_from_desc(desc)
        else:
            opts["smoke"] = fm or None
        for lk in ("flammes", "eclairs", "rayons"):    # null | auto | partout (+ ajustement par image)
            mode = cfg.get(lk)
            opts[lk] = bool(a[lk]) if lk in a else (light_from_desc(lk, desc) if mode == "auto" else mode == "partout")
        if "travel" in e:
            shots.append((e["t"], end, "travel", e["travel"], opts))
            continue
        img = e["img"]
        n = seen.get(img, 0)
        seen[img] = n + 1
        if opts["camera"] == "auto":
            opts["camera"] = camera_from_plan(desc)
        opts["dir"] = 1 if (len(shots) + n) % 2 == 0 else -1        # sens alterné
        opts["mirror"] = bool(variantes and n % 2 == 1)
        opts["desat"] = bool(variantes and total[img] >= 3 and n == total[img] - 1)
        shots.append((e["t"], end, "case", img, opts))
    return shots


# ---------------------------------------------------------------- worker state

S = {}


def _memoire_dispo():
    """Mémoire vive disponible (Mo) ; 8000 si inconnue."""
    try:
        if sys.platform == "win32":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullAvailPhys / 2**20
        dispo = None
        with open("/proc/meminfo") as f:                  # Linux
            for line in f:
                if line.startswith("MemAvailable:"):
                    dispo = int(line.split()[1]) / 1024
        for lim in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
            try:                                          # conteneur (Docker) : sa propre limite
                v = open(lim).read().strip()
                if v.isdigit():
                    dispo = min(dispo or 1e9, int(v) / 2**20)
            except OSError:
                pass
        return dispo or 8000
    except Exception:
        return 8000


def _init(state):
    S.update(state)
    S["cache"] = {}


def _pulse(t):
    if not S["pulse"]:
        return 0.0
    beats = S["beats"]
    i = bisect.bisect_left(beats, t - 0.30)
    p = 0.0
    while i < len(beats) and beats[i] < t + 0.10:
        d = t - beats[i]
        if -0.10 < d < 0.30:
            p = max(p, math.exp(d / -0.09))
        i += 1
    return p * S["pulse"]


def _harmonize(im, target, strength=0.5):
    """Rapproche moyenne / écart-type de chaque canal d'une cible commune au clip :
    les planches générées séparément prennent une colorimétrie cohérente."""
    a = np.asarray(im, dtype=np.float32)
    m, s = a.reshape(-1, 3).mean(0), a.reshape(-1, 3).std(0) + 1e-3
    tm, ts = np.array(target[0]), np.array(target[1])
    out = (a - m) / s * ts + tm
    out = a * (1 - strength) + out * strength
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def _embers(frame, t, seed):
    """Tisons ardents : chaque braise naît en bas, monte en ondulant, scintille puis s'éteint ;
    halo lumineux ajouté en mode « écran » (la braise éclaire l'image)."""
    from PIL import ImageChops
    W, H = frame.size
    k = min(W, H) / 1080
    rng = np.random.default_rng(seed)
    n = max(1, int(120 * S.get("densite", 1.0)))
    life = rng.uniform(2.5, 6.0, n)                       # durée de vie (s)
    off = rng.uniform(0, 6.0, n)
    x0 = rng.uniform(-0.05, 1.05, n) * W
    y0 = rng.uniform(0.70, 1.10, n) * H                   # naissent dans le bas de l'image
    rise = rng.uniform(0.5, 1.1, n) * H                   # distance parcourue sur une vie
    drift = rng.uniform(-110, 110, n) * k                 # dérive latérale (vent chaud)
    size = rng.uniform(1.8, 4.2, n) * k
    size[rng.random(n) < 0.12] *= 1.8                     # quelques grosses braises bien vives
    phase = rng.uniform(0, 6.28, n)
    hue = rng.uniform(0, 1, n)                            # 0 = rouge orangé, 1 = jaune
    u = ((t + off) % life) / life                         # âge relatif 0 → 1
    wob = 22 * k * np.sin(t * 2.1 + phase)
    xs = x0 + drift * u + wob
    ys = y0 - rise * u
    vx = drift / life + 22 * k * 2.1 * np.cos(t * 2.1 + phase)   # vitesse (px/s) → traînée
    vy = -rise / life
    glow = np.sin(np.pi * u) ** 0.7 * (0.6 + 0.4 * np.sin(t * 13 + phase * 3))  # naissance, extinction, scintillement
    s = 2                                                 # halo calculé à demi-résolution (rapide)
    halo = Image.new("RGB", (W // s, H // s), (0, 0, 0))
    core = Image.new("RGB", (W, H), (0, 0, 0))
    dh, dc = ImageDraw.Draw(halo), ImageDraw.Draw(core)
    for x, y, r, g, h, ax, ay in zip(xs, ys, size * (1.15 - 0.55 * u), glow, hue, vx, vy):
        if g <= 0.03 or y < -30:
            continue
        col = (255, int(80 + 130 * h), int(15 + 45 * h))
        R = r * 5 / s
        dh.ellipse((x / s - R, y / s - R, x / s + R, y / s + R), fill=tuple(int(c * 0.6 * g) for c in col))
        hot = tuple(int(c * g) for c in (255, 200 + int(40 * h), 120 + int(60 * h)))
        dc.line((x, y, x - ax * 0.045, y - ay * 0.045), fill=hot, width=max(1, int(r)))   # traînée
        dc.ellipse((x - r, y - r, x + r, y + r), fill=tuple(min(255, int(c * 1.15)) for c in hot))
    halo = halo.filter(ImageFilter.GaussianBlur(4 * k)).resize((W, H), Image.BILINEAR)
    light = ImageChops.add(halo, core.filter(ImageFilter.GaussianBlur(0.7 * k)))
    return ImageChops.screen(frame, light)


def _particles(frame, kind, t, seed):
    """Neige (flocons qui tombent en ondulant), poussière lumineuse (points chauds qui montent)
    ou braises (tisons ardents qui montent et scintillent)."""
    if kind == "braises":
        return _embers(frame, t, seed)
    new = {"pluie": FX.rain, "confettis": FX.confetti, "bokeh": FX.bokeh, "etincelles": FX.sparks}
    if kind in new:
        return new[kind](frame, t, seed, S.get("densite", 1.0))
    W, H = frame.size
    rng = np.random.default_rng(seed)
    n = max(1, int((170 if kind == "neige" else 70) * S.get("densite", 1.0)))
    x0, y0 = rng.uniform(0, W, n), rng.uniform(0, H, n)
    speed = rng.uniform(40, 140, n) * (min(W, H) / 1080)
    size = rng.uniform(1.5, 5.0, n) * (min(W, H) / 1080)
    phase = rng.uniform(0, 6.28, n)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if kind == "neige":
        ys = (y0 + speed * t) % H
        xs = (x0 + 25 * np.sin(t * 0.8 + phase)) % W
        color = [(255, 255, 255, int(a)) for a in rng.uniform(110, 220, n)]
    else:
        ys = (y0 - speed * 0.25 * t) % H
        xs = (x0 + 15 * np.sin(t * 0.5 + phase)) % W
        size = size * 0.7
        color = [(255, 214, 160, int(a * (0.6 + 0.4 * math.sin(t * 1.3 + p))))
                 for a, p in zip(rng.uniform(60, 130, n), phase)]
    for x, y, r, c in zip(xs, ys, size, color):
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    if kind == "neige":
        layer = layer.filter(ImageFilter.GaussianBlur(0.8))
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def _case_base(name, fit, mirror=False, desat=False, tone=None):
    """Image de case préparée à la taille de couverture × marge de zoom."""
    key = ("case", name, fit, mirror, desat, tone)
    if key in S["cache"]:
        return S["cache"][key]
    W, H = S["size"]
    path = next(S["cases"].glob(f"{name}.*"))
    im = Image.open(path).convert("RGB")
    if S.get("harmo"):
        im = _harmonize(im, S["harmo"])
    if mirror:
        im = ImageOps.mirror(im)
    if desat:
        grey = ImageOps.grayscale(im).convert("RGB")
        im = Image.blend(im, grey, 0.85)
    if tone and tone != (1.0, 1.0):
        im = ImageEnhance.Color(ImageEnhance.Brightness(im).enhance(tone[0])).enhance(tone[1])
    margin = 1.12                         # zoom max ≈ 1.10
    if fit == "contain":
        # case entière au centre, même image floutée en fond
        bg_s = max(W / im.width, H / im.height) * margin
        bg = im.resize((int(im.width * bg_s), int(im.height * bg_s)), Image.BILINEAR)
        bg = bg.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.45))
        fg_s = min(W * margin / im.width, H * margin / im.height)
        fg = im.resize((int(im.width * fg_s), int(im.height * fg_s)), Image.LANCZOS)
        bg.paste(fg, ((bg.width - fg.width) // 2, (bg.height - fg.height) // 2))
        base = bg
    else:
        s = max(W / im.width, H / im.height) * margin
        base = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    S["cache"][key] = base
    return base


def _pano(name, tone=None):
    key = ("pano", name, tone)
    if key not in S["cache"]:
        H = S["size"][1]
        im = Image.open(S["solos"] / name).convert("RGB")
        if S.get("harmo"):
            im = _harmonize(im, S["harmo"])
        if tone and tone != (1.0, 1.0):
            im = ImageEnhance.Color(ImageEnhance.Brightness(im).enhance(tone[0])).enhance(tone[1])
        s = H * 1.10 / im.height
        S["cache"][key] = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    return S["cache"][key]


def _crop_box(size, zoom, cx=0.5, cy=0.5):
    W, H = S["inner"]                     # zone image (hors bandes noires éventuelles)
    bw, bh = size
    # la base couvre W×H × marge 1.12 : zoom 1.0 = marge conservée, le zoom resserre
    scale = min(bw / W, bh / H) / 1.12
    ww, wh = W * scale / zoom, H * scale / zoom
    left = (bw - ww) * cx
    top = (bh - wh) * cy
    return (left, top, left + ww, top + wh)


def _crop_zoom(base, zoom, cx=0.5, cy=0.5):
    return base.resize(S["inner"], Image.BILINEAR, box=_crop_box(base.size, zoom, cx, cy))


def _depth(name, mirror, size):
    """Carte de profondeur (PIL mode F, 1 = proche) alignée sur la base de la case, ou None."""
    import cv2
    key = ("depth", name, mirror, size)
    if key not in S["cache"]:
        f = S["depth_dir"] / f"{name}.png"
        d = None
        if f.exists():
            d = cv2.imread(str(f), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0
            if mirror:
                d = np.ascontiguousarray(d[:, ::-1])
            d = cv2.resize(d, size, interpolation=cv2.INTER_LINEAR)
            k = max(3, int(size[0] * 0.012)) | 1        # adoucit les bords → moins de déchirures
            d = Image.fromarray(cv2.GaussianBlur(d, (k, k), 0), mode="F")
        S["cache"][key] = d
    return S["cache"][key]


def _parallax(base, depth, cam, e, opts, extra_zoom):
    """Caméra 3D : chaque pixel est déplacé selon sa profondeur.
    pan / zoom → orbite latérale (le premier plan glisse plus que le fond) ;
    push / pull → travelling avant / arrière (le premier plan grossit plus que le fond)."""
    import cv2
    W, H = S["inner"]
    box = _crop_box(base.size, 1.05 + extra_zoom, 0.5, opts["cy"])
    img = np.asarray(base.resize((W, H), Image.BILINEAR, box=box))
    D = np.asarray(depth.resize((W, H), Image.BILINEAR, box=box))
    if "grid" not in S:
        S["grid"] = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    X, Y = S["grid"]
    a = S["parallaxe"]
    if cam in ("push", "pull"):
        k = a * 2.5 * (e if cam == "push" else 1 - e)
        s = 1 + k * D
        cx, cy = W / 2, H * 0.45
        mx, my = cx + (X - cx) / s, cy + (Y - cy) / s
    else:
        dx = a * W * (e - 0.5) * 2 * opts.get("dir", 1)
        mx, my = X - dx * (D - 0.5), Y - 0.2 * dx * (D - 0.5)
    out = cv2.remap(img, mx.astype(np.float32), my.astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(out)


def _shot_frame(shot, t):
    start, end, kind, src, opts = shot
    p = _pulse(t)
    if kind == "video":
        # vidéo (ex. générée avec Flow) : lue depuis le début à chaque apparition ; si le plan est plus
        # long que la vidéo, elle est légèrement ralentie pour le couvrir (jamais figée)
        n = opts["nframes"]
        if end - start > n / S["fps"]:
            u = min(max((t - start) / max(end - start, 1e-6), 0.0), 1.0)
            idx = int(u * (n - 1))
        else:
            idx = min(n - 1, max(0, int((t - start) * S["fps"])))
        frame = Image.open(Path(src) / f"{idx + 1:05d}.jpg").convert("RGB")
        if frame.size != S["inner"]:
            frame = frame.resize(S["inner"], Image.BILINEAR)
        flash = 0.18
    elif kind == "travel":
        u = min(max((t - start) / max(end - start, 1e-6), 0.0), 1.0)   # borné : fondus hors plan
        ease = (1 - math.cos(u * math.pi)) / 2
        frame = _crop_zoom(_pano(src, opts.get("tone")), (1.0 + 0.06 * ease) * (1.0 + 0.02 * p), cx=ease)
        flash = 0.18
    else:
        base = _case_base(src, opts["fit"], opts.get("mirror", False), opts.get("desat", False),
                          opts.get("tone"))
        u = min(max((t - start) / max(end - start, 1e-6), 0.0), 1.0)
        e = u * u * (3 - 2 * u)                         # lissage début / fin
        ca = S.get("cam_amp", 1.0)
        amp = 0.10 * ca * min(1.0, (end - start) / 5.0)  # plans courts : mouvement plus doux
        cam, cx = opts.get("camera", "zoom"), 0.5
        if cam == "pan":
            zoom = 1.06
            cx = 0.5 + opts.get("dir", 1) * (e - 0.5) * min(0.95, 0.9 * ca) * min(1.0, (end - start) / 4.0)
        elif cam == "push":
            zoom = 1.0 + amp * e
        elif cam == "pull":
            zoom = 1.0 + amp * (1 - e)
        else:                                            # « zoom » : oscillation historique
            zoom = 1.0 + 0.05 * S.get("cam_amp", 1.0) * math.sin(t * 0.6)
        depth = None
        if S.get("parallaxe") and opts.get("parallaxe", True) and opts["fit"] == "cover":
            depth = _depth(src, opts.get("mirror", False), base.size)
        if depth is not None:
            frame = _parallax(base, depth, cam, e, opts, 0.05 * p)
            box = _crop_box(base.size, 1.05 + 0.05 * p, 0.5, opts["cy"])
        else:
            box = _crop_box(base.size, max(zoom + 0.05 * p, 0.9), cx, opts["cy"])
            frame = base.resize(S["inner"], Image.BILINEAR, box=box)
        if (S.get("flou_fond") or S.get("brume_prof")) and opts["fit"] == "cover" and opts.get("parallaxe", True):
            dimg = _depth(src, opts.get("mirror", False), base.size)
            if dimg is not None:
                D = dimg.resize(S["inner"], Image.BILINEAR, box=box)
                frame = FX.depth_blur(frame, D, S.get("flou_fond", 0))
                frame = FX.depth_fog(frame, D, S.get("brume_prof", 0))
        flash = 0.22
    if p > 0.5:
        frame = Image.blend(frame, Image.new("RGB", frame.size, (255, 255, 255)), (p - 0.5) * flash)
    if opts.get("flammes"):                            # feu au pied de l'image, sous la fumée et les braises
        frame = FX.fire(frame, t, S.get("flammes_hauteur", 0.3), S.get("flammes_intensite", 1.0))
    if opts.get("smoke"):                              # fumée derrière les particules (braises devant)
        frame = _smoke(frame, opts["smoke"], t)
    if opts.get("rayons"):
        W, H = frame.size
        frame = FX.god_rays(frame, t, S.get("rayons_intensite", 1.0), _noise_texture("fumee", max(8, W // 4), max(8, H // 4)))
    if opts.get("fx"):
        frame = _particles(frame, opts["fx"], t, seed=int(start * 1000) % 2 ** 31)
    if opts.get("eclairs"):
        frame = FX.lightning(frame, t, seed=int(start * 100) % 10000)
    return frame


def _transition(A, B, w, kind):
    """Mélange de deux plans pendant une transition (w : 0 = plan A, 1 = plan B)."""
    w = min(max(w, 0.0), 1.0)
    if kind == "noir" or kind == "flash":
        mid = Image.new("RGB", A.size, (0, 0, 0) if kind == "noir" else (255, 255, 255))
        return Image.blend(A, mid, w * 2) if w < 0.5 else Image.blend(mid, B, (w - 0.5) * 2)
    if kind == "glissement":
        e = w * w * (3 - 2 * w)
        W = A.width
        out = Image.new("RGB", A.size)
        out.paste(A, (int(-e * W), 0))
        out.paste(B, (int((1 - e) * W), 0))
        return out
    if kind == "zoom":
        z = 1 + 0.35 * w                                  # le plan A s'enfonce en s'effaçant
        W, H = A.size
        ww, hh = W / z, H / z
        A = A.resize((W, H), Image.BILINEAR, box=((W - ww) / 2, (H - hh) / 2, (W + ww) / 2, (H + hh) / 2))
    return Image.blend(A, B, w)


def _beat_env(t):
    """Enveloppe du beat le plus proche (0-1), indépendante du réglage « effet au beat », + n° du beat."""
    beats = S["beats"]
    i = bisect.bisect_left(beats, t - 0.30)
    env, idx = 0.0, max(0, i - 1)
    while i < len(beats) and beats[i] < t + 0.10:
        d = t - beats[i]
        if -0.10 < d < 0.30 and math.exp(d / -0.09) > env:
            env, idx = math.exp(d / -0.09), i
        i += 1
    return min(env, 1.0), idx


def _section(t):
    j = bisect.bisect_right(S["sec_t"], t) - 1
    return S["sec_k"][j] if j >= 0 else "intro"


def _post_effects(frame, t, starts):
    """Effets appliqués à l'image complète : lumière, rythme, pellicule, son."""
    env, bi = _beat_env(t)
    k = bisect.bisect_right(starts, t)
    near_cut = min((abs(t - starts[j]) for j in (k - 1, k) if 0 <= j < len(starts)), default=9)
    if S.get("fuites"):
        frame = FX.light_leaks(frame, t, S["fuites"], boost=max(0.0, 1 - near_cut / 0.8))
    if S.get("projecteurs"):
        frame = FX.spotlights(frame, env, bi, S["projecteurs"])
    zone_ok = S.get("trem_zone", "partout") == "partout" or _section(t) == "refrain"
    if S.get("tremblement") and zone_ok:
        frame = FX.shake(frame, t, env * S["tremblement"])
    if S.get("rvb"):
        frame = FX.rgb_split(frame, env * S["rvb"])
    g = S.get("glitch")
    if g:
        hit = False
        if g in ("beats", "les_deux") and env > 0.55:
            hit = np.random.default_rng(bi * 7919).random() < 0.35   # ~1 beat sur 3
        if g in ("transitions", "les_deux") and near_cut < 0.12:
            hit = True
        if hit:
            frame = FX.glitch(frame, t, seed=int(t * 30), intensity=S.get("glitch_intensite", 1.0))
    if S.get("vieux_film"):
        frame = FX.old_film(frame, t, S["vieux_film"])
    vis = S.get("vis_data")
    if vis is not None:
        fi = min(len(vis) - 1, int(round(t * S["fps"])))
        paroles = any(a <= t < b for a, b in S["bar_spans"])
        if fi >= 0 and (S["vis_zone"] == "partout" or not paroles):
            frame = FX.visualizer(frame, vis[fi], S["vis_style"], S["vis_couleur"], S["vis_hauteur"])
    return frame


def _render(fi):
    t = fi / S["fps"]
    shots, starts = S["shots"], S["starts"]
    k = max(0, bisect.bisect_right(starts, t) - 1)
    half = S["fondu"] / 2 if S["transition"] != "coupe" else 0
    # transition centrée sur la coupe : commence half avant, finit half après
    if half and k + 1 < len(shots) and t >= starts[k + 1] - half:
        a, b = k, k + 1
    elif half and k > 0 and t < starts[k] + half:
        a, b = k - 1, k
    else:
        a = b = k
    frame = _shot_frame(shots[b], t)
    if a != b:
        w = (t - (starts[b] - half)) / (2 * half)
        frame = _transition(_shot_frame(shots[a], t), frame, w, S["transition"])
    frame = _post_effects(frame, t, starts)
    if S["inner"] != S["size"]:                          # bandes noires cinéma
        canvas = Image.new("RGB", S["size"], (0, 0, 0))
        canvas.paste(frame, (0, (S["size"][1] - S["inner"][1]) // 2))
        frame = canvas
    elif S["bar"] is not None and any(a <= t < b for a, b in S["bar_spans"]):
        frame.paste(S["bar"], (0, S["bar_y"]), S["bar"])
    if S.get("logo") is not None:
        frame.paste(S["logo"], S["logo_pos"], S["logo"])
    return frame.tobytes()


# ---------------------------------------------------------------- karaoké ASS

def _ass_time(t):
    t = max(0.0, t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ass_color(hex_rgb, alpha=0):
    """#RRGGBB → &HAABBGGRR& (ASS)."""
    h = (hex_rgb or "#FFFFFF").lstrip("#")
    h = (h + "FFFFFF")[:6]
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def _fill_times(words, seg_start, seg_end):
    """Complète les mots non alignés par interpolation."""
    out, n = [], len(words)
    for i, w in enumerate(words):
        s, e = w["s"], w["e"]
        if s is None:
            s = seg_start + (seg_end - seg_start) * i / n
            e = seg_start + (seg_end - seg_start) * (i + 1) / n
        out.append((w["w"], s, e))
    return out


ALIGN = {"bas": 2, "haut": 8, "centre": 5}
CORNERS = {"haut-gauche": 7, "haut-droite": 9, "bas-gauche": 1, "bas-droite": 3}


def write_ass(segments, path, size, k, titles=(), mention=None):
    """Karaoké + titres. k : réglages (voir karaoke_opts). Retourne les plages où une ligne est affichée."""
    W, H = size
    sc, fs = k["scale"], int(k["taille"] * k["scale"])
    act, txtc = _ass_color(k["couleur"]), _ass_color(k["texte"])
    al, mv = ALIGN.get(k["position"], 2), int(k["margin_v"])
    out_w = max(1, int(3 * sc))
    nfs = int(fs * 0.72)
    # avec la ligne suivante : la ligne chantée se décale pour laisser la place
    mv_k = mv + int(nfs * 1.25) if k["suivante"] and al == 2 else mv
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: K,{k['police']},{fs},{txtc},{txtc},&H00000000&,&H00000000&,-1,0,0,0,100,100,0,0,1,"
        f"{out_w},0,{al},{int(60 * sc)},{int(60 * sc)},{mv_k},1",
        # remplissage progressif (\kf) : Primary = couleur remplie, Secondary = couleur de départ
        f"Style: KF,{k['police']},{fs},{act},{txtc},&H00000000&,&H00000000&,-1,0,0,0,100,100,0,0,1,"
        f"{out_w},0,{al},{int(60 * sc)},{int(60 * sc)},{mv_k},1",
        f"Style: N,{k['police']},{nfs},{_ass_color(k['texte'], 0x70)},{txtc},&H40000000&,&H00000000&,-1,0,0,0,"
        f"100,100,0,0,1,{max(1, out_w - 1)},0,{al},{int(60 * sc)},{int(60 * sc)},{mv},1",
        f"Style: T,{k['police']},{int(110 * sc)},{WHITE_ASS},{WHITE_ASS},&H00000000&,&H80000000&,-1,0,0,0,"
        f"100,100,{int(12 * sc)},0,1,{max(1, int(2 * sc))},{max(1, int(4 * sc))},5,0,0,0,1",
        f"Style: G,{k['police']},{int(54 * sc)},{WHITE_ASS},{WHITE_ASS},&H00000000&,&H80000000&,-1,0,0,0,"
        f"100,100,{int(6 * sc)},0,1,{max(1, int(2 * sc))},{max(1, int(3 * sc))},5,0,0,0,1",
        f"Style: M,{k['police']},{int(30 * sc)},&H50FFFFFF&,&H50FFFFFF&,&H80000000&,&H00000000&,-1,0,0,0,"
        f"100,100,{int(2 * sc)},0,1,{max(1, int(2 * sc))},0,{CORNERS.get((mention or {}).get('coin'), 3)},"
        f"{int(30 * sc)},{int(30 * sc)},{int(24 * sc)},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for a, b, text, style in titles:
        lines.append(f"Dialogue: 1,{_ass_time(a)},{_ass_time(b)},{style},,0,0,0,,{{\\fad(900,900)}}{text}")
    if mention:
        lines.append(f"Dialogue: 2,{_ass_time(mention['debut'])},{_ass_time(mention['fin'])},M,,0,0,0,,"
                     f"{mention['texte']}")
    spans = []
    if k["mode"] == "aucun":
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return spans
    d = k["decalage"]
    up = (lambda s: s.upper()) if k["majuscules"] else (lambda s: s)
    segs = [s for s in segments if s["start"] is not None]
    for i, seg in enumerate(segs):
        words = [(up(w), s + d, e + d) for w, s, e in _fill_times(seg["words"], seg["start"], seg["end"])]
        show = seg["start"] + d - 0.25
        nxt = segs[i + 1]["start"] + d - 0.25 if i + 1 < len(segs) else seg["end"] + d + 1.0
        hide = min(seg["end"] + d + 0.6, nxt)
        spans.append((show, hide))
        if k["suivante"] and i + 1 < len(segs) and segs[i + 1]["start"] - seg["end"] < 4.0:
            nt = up(segs[i + 1]["text"])
            pos = f"{{\\an5\\pos({W // 2},{H // 2 + int(fs * 1.15)})}}" if al == 5 else \
                  (f"{{\\an8\\pos({W // 2},{mv + int(fs * 1.35)})}}" if al == 8 else "")
            lines.append(f"Dialogue: 0,{_ass_time(show)},{_ass_time(hide)},N,,0,0,0,,{pos}{nt}")
        if k["mode"] == "ligne":                            # sous-titre simple : ligne entière
            lines.append(f"Dialogue: 0,{_ass_time(show)},{_ass_time(hide)},K,,0,0,0,,"
                         + " ".join(w[0] for w in words))
            continue
        if k["animation"] == "remplir":                     # remplissage progressif mot par mot
            parts = [f"{{\\k{max(0, int(round((words[0][1] - show) * 100)))}}}"]
            for j, (w, s, e) in enumerate(words):
                nxt_s = words[j + 1][1] if j + 1 < len(words) else e
                parts.append(f"{{\\kf{max(1, int(round((nxt_s - s) * 100)))}}}{w} ")
            lines.append(f"Dialogue: 0,{_ass_time(show)},{_ass_time(hide)},KF,,0,0,0,,{''.join(parts).rstrip()}")
            continue
        big = "\\fscx118\\fscy118" if k["animation"] == "grossir" else ""
        norm = "\\fscx100\\fscy100" if big else ""

        def line(active):
            return " ".join((f"{{\\c{act}{big}}}{w[0]}{{\\c{txtc}{norm}}}" if j == active else w[0])
                            for j, w in enumerate(words))
        # un événement par état : aucun mot / mot k surligné (jusqu'au début du suivant)
        marks = [show] + [w[1] for w in words] + [hide]
        for j in range(len(words)):
            a, b = marks[j], marks[j + 1]
            if b > a:
                lines.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},K,,0,0,0,,{line(j - 1)}")
        lines.append(f"Dialogue: 0,{_ass_time(words[-1][1])},{_ass_time(hide)},K,,0,0,0,,{line(len(words) - 1)}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return spans


# ---------------------------------------------------------------- encodage

def _amf_ok():
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=640x360:d=0.2",
                        "-c:v", "h264_amf", "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


def _video_codec(encoder, preview, pixels=1920 * 1080):
    if preview:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"]
    # débit plafonné (~12 Mb/s en 1080p, recommandation YouTube ; ×3 en 4K) : sans plafond, le grain
    # de film (bruit différent à chaque image) fait exploser la taille (2,7 Go pour 3 min)
    r = max(1.0, pixels / (1920 * 1080)) ** 0.8
    b, mx, bs = f"{int(12 * r)}M", f"{int(16 * r)}M", f"{int(24 * r)}M"
    if encoder == "amf" or (encoder == "auto" and _amf_ok()):
        return ["-c:v", "h264_amf", "-quality", "quality", "-rc", "vbr_peak", "-b:v", b, "-maxrate", mx, "-bufsize", bs]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-maxrate", mx, "-bufsize", bs]


# étalonnages (couleur) ; grain et vignettage ajoutés séparément, avec des valeurs par défaut par look
LOOKS = {
    "aucun": ("", 0, 0.0),
    "cinema": ("eq=contrast=1.06:saturation=0.92:gamma=0.98,"
               "colorbalance=rs=-0.03:bs=0.04:rh=0.04:gh=0.01:bh=-0.03", 7, 0.7),
    "nb": ("hue=s=0,eq=contrast=1.12", 6, 0.6),
    "sepia": ("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.05", 5, 0.7),
    "vhs": ("rgbashift=rh=-3:bh=3,eq=saturation=1.25:contrast=1.08,gblur=sigma=0.7,"
            "drawgrid=w=iw:h=4:t=1:c=black@0.18", 11, 0.5),
    "neon": ("eq=saturation=1.6:contrast=1.15:gamma=0.95", 0, 0.8),
    "froid": ("colorbalance=rs=-0.05:bs=0.08:rm=-0.03:bm=0.05,eq=saturation=0.75:contrast=1.05", 5, 0.6),
}
FORMATS = {"16:9": (1920, 1080), "4k": (3840, 2160), "9:16": (1080, 1920), "1:1": (1080, 1080)}
SUFFIXES = {"4k": "_4k", "9:16": "_vertical", "1:1": "_carre"}
SECTION_KEYS = {"chorus": "refrain", "refrain": "refrain", "verse": "couplet", "couplet": "couplet",
                "bridge": "pont", "pont": "pont", "outro": "outro", "intro": "intro",
                "instrumental": "instrumental"}


def look_filter(cfg):
    base, g0, v0 = LOOKS.get(cfg.get("look", "aucun"), LOOKS["aucun"])
    grain = cfg.get("grain")
    grain = g0 if grain is None else float(grain)
    vign = cfg.get("vignettage")
    vign = v0 if vign is None else float(vign)
    parts = [base] if base else []
    lum, con = float(cfg.get("luminosite") or 0), float(cfg.get("contraste") or 1)
    if lum or con != 1:
        parts.append(f"eq=brightness={lum:.3f}:contrast={con:.3f}")
    if vign > 0:
        parts.append(f"vignette=angle={min(1.4, vign * 0.9):.3f}")
    if grain > 0:
        parts.append(f"noise=alls={int(grain)}:allf=t")
    return ",".join(parts)


def _descriptions(projet_dir, cfg):
    desc = dict(cfg.get("descriptions") or {})
    f = projet_dir / "build" / "descriptions.json"
    if f.exists():
        desc.update(json.loads(f.read_text(encoding="utf-8-sig")))
    fs = projet_dir / "build" / "solos.json"             # photos de solo : leur prompt sert de description
    if fs.exists():
        for i, s in enumerate(json.loads(fs.read_text(encoding="utf-8-sig")).get("solos", []), 1):
            desc.setdefault(f"solo{i}", s.get("prompt", ""))
    return desc


def _harmo_target(projet_dir, shots):
    """Moyenne / écart-type RVB communs à toutes les cases utilisées (sur vignettes réduites)."""
    ms, ss = [], []
    for name in sorted({s[3] for s in shots if s[2] == "case"}):
        f = next((projet_dir / "cases").glob(f"{name}.*"), None)
        if f is None:
            continue
        im = Image.open(f).convert("RGB")
        im.thumbnail((160, 160))
        a = np.asarray(im, dtype=np.float32).reshape(-1, 3)
        ms.append(a.mean(0)), ss.append(a.std(0))
    return (np.mean(ms, 0).tolist(), np.mean(ss, 0).tolist()) if ms else None


def _titles(cfg, segments, d0, d1, scale):
    """Titre d'ouverture (fondu sur l'intro, avant le 1er vers) et générique de fin."""
    titre = cfg.get("titre")
    if not titre:
        return []
    artiste = cfg.get("artiste")
    first = min((s["start"] for s in segments if s["start"] is not None and s["start"] >= d0), default=d0 + 10)
    end_t = max(d0 + 3.0, min(first - 1.0, d0 + 9.0))
    sub = f"\\N{{\\fs{int(52 * scale)}}}{artiste}" if artiste else ""
    out = [(d0 + 1.0, end_t, f"{titre}{sub}", "T")]
    if cfg.get("generique", True):
        out.append((d1 - 7.0, d1, " — ".join(x for x in (titre, artiste) if x), "G"))
    return out


def _downbeats(beats, segments):
    """Garde 1 beat sur 4 (1er temps de la mesure) : phase choisie pour coïncider au mieux
    avec les débuts de vers, qui tombent en général sur un temps fort."""
    starts = [s["start"] for s in segments if s["start"] is not None]

    def score(ph):
        sel = beats[ph::4]
        return sum(1 for t in starts if sel and min(abs(b - t) for b in sel) < 0.15)
    return beats[max(range(4), key=score)::4]


def _split_long(shots, maxd):
    """Découpe les plans d'image trop longs en plusieurs mouvements de caméra (sens inversé,
    zoom avant ↔ arrière) : l'image reste, mais le plan ne lasse plus."""
    out = []
    swap = {"push": "pull", "pull": "push"}
    for s in shots:
        start, end, kind, src, opts = s
        n = int(math.ceil((end - start) / maxd)) if kind == "case" and maxd > 0 else 1
        if n <= 1:
            out.append(s)
            continue
        for j in range(n):
            o = dict(opts)
            if j % 2:
                o["dir"] = -o.get("dir", 1)
                o["camera"] = swap.get(o.get("camera"), o.get("camera"))
            out.append((start + (end - start) * j / n, start + (end - start) * (j + 1) / n, kind, src, o))
    return out


VIDEO_EXT = (".mp4", ".mov", ".webm", ".m4v")


def _use_videos(projet_dir, shots, size, fps):
    """Une vidéo videos/<id>.mp4 (id = p1_c2, solo1…) remplace cette image partout où elle apparaît.
    Ses images sont extraites une fois (à la taille et à la cadence du rendu) dans build/video_frames/."""
    vdir = projet_dir / "videos"
    if not vdir.is_dir():
        return shots
    vids = {f.stem.lower(): f for f in vdir.iterdir() if f.suffix.lower() in VIDEO_EXT}
    if not vids:
        return shots
    W, H = size
    out, done = [], {}
    for s in shots:
        start, end, kind, src, opts = s
        key = Path(src).stem.lower()
        if key not in vids:
            out.append(s)
            continue
        if key not in done:
            v = vids[key]
            d = projet_dir / "build" / "video_frames" / f"{key}_{W}x{H}_{fps}"
            if not d.is_dir() or not any(d.iterdir()) or d.stat().st_mtime < v.stat().st_mtime:
                d.mkdir(parents=True, exist_ok=True)
                for old in d.glob("*.jpg"):
                    old.unlink()
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-an",
                                "-vf", f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                                "-q:v", "3", str(d / "%05d.jpg")], check=True)
            n = len(list(d.glob("*.jpg")))
            done[key] = (str(d), n)
            print(f"  vidéo {v.name} : {n} images ({n / fps:.1f} s) → remplace {key}")
        d, n = done[key]
        if n:
            out.append((start, end, "video", d, {**opts, "nframes": n}))
        else:
            out.append(s)
    return out


def karaoke_opts(cfg, scale, lb, W, H):
    pos = cfg.get("karaoke_position", "bas")
    taille = float(cfg.get("karaoke_taille") or 46)
    fs = taille * scale
    if lb:                                             # bandes noires : texte centré dans la bande
        mv = max(4, (lb - fs * 1.2) / 2)
    else:
        mv = 80 * scale if pos != "centre" else 0
    return {"scale": scale, "taille": taille, "police": cfg.get("font") or "Arial",
            "couleur": cfg.get("karaoke_couleur") or "#FFDC50", "texte": cfg.get("karaoke_texte") or "#FFFFFF",
            "position": pos, "margin_v": mv, "mode": cfg.get("karaoke_mode", "mot"),
            "animation": cfg.get("karaoke_animation", "aucune"), "suivante": bool(cfg.get("karaoke_suivante")),
            "majuscules": bool(cfg.get("karaoke_majuscules")), "decalage": float(cfg.get("karaoke_decalage") or 0)}


def _logo(projet_dir, cfg, W, H):
    name = cfg.get("logo")
    if not name or not (projet_dir / name).exists():
        return None, (0, 0)
    im = Image.open(projet_dir / name).convert("RGBA")
    h = max(8, int(min(W, H) * 0.09))
    im = im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)
    a = im.getchannel("A").point(lambda v: int(v * 0.85))
    im.putalpha(a)
    m = int(min(W, H) * 0.03)
    coin = cfg.get("logo_position", "haut-droite")
    x = m if "gauche" in coin else W - im.width - m
    y = m if "haut" in coin else H - im.height - m
    return im, (x, y)


def render(projet_dir, cfg, preview=False, start=None, duration=None, workers=None, out_name=None):
    projet_dir = Path(projet_dir)
    build = projet_dir / "build"
    audio = projet_dir / cfg["audio"]
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "csv=p=0", str(audio)], capture_output=True, text=True).stdout)
    # fenêtre utile de la chanson (début / fin coupés)
    d0 = min(max(0.0, float(cfg.get("debut") or 0)), total - 1)
    d1 = float(cfg.get("fin") or 0)
    d1 = total if d1 <= d0 else min(d1, total)
    extrait = start is not None or duration is not None
    start = d0 if start is None else max(d0, float(start))
    end = min(d1, start + duration) if duration else d1

    scale = 0.5 if preview else 1.0
    fps = 15 if preview else cfg.get("fps", 30)
    fmt = cfg.get("format", "16:9")
    base_w, base_h = FORMATS.get(fmt, tuple(cfg.get("size") or (1920, 1080)))
    W, H = int(base_w * scale) // 2 * 2, int(base_h * scale) // 2 * 2
    ts = min(W, H) / 1080                              # échelle du texte et des effets
    if H > W:                                          # vertical : vu sur téléphone → texte plus grand
        ts *= 1.4
    # bandes noires cinéma (2,39:1) : seulement en format paysage
    lb = (H - int(W / 2.39)) // 2 // 2 * 2 if cfg.get("letterbox") and W > H else 0
    inner = (W, H - 2 * lb)

    shots = load_timeline(cfg, total, _descriptions(projet_dir, cfg))
    segments = json.loads((build / "words.json").read_text(encoding="utf-8"))["segments"]
    secs = section_at(segments)
    sec_t = [a for a, _ in secs]

    def section_of(s):
        j = bisect.bisect_right(sec_t, (s[0] + s[1]) / 2) - 1
        return secs[j][1] if j >= 0 else "intro"
    ps = {k: v for k, v in (cfg.get("particules_sections") or {}).items() if v and v != "auto"}
    for s in shots:
        if cfg.get("look_sections"):                  # tonalité selon la section chantée
            s[4]["tone"] = SECTION_TONES.get(section_of(s), (1.0, 1.0))
        key = SECTION_KEYS.get(section_of(s))
        if key in ps and not s[4].get("fx_adj"):      # particules imposées pour cette section
            s[4]["fx"] = None if ps[key] == "aucune" else ps[key]
    maxd = float(cfg.get("duree_max_image") or 0)
    if maxd > 0:
        shots = _split_long(shots, maxd)
    shots = _use_videos(projet_dir, shots, inner, fps)

    k = karaoke_opts(cfg, ts, lb, W, H)
    ment = None
    if cfg.get("mention_ia_ecran"):
        ment = {"texte": cfg.get("mention_ia_texte") or "Version IA", "coin": cfg.get("mention_ia_position", "bas-droite"),
                "debut": d0, "fin": d1}
    ass = build / ("preview.ass" if preview else "karaoke.ass")
    spans = write_ass(segments, ass, (W, H), k, titles=_titles(cfg, segments, d0, d1, ts), mention=ment)
    beats = np.load(build / "beats.npy").tolist()
    if cfg.get("pulse_mesure"):
        beats = _downbeats(beats, segments)

    # bandeau en dégradé sous (ou sur) les paroles, sauf au centre ou avec les bandes noires
    bar, bar_y = None, 0
    if not lb and k["mode"] != "aucun" and k["position"] in ("bas", "haut"):
        bar_h = int(200 * ts * (1.35 if k["suivante"] else 1))
        top = cfg.get("bar_alpha", 150)
        alpha = np.minimum(np.linspace(0, top * 1.6, bar_h), top).astype(np.uint8)
        if k["position"] == "haut":
            alpha = alpha[::-1]
        bar = Image.new("RGBA", (W, bar_h), (0, 0, 0, 0))
        bar.putalpha(Image.fromarray(np.repeat(alpha[:, None], W, axis=1), "L"))
        bar_y = 0 if k["position"] == "haut" else H - bar_h

    f0, f1 = int(round(start * fps)), int(round(end * fps))
    name = out_name or ("preview.mp4" if preview else f"{projet_dir.name}{SUFFIXES.get(fmt, '')}.mp4")
    out = build / name

    par = cfg.get("parallaxe")
    par = 0.03 if par is True else float(par or 0)          # amplitude (fraction de la largeur)
    cam_amp = float(cfg.get("camera_intensite") or 1.0)
    if par or cfg.get("flou_fond") or cfg.get("brume_profondeur"):
        from .depth import compute
        compute(projet_dir, [s[3] for s in shots if s[2] == "case"])
    vis_data = None
    if cfg.get("visualiseur") in ("barres", "onde"):     # spectre / onde précalculés pour chaque image
        from .audio import load_mono, SR
        xa = load_mono(audio)
        nf = int(round(total * fps)) + 2
        vis_data = (FX.spectrum_frames(xa, SR, fps, nf) if cfg["visualiseur"] == "barres"
                    else FX.wave_frames(xa, SR, fps, nf))
    logo, logo_pos = _logo(projet_dir, cfg, W, H)
    state = {
        "size": (W, H), "inner": inner, "fps": fps,
        "parallaxe": par * cam_amp, "depth_dir": build / "depth", "cam_amp": cam_amp,
        "densite": float(cfg.get("particules_densite") or 1.0),
        "fumee_densite": float(cfg.get("fumee_densite") or 1.0),
        "rayons_intensite": float(cfg.get("rayons_intensite") or 1.0),
        "flammes_hauteur": float(cfg.get("flammes_hauteur") or 0.3),
        "flammes_intensite": float(cfg.get("flammes_intensite") or 1.0),
        "fuites": float(cfg.get("fuites_lumiere") or 0), "projecteurs": float(cfg.get("projecteurs") or 0),
        "tremblement": float(cfg.get("tremblement") or 0), "trem_zone": cfg.get("tremblement_zone", "partout"),
        "rvb": float(cfg.get("rvb_beat") or 0), "glitch": cfg.get("glitch") or None,
        "glitch_intensite": float(cfg.get("glitch_intensite") or 1.0),
        "vieux_film": float(cfg.get("vieux_film") or 0),
        "flou_fond": float(cfg.get("flou_fond") or 0), "brume_prof": float(cfg.get("brume_profondeur") or 0),
        "sec_t": sec_t, "sec_k": [SECTION_KEYS.get(k2, k2) for _, k2 in secs],
        "vis_data": vis_data, "vis_style": cfg.get("visualiseur"), "vis_zone": cfg.get("visualiseur_zone", "instrumentaux"),
        "vis_couleur": cfg.get("visualiseur_couleur") or "#FFDC50", "vis_hauteur": float(cfg.get("visualiseur_hauteur") or 0.12),
        "harmo": _harmo_target(projet_dir, shots) if cfg.get("harmonisation") else None,
        "pulse": float(cfg.get("pulse", 1.0)),        # 0 = ni gonflement ni flash au beat
        "fondu": max(float(cfg.get("fondu", XFADE)), 1.0 / fps),   # durée de la transition (s)
        "transition": cfg.get("transition", "fondu"),
        "beats": beats,
        "shots": shots, "starts": [s[0] for s in shots],
        "cases": projet_dir / "cases", "solos": projet_dir / cfg.get("solos", "solos"),
        "bar": bar, "bar_y": bar_y, "bar_spans": spans, "logo": logo, "logo_pos": logo_pos,
    }
    look = look_filter(cfg)
    # l'ASS est lu depuis build/ (cwd) : évite l'échappement des chemins Windows
    vf = f"setpts=PTS+{start:.3f}/TB,ass={ass.name},setpts=PTS-STARTPTS" if start else f"ass={ass.name}"
    if look:
        vf = f"{look},{vf}"
    af = []
    if cfg.get("volume_normalise"):                   # volume YouTube (-14 LUFS)
        af += ["loudnorm=I=-14:TP=-1.5:LRA=11", "aresample=48000"]
    if not extrait and start > 0:                      # début coupé : fondu d'entrée
        vf += ",fade=t=in:st=0:d=0.8"
        af.append("afade=t=in:st=0:d=0.8")
    if end >= d1 - 0.01:                               # fondu de fin si on rend jusqu'au bout
        fd = cfg.get("fade_out", 2.0)
        fo = max(0.0, end - start - fd)
        vf += f",fade=t=out:st={fo:.3f}:d={fd}"
        af.append(f"afade=t=out:st={fo:.3f}:d={fd}")
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(audio),
           "-map", "0:v", "-map", "1:a:0",
           "-vf", vf, "-af", ",".join(af) or "anull",
           *_video_codec(cfg.get("encoder", "auto"), preview, W * H),
           "-pix_fmt", "yuv420p", "-r", str(fps),
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", name]
    print(f"  {len(shots)} plans, {f1 - f0} frames {W}×{H}@{fps} ({fmt}) → {out}")
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, cwd=build)
    # file bornée : Pool.imap n'a pas de contre-pression → les frames (6 Mo) s'accumulent en RAM
    # si ffmpeg encode moins vite que les workers ne rendent, et le pipe Windows finit par casser
    # chaque worker charge ses propres images (~250-400 Mo) : on en lance autant que la mémoire le permet
    workers = workers or max(1, min(12, os.cpu_count() or 4, int((_memoire_dispo() - 700) // 450)))
    print(f"  {workers} processus de rendu")
    pending = deque()
    # « spawn » partout : sous Linux, le « fork » par défaut copie les threads et le pipe de ffmpeg
    # du processus principal, et les workers restent bloqués (aucune image rendue)
    with multiprocessing.get_context("spawn").Pool(workers, initializer=_init, initargs=(state,)) as pool:
        for fi in range(f0, f1):
            pending.append(pool.apply_async(_render, (fi,)))
            if len(pending) >= workers * 3:
                ff.stdin.write(pending.popleft().get())
        while pending:
            ff.stdin.write(pending.popleft().get())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg a échoué")
    return out
