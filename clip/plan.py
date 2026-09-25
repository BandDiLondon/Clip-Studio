"""Proposition automatique de timeline : chaque vers → son image de la shotlist,
passages instrumentaux → travelling sur solos, sinon images d'ambiance."""
import bisect

from .shots import key

SNAP = 0.25        # une coupe se cale sur un beat s'il est à moins de SNAP s
MIN_GAP = 3.0      # trou sans paroles au-delà duquel on remplit l'instrumental
FILL_MIN = 4.0     # durée min / max d'un plan d'instrumental
FILL_MAX = 9.0


def snap(t, beats):
    i = bisect.bisect_left(beats, t)
    near = [b for b in beats[max(0, i - 1):i + 1] if abs(b - t) <= SNAP]
    return round(min(near, key=lambda b: abs(b - t)), 3) if near else round(t, 3)


class _Filler:
    """Remplit les passages instrumentaux : photos de solo (travelling) et images d'ambiance en alternance."""

    def __init__(self, solos, ambiance, beats):
        self.beats, self.k = beats, 0
        a, b = [("travel", x) for x in solos], [("img", x) for x in ambiance]
        # répartition régulière des deux listes, en commençant par une photo de solo
        pos = [(i / len(a), 0, x) for i, x in enumerate(a)] + [((i + 0.5) / len(b), 1, x) for i, x in enumerate(b)]
        self.pool = [x for _, _, x in sorted(pos)]

    def __bool__(self):
        return bool(self.pool)

    def fill(self, a, b, note):
        n = max(1, round((b - a) / FILL_MAX + 0.49))
        if (b - a) / n < FILL_MIN:
            n = max(1, int((b - a) // FILL_MIN))
        out = []
        for j in range(n):
            t = a if j == 0 else snap(a + (b - a) * j / n, self.beats)
            kind, name = self.pool[self.k % len(self.pool)]
            out.append({"t": round(t, 3), kind: name, "note": note})
            self.k += 1
        return out


def build(segments, beats, cfg, duration, shotlist):
    by_key = {s["key"]: s["id"] for s in shotlist["shots"] if s.get("key")}
    filler = _Filler(cfg.get("solos_list") or [],
                     [s["id"] for s in shotlist["shots"] if s.get("ambiance")], beats)
    ev, missing = [], []
    prev_end = 0.0
    for s in (s for s in segments if s["start"] is not None):
        start = snap(s["start"], beats)
        if start - prev_end > MIN_GAP:
            if not ev and cfg.get("intro_image"):
                ev.append({"t": 0.0, "img": cfg["intro_image"], "note": "intro"})
            elif filler:
                ev += filler.fill(0.0 if not ev else snap(prev_end + 0.3, beats), start,
                                  "intro" if not ev else "instrumental")
        img = by_key.get(key(s["text"]))
        if img is None:
            missing.append(s["text"])
        else:
            ev.append({"t": start if ev else 0.0, "img": img, "note": s["text"]})
        prev_end = s["end"]
    if duration - prev_end > MIN_GAP:
        if cfg.get("outro_image"):
            ev.append({"t": snap(prev_end + 0.3, beats), "img": cfg["outro_image"], "note": "outro"})
        elif filler:
            ev += filler.fill(snap(prev_end + 0.3, beats), duration, "outro")
    if missing:
        print(f"  ⚠ {len(missing)} vers sans image dans la shotlist : {missing[:3]}")
    return ev
