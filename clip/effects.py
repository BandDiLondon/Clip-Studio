"""Effets visuels supplémentaires (fonctions pures, appelées image par image par clip.render).
Particules : pluie, confettis, bokeh, étincelles. Lumière : fuites de lumière, projecteurs au beat,
éclairs, rayons. Rythme : tremblement, décalage RVB, glitch. Pellicule : vieux film.
Son : visualiseur. Profondeur : flou d'arrière-plan, brume en profondeur."""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


def _k(frame):
    return min(frame.size) / 1080


# ---------------------------------------------------------------- particules

def rain(frame, t, seed, dens=1.0):
    """Pluie : traits obliques rapides, plusieurs plans de profondeur."""
    W, H = frame.size
    k = _k(frame)
    rng = np.random.default_rng(seed)
    n = max(1, int(260 * dens))
    x0, y0 = rng.uniform(0, W * 1.2, n), rng.uniform(0, H, n)
    depth = rng.uniform(0.3, 1.0, n)                      # proche = plus long, plus rapide, plus clair
    speed = (900 + 1300 * depth) * k
    length = (30 + 60 * depth) * k
    slant = 0.22
    ys = (y0 + speed * t) % (H + 80 * k) - 40 * k
    xs = (x0 - slant * speed * t) % (W * 1.2) - W * 0.1
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, L, dp in zip(xs, ys, length, depth):
        d.line((x, y, x + slant * L, y - L), fill=(215, 225, 240, int(90 + 140 * dp)), width=max(1, int(2.4 * k * dp)))
    return Image.alpha_composite(frame.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.5))).convert("RGB")


def confetti(frame, t, seed, dens=1.0):
    """Confettis dorés et colorés qui tombent en tournoyant (reflets = largeur qui varie)."""
    W, H = frame.size
    k = _k(frame)
    rng = np.random.default_rng(seed)
    n = max(1, int(170 * dens))
    x0, y0 = rng.uniform(0, W, n), rng.uniform(0, H, n)
    speed = rng.uniform(80, 190, n) * k
    size = rng.uniform(11, 22, n) * k
    spin, ph = rng.uniform(2, 7, n), rng.uniform(0, 6.28, n)
    pal = [(255, 205, 60), (255, 225, 120), (230, 170, 40), (255, 90, 90), (90, 170, 255), (255, 255, 255)]
    cols = [pal[i] for i in rng.integers(0, len(pal), n)]
    gold = rng.random(n) < 0.6                             # majorité dorée
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, v, s, sp, p, c, g in zip(x0, y0, speed, size, spin, ph, cols, gold):
        yy = (y + v * t) % (H + 40) - 20
        xx = (x + 30 * k * math.sin(t * 1.3 + p)) % W
        w = abs(math.cos(t * sp + p)) * s                  # la pièce tourne sur elle-même
        c = pal[0] if g else c
        shine = int(170 + 85 * abs(math.sin(t * sp + p)))
        d.polygon([(xx - w, yy - s * 0.4), (xx + w, yy - s * 0.2), (xx + w * 0.8, yy + s * 0.4), (xx - w * 0.9, yy + s * 0.25)],
                  fill=(*c, shine))
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def bokeh(frame, t, seed, dens=1.0):
    """Bokeh / lucioles : grosses taches de lumière floues qui dérivent et respirent."""
    W, H = frame.size
    k = _k(frame)
    rng = np.random.default_rng(seed)
    n = max(1, int(26 * dens))
    x0, y0 = rng.uniform(0, W, n), rng.uniform(0, H, n)
    r = rng.uniform(18, 60, n) * k
    vx, vy = rng.uniform(-18, 18, n) * k, rng.uniform(-12, 6, n) * k
    ph = rng.uniform(0, 6.28, n)
    pal = [(255, 200, 120), (255, 160, 90), (255, 230, 170), (180, 210, 255)]
    cols = [pal[i] for i in rng.integers(0, len(pal), n)]
    s = 2
    layer = Image.new("RGB", (W // s, H // s), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, R, ax, ay, p, c in zip(x0, y0, r, vx, vy, ph, cols):
        xx, yy = (x + ax * t) % W, (y + ay * t) % H
        g = 0.35 + 0.35 * (1 + math.sin(t * 0.9 + p)) / 2
        d.ellipse(((xx - R) / s, (yy - R) / s, (xx + R) / s, (yy + R) / s), fill=tuple(int(v * g) for v in c))
    layer = layer.filter(ImageFilter.GaussianBlur(3 * k)).resize((W, H), Image.BILINEAR)
    return ImageChops.screen(frame, layer)


def sparks(frame, t, seed, dens=1.0):
    """Étincelles : jaillissent du bas, montent vite puis retombent (gravité), traînées lumineuses."""
    W, H = frame.size
    k = _k(frame)
    rng = np.random.default_rng(seed)
    n = max(1, int(170 * dens))
    life = rng.uniform(0.8, 1.8, n)
    off = rng.uniform(0, 2.0, n)
    src_x = rng.choice([0.3, 0.5, 0.7], n) * W + rng.normal(0, 40 * k, n)
    vx0 = rng.normal(0, 260, n) * k
    vy0 = -rng.uniform(600, 1100, n) * k
    g = 1400 * k
    u = (t + off) % life
    xs, ys = src_x + vx0 * u, H * 1.02 + vy0 * u + 0.5 * g * u * u
    vy = vy0 + g * u
    fade = 1 - u / life
    core = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(core)
    for x, y, ax, ay, f in zip(xs, ys, vx0, vy, fade):
        if f <= 0.02 or y > H + 10:
            continue
        col = (255, int(170 + 70 * f), int(60 * f))
        d.line((x, y, x - ax * 0.035, y - ay * 0.035), fill=tuple(int(c * f) for c in col), width=max(2, int(3 * k)))
    glow = core.filter(ImageFilter.GaussianBlur(5 * k))
    return ImageChops.screen(frame, ImageChops.add(ImageChops.add(core, glow), glow))


# ---------------------------------------------------------------- feu

_FIRE_TEX = {}
_FIRE_STOPS = np.array([0.0, 0.22, 0.45, 0.68, 0.86, 1.0], np.float32)
_FIRE_COLS = np.array([(0, 0, 0), (110, 8, 0), (220, 55, 0), (255, 140, 20), (255, 215, 90), (255, 250, 220)], np.float32)


def _fire_texture(w, h):
    """Bruit périodique fin (FFT, 1/f^1.6) : répété sans couture pendant le défilement vers le haut."""
    key = (w, h)
    if key not in _FIRE_TEX:
        rng = np.random.default_rng(21)
        spec = np.fft.fft2(rng.standard_normal((h, w)))
        fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
        f = np.sqrt((fx * 0.55) ** 2 + (fy * 1.9) ** 2)      # lisse en hauteur → langues étirées verticalement
        f[0, 0] = 1.0
        a = np.real(np.fft.ifft2(spec / (f + 2.0 / max(w, h)) ** 1.6)).astype(np.float32)
        a = (a - a.min()) / (a.max() - a.min() + 1e-6)
        _FIRE_TEX[key] = np.tile(a, (2, 2))
    return _FIRE_TEX[key]


def fire(frame, t, height=0.3, intensity=1.0):
    """Flammes qui montent du bas de l'image : deux couches de bruit qui défilent vers le haut à des
    vitesses différentes, colorées du rouge sombre au jaune blanc, lueur chaude et ondulation de chaleur."""
    if intensity <= 0:
        return frame
    W, H = frame.size
    q = 4
    w, h = max(8, W // q), max(8, H // q)
    tex = _fire_texture(w, h)
    oy1, oy2 = int(t * 0.55 * h) % h, int(t * 0.95 * h + h / 3) % h            # montée rapide
    ox1, ox2 = int(8 * math.sin(t * 1.3)) % w, int(w / 2 + 12 * math.sin(t * 0.9 + 1)) % w
    n = 0.6 * tex[oy1:oy1 + h, ox1:ox1 + w] + 0.4 * tex[oy2:oy2 + h, ox2:ox2 + w]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    fh = max(0.05, min(0.9, height))
    grad = np.clip((yy - (1 - fh)) / fh, 0, 1)                                  # 0 en haut de la zone, 1 en bas
    # plein en bas ; en montant, seules les parties « chaudes » du bruit restent → langues de flammes
    heat = np.clip((n - (1 - grad) * 0.95) * 2.6, 0, 1) * np.clip(grad * 3, 0, 1)
    heat = np.clip(heat * min(1.4, intensity), 0, 1)
    rgb = np.stack([np.interp(heat, _FIRE_STOPS, _FIRE_COLS[:, c]) for c in range(3)], -1)
    flames = Image.fromarray(rgb.astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.5 * _k(frame)))
    # ondulation de chaleur juste au-dessus des flammes
    a = np.asarray(frame).copy()
    k = _k(frame)
    y0, y1 = int(H * max(0.0, 1 - fh * 1.6)), H
    rows = np.arange(y0, y1)
    shift = (np.sin(rows * 0.09 + t * 9.0) * 3.5 * k * intensity * ((rows - y0) / max(1, y1 - y0))).astype(int)
    cols = (np.arange(W)[None, :] - shift[:, None]) % W                            # décalage ligne par ligne
    a[y0:y1] = a[rows[:, None], cols]
    frame = Image.fromarray(a)
    # lueur chaude : le bas de l'image est éclairé par le feu
    glow = np.clip((yy - (1 - fh * 1.8)) / (fh * 1.8), 0, 1) ** 1.5 * 0.35 * min(1.2, intensity)   # (h, 1)
    col = glow[:, :, None] * np.array((255, 120, 30), np.float32)                                 # (h, 1, 3)
    glow_img = Image.fromarray(np.repeat(col, w, axis=1).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    frame = ImageChops.screen(frame, glow_img)
    return ImageChops.screen(frame, flames)


# ---------------------------------------------------------------- lumière

def light_leaks(frame, t, intensity, boost=0.0):
    """Fuites de lumière : grands halos chauds (orange, rose) qui traversent lentement l'image ;
    `boost` (0-1) les renforce près des changements de plan."""
    if intensity <= 0:
        return frame
    W, H = frame.size
    s = 8
    w, h = max(4, W // s), max(4, H // s)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = np.zeros((h, w, 3), np.float32)
    for cx, cy, r, col, sp, ph in ((0.1, 0.2, 0.55, (255, 140, 50), 0.07, 0.0), (0.9, 0.8, 0.5, (255, 80, 120), 0.05, 2.1),
                                   (0.5, 0.0, 0.45, (255, 200, 120), 0.09, 4.0)):
        x = (cx + 0.35 * math.sin(t * sp * 6.28 + ph)) * w
        y = (cy + 0.25 * math.cos(t * sp * 5.1 + ph)) * h
        m = np.exp(-(((xx - x) / (r * w)) ** 2 + ((yy - y) / (r * h)) ** 2))
        out += m[..., None] * np.array(col, np.float32)
    a = 0.55 * intensity * (0.35 + 0.65 * min(1.0, boost)) * (0.8 + 0.2 * math.sin(t * 0.7))
    layer = Image.fromarray(np.clip(out * a, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return ImageChops.screen(frame, layer)


def spotlights(frame, env, beat_i, intensity):
    """Projecteurs de concert : lavage coloré depuis le haut, couleur alternée à chaque beat."""
    if intensity <= 0 or env <= 0.05:
        return frame
    W, H = frame.size
    pal = [(255, 40, 40), (40, 90, 255), (255, 60, 200), (40, 220, 255)]
    col = pal[beat_i % len(pal)]
    s = 8
    w, h = max(4, W // s), max(4, H // s)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    side = 0.15 if beat_i % 2 == 0 else 0.85               # le faisceau vient d'un coin puis de l'autre
    m = np.exp(-(((xx / w - side) / 0.45) ** 2 + ((yy / h) / 0.9) ** 2))
    layer = (m[..., None] * np.array(col, np.float32) * env * intensity).astype(np.uint8)
    return ImageChops.screen(frame, Image.fromarray(layer).resize((W, H), Image.BILINEAR))


def lightning(frame, t, seed, intensity=1.0):
    """Éclairs : de temps en temps (toutes les ~5-10 s), double flash bleuté très bref."""
    period = 7.0
    n = int(t // period)
    rng = np.random.default_rng(seed + n)
    at = n * period + rng.uniform(0.5, period - 1.5)
    dt = t - at
    if not (0 <= dt < 0.45):
        return frame
    flash = math.exp(-dt / 0.05) + 0.7 * (math.exp(-(dt - 0.18) / 0.05) if dt >= 0.18 else 0)
    a = min(0.85, flash * 0.75 * intensity)
    return Image.blend(frame, Image.new("RGB", frame.size, (215, 225, 255)), a)


def god_rays(frame, t, intensity, tex=None):
    """Rayons de lumière : faisceaux obliques qui tombent d'en haut, se balancent doucement,
    modulés par une texture de fumée (effet volumétrique)."""
    if intensity <= 0:
        return frame
    W, H = frame.size
    s = 6
    w, h = max(4, W // s), max(4, H // s)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    beams = np.zeros((h, w), np.float32)
    for x0, width, sp, ph in ((0.25, 0.05, 0.3, 0.0), (0.45, 0.035, 0.22, 1.7), (0.62, 0.06, 0.26, 3.1), (0.8, 0.03, 0.35, 4.4)):
        x = (x0 + 0.03 * math.sin(t * sp + ph)) * w + (yy / h) * 0.18 * w      # faisceaux obliques
        beams += np.exp(-((xx - x) / (width * w)) ** 2) * (0.6 + 0.4 * math.sin(t * sp * 2 + ph))
    beams *= np.clip(1.15 - yy / h, 0, 1) ** 1.5          # plus forts en haut
    if tex is not None:
        th, tw = tex.shape
        oy, ox = int(t * 5) % (th // 2), int(t * 3) % (tw // 2)
        beams *= 0.55 + 0.45 * np.asarray(Image.fromarray((tex[oy:oy + th // 2, ox:ox + tw // 2] * 255).astype(np.uint8))
                                          .resize((w, h), Image.BILINEAR), np.float32) / 255
    layer = np.clip(beams[..., None] * np.array((255, 236, 200), np.float32) * 0.55 * intensity, 0, 255).astype(np.uint8)
    img = Image.fromarray(layer).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4 * _k(frame)))
    return ImageChops.screen(frame, img)


# ---------------------------------------------------------------- rythme

def shake(frame, t, amount):
    """Tremblement de caméra : décalage aléatoire (déterministe) proportionnel à `amount` (0-1)."""
    if amount <= 0.01:
        return frame
    W, H = frame.size
    k = _k(frame)
    dx = math.sin(t * 91.3) * math.cos(t * 57.1) * 18 * k * amount
    dy = math.sin(t * 73.7 + 1.3) * 12 * k * amount
    z = 1 + 0.03 * amount
    ww, hh = W / z, H / z
    x0, y0 = (W - ww) / 2 + dx, (H - hh) / 2 + dy
    return frame.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + ww, y0 + hh))


def rgb_split(frame, amount):
    """Décalage RVB : rouge à gauche, bleu à droite, de `amount` × 14 px (à 1080p)."""
    px = int(round(14 * _k(frame) * amount))
    if px < 1:
        return frame
    a = np.asarray(frame).copy()
    a[:, :, 0] = np.roll(a[:, :, 0], -px, axis=1)
    a[:, :, 2] = np.roll(a[:, :, 2], px, axis=1)
    return Image.fromarray(a)


def glitch(frame, t, seed, intensity=1.0):
    """Glitch numérique : bandes horizontales décalées, un bloc aux couleurs inversées, léger RVB."""
    W, H = frame.size
    rng = np.random.default_rng(seed)
    a = np.asarray(frame).copy()
    for _ in range(int(3 + 7 * intensity)):
        y = int(rng.uniform(0, H))
        h = int(rng.uniform(4, 40) * _k(frame))
        dx = int(rng.normal(0, 60 * intensity) * _k(frame))
        a[y:y + h] = np.roll(a[y:y + h], dx, axis=1)
    if rng.random() < 0.6:
        bw, bh = int(rng.uniform(0.1, 0.35) * W), int(rng.uniform(0.03, 0.1) * H)
        bx, by = int(rng.uniform(0, W - bw)), int(rng.uniform(0, H - bh))
        a[by:by + bh, bx:bx + bw] = 255 - a[by:by + bh, bx:bx + bw][:, :, ::-1]
    return rgb_split(Image.fromarray(a), 0.8 * intensity)


# ---------------------------------------------------------------- pellicule

def old_film(frame, t, intensity):
    """Vieux film : sautillement, scintillement, rayures verticales et poussières (changent à 12 i/s)."""
    if intensity <= 0:
        return frame
    W, H = frame.size
    k = _k(frame)
    step = int(t * 12)                                    # rythme « projecteur » : 12 variations / s
    rng = np.random.default_rng(1000 + step)
    jy = int(rng.normal(0, 2.5 * k * intensity))          # sautillement vertical
    if jy:
        frame = ImageChops.offset(frame, 0, jy)
    flick = 1 + rng.normal(0, 0.05 * intensity)           # scintillement
    frame = Image.eval(frame, lambda v: max(0, min(255, int(v * flick))))
    d = ImageDraw.Draw(frame)
    for _ in range(rng.poisson(2.5 * intensity)):          # rayures
        x = rng.uniform(0, W)
        c = int(rng.choice([30, 225]))
        d.line((x, 0, x + rng.normal(0, 3), H), fill=(c, c, c), width=1)
    for _ in range(rng.poisson(14 * intensity)):           # poussières
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 4) * k
        c = int(rng.choice([15, 235]))
        d.ellipse((x - r, y - r, x + r, y + r * rng.uniform(0.5, 2)), fill=(c, c, c))
    return frame


# ---------------------------------------------------------------- son

def spectrum_frames(x, sr, fps, n_frames, bands=40):
    """Énergie par bande (log) pour chaque image vidéo : tableau (n_frames, bands) normalisé 0-1."""
    hop = sr / fps
    win = 2048
    out = np.zeros((n_frames, bands), np.float32)
    edges = np.geomspace(40, min(12000, sr / 2 - 1), bands + 1)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    idx = [np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0] for i in range(bands)]
    wnd = np.hanning(win).astype(np.float32)
    for f in range(n_frames):
        c = int(f * hop)
        seg = x[max(0, c - win // 2): c + win // 2]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        mag = np.abs(np.fft.rfft(seg * wnd))
        out[f] = [np.log1p(mag[i].mean()) if len(i) else 0 for i in idx]
    out /= np.percentile(out, 99) + 1e-6
    # lissage temporel (retombée douce)
    for f in range(1, n_frames):
        out[f] = np.maximum(out[f], out[f - 1] * 0.82)
    return np.clip(out, 0, 1)


def wave_frames(x, sr, fps, n_frames, points=160):
    """Forme d'onde autour de chaque image : tableau (n_frames, points) entre -1 et 1."""
    hop = sr / fps
    span = int(sr * 0.05)
    out = np.zeros((n_frames, points), np.float32)
    peak = np.percentile(np.abs(x), 99.5) + 1e-6
    for f in range(n_frames):
        c = int(f * hop)
        seg = x[max(0, c - span // 2): c + span // 2]
        if len(seg) < 2:
            continue
        out[f] = np.interp(np.linspace(0, len(seg) - 1, points), np.arange(len(seg)), seg) / peak
    return np.clip(out, -1, 1)


def visualizer(frame, data, style, color, height):
    """Barres de spectre ou onde, en bas de l'image, lumineuses et semi-transparentes."""
    W, H = frame.size
    k = _k(frame)
    hpx = height * H
    base = H - int(40 * k)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) if color else (255, 220, 80)
    if style == "barres":
        n = len(data)
        margin = W * 0.12
        bw = (W - 2 * margin) / n
        for i, v in enumerate(data):
            x = margin + i * bw
            d.rounded_rectangle((x + bw * 0.18, base - max(3 * k, v * hpx), x + bw * 0.82, base),
                                radius=max(1, int(bw * 0.25)), fill=(*rgb, 200))
    else:
        pts = [(W * 0.08 + i * (W * 0.84) / (len(data) - 1), base - hpx / 2 + v * hpx / 2) for i, v in enumerate(data)]
        d.line(pts, fill=(*rgb, 220), width=max(2, int(3 * k)), joint="curve")
    glow = layer.filter(ImageFilter.GaussianBlur(6 * k))
    out = Image.alpha_composite(frame.convert("RGBA"), glow)
    return Image.alpha_composite(out, layer).convert("RGB")


# ---------------------------------------------------------------- profondeur

def depth_blur(frame, D, intensity):
    """Flou d'arrière-plan : le fond (profondeur faible) devient flou, le premier plan reste net."""
    if intensity <= 0 or D is None:
        return frame
    blurred = frame.filter(ImageFilter.GaussianBlur(10 * _k(frame) * intensity))
    m = np.clip((1 - np.asarray(D, np.float32)) * 1.4 - 0.2, 0, 1) ** 1.3
    return Image.composite(blurred, frame, Image.fromarray((m * 255).astype(np.uint8), "L"))


def depth_fog(frame, D, intensity, color=(200, 206, 216)):
    """Brume en profondeur : le fond s'efface dans une brume claire, le premier plan reste net."""
    if intensity <= 0 or D is None:
        return frame
    m = np.clip(1 - np.asarray(D, np.float32), 0, 1) ** 1.8 * 0.85 * intensity
    return Image.composite(Image.new("RGB", frame.size, color), frame,
                           Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8), "L"))
