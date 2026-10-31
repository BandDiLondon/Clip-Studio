"""Mode instrumental : pas de paroles, des images abstraites qui suivent le rythme.

Analyse (build/rythme.json, faite avec les beats) : énergie de chaque beat → passages calme / modéré / intense,
1er temps des mesures, et « pics » (accents nettement au-dessus du reste : caisse claire, coups, attaques).
Montage : une coupe toutes les 2 mesures au calme, à chaque mesure en modéré, tous les `densite` beats en intense,
plus une coupe forcée sur chaque pic marqué. Les images, réparties par niveau d'énergie, reviennent avec des
variantes (miroir, rotation, teinte) pour que deux coupes ne se ressemblent pas."""
import json

import numpy as np

from .i18n import tp

NIVEAUX = {"fr": ("calme", "modéré", "intense"), "en": ("calm", "moderate", "intense")}
CHAPITRES = {"fr": ("Calme", "Modéré", "Intense"), "en": ("Calm", "Moderate", "Intense")}
PAS = {0: 8, 1: 4}          # beats entre deux coupes : calme = 2 mesures, modéré = 1 mesure (intense : densite)
RUN_MIN = 16                # un passage dure au moins 4 mesures
PIC_ECART = 4.0             # en moyenne, au plus un pic toutes les 4 s
PIC_MIN = 0.34              # écart minimal entre deux pics (s) : au plus 3 flashs par seconde
PIC_COUPE = 0.5             # force à partir de laquelle un pic impose une coupe
COUPE_MIN = 0.3             # plan le plus court (s)
IMAGES = (12, 60)           # nombre d'images abstraites permis (défaut 30)


def _lisse(v, n):
    if len(v) < 2:
        return np.asarray(v, dtype=float)
    k = np.ones(min(n, len(v))) / min(n, len(v))
    pad = len(k) // 2
    return np.convolve(np.pad(v, (pad, len(k) - 1 - pad), mode="edge"), k, mode="valid")


def niveaux(energie):
    """Énergie lissée par beat → niveau 0 / 1 / 2, relatif à la chanson : ses 30 % les plus calmes, ses 30 % les
    plus intenses (une chanson très compressée varie de moins de 1 dB : un seuil absolu n'y verrait rien)."""
    e = _lisse(np.asarray(energie, dtype=float), 8)
    if not len(e):
        return []
    q1, q2 = np.percentile(e, 30), np.percentile(e, 70)
    if q2 - q1 < 1e-6:                                   # parfaitement uniforme
        lv = [1] * len(e)
    else:
        lv = [0 if x < q1 else 2 if x >= q2 else 1 for x in e]
    # passages trop courts fondus dans le précédent (ou le suivant au début)
    changed = True
    while changed:
        changed = False
        runs = _runs(lv)
        for k, (a, b, n) in enumerate(runs):
            if b - a < RUN_MIN and len(runs) > 1:
                fill = runs[k - 1][2] if k > 0 else runs[k + 1][2]
                lv[a:b] = [fill] * (b - a)
                changed = True
                break
    return lv


def _runs(lv):
    """[(début, fin exclue, niveau)] des suites de beats de même niveau."""
    out, a = [], 0
    for i in range(1, len(lv) + 1):
        if i == len(lv) or lv[i] != lv[a]:
            out.append((a, i, lv[a]))
            a = i
    return out


def pics(env, t_hop, ratio=3.0):
    """Accents de l'enveloppe d'attaques : maximum local, dans les 10 % les plus forts et au moins `ratio` fois le
    niveau ambiant (médiane sur ±1 s). On garde les plus marqués (force = attaque × rapport à l'ambiance), en
    moyenne un toutes les PIC_ECART s, jamais deux à moins de PIC_MIN s. → [[temps, force 0.15-1]]."""
    env = np.asarray(env, dtype=float)
    if len(env) < 3:
        return []
    w = max(1, int(1.0 / t_hop))
    med = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(env, w, mode="edge"), 2 * w + 1), axis=1)
    p90, r = np.percentile(env, 90), max(1, int(0.08 / t_hop))
    cand = []
    for i in range(1, len(env) - 1):
        rap = env[i] / (med[i] + 1e-9)
        if env[i] >= p90 and rap >= ratio and env[i] == env[max(0, i - r):i + r + 1].max():
            cand.append((env[i] * min(rap, 10.0), i))
    garde, maxi = [], max(1, int(len(env) * t_hop / PIC_ECART))
    for v, i in sorted(cand, reverse=True):              # les plus marqués d'abord
        if len(garde) >= maxi:
            break
        t = i * t_hop
        if all(abs(t - g[0]) >= PIC_MIN for g in garde):
            garde.append((t, v))
    if not garde:
        return []
    lo, hi = min(v for _, v in garde), max(v for _, v in garde)
    return [[round(t, 3), round(0.15 + 0.85 * (v - lo) / (hi - lo), 2) if hi > lo else 1.0] for t, v in sorted(garde)]


def analyse(audio_path, beats):
    """Énergie par beat, niveaux, phase des mesures et pics. → dict (enregistré dans build/rythme.json)."""
    import librosa
    from .audio import HOP, SR, load_mono, onset_envelope
    x = load_mono(audio_path)
    t_hop = HOP / SR
    env = onset_envelope(x)
    rms = librosa.feature.rms(y=x, frame_length=2048, hop_length=HOP)[0]
    beats = np.asarray(beats, dtype=float)
    fr = np.clip((beats / t_hop).astype(int), 0, len(rms) - 1)
    bornes = list(fr) + [len(rms)]
    moy = lambda v: np.array([v[a:max(a + 1, b)].mean() for a, b in zip(bornes[:-1], bornes[1:])])
    e = np.array([])
    if len(fr):                                          # énergie = volume + densité d'attaques, à parts égales
        er, eo = moy(rms), moy(env[:len(rms)])
        e = 0.5 * np.clip(er / (np.percentile(er, 90) + 1e-9), 0, 1.2) +             0.5 * np.clip(eo / (np.percentile(eo, 90) + 1e-9), 0, 1.2)
    # 1er temps de la mesure : la phase (sur 4) dont les beats portent les attaques les plus fortes
    fe = np.clip(fr, 0, len(env) - 1)
    phase = int(np.argmax([env[fe[ph::4]].mean() if len(fe[ph::4]) else 0 for ph in range(4)])) if len(fe) else 0
    return {"phase": phase, "energie": [round(float(v), 3) for v in e], "niveaux": niveaux(e),
            "pics": pics(env, t_hop), "duree": round(len(x) / SR, 3)}


POIDS = (0.45, 1.45)        # force des effets au beat : passage le plus calme → le plus intense


def poids(r):
    """Force des effets au beat pour chaque beat (POIDS[0] au plus calme, POIDS[1] au plus intense), d'après l'énergie
    lissée : le tremblement, les projecteurs, le RVB, le glitch et le gonflement suivent l'intensité du morceau."""
    e = _lisse(np.asarray(r.get("energie") or [], dtype=float), 8)
    if not len(e):
        return []
    lo, hi = np.percentile(e, 10), np.percentile(e, 90)
    u = np.clip((e - lo) / (hi - lo), 0, 1) if hi > lo else np.full(len(e), 0.55)
    return [round(float(POIDS[0] + (POIDS[1] - POIDS[0]) * x), 3) for x in u]


def sauver(r, path):
    from . import ecrire
    ecrire(path, json.dumps(r, ensure_ascii=False))


def charger(p):
    f = p / "build" / "rythme.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def passages(beats, r):
    """[{niveau, debut, fin}] : passages d'énergie, en secondes."""
    lv, d = r.get("niveaux") or [], r.get("duree") or (beats[-1] if len(beats) else 0)
    out = []
    for a, b, n in _runs(lv):
        out.append({"niveau": n, "debut": 0.0 if not out else round(float(beats[a]), 2),
                    "fin": round(float(beats[b]) if b < len(beats) else float(d), 2)})
    return out


def coupes(beats, r, densite=2):
    """Instants de coupe [(temps, niveau)] : grille de mesures selon l'énergie + pics marqués."""
    beats = [float(b) for b in beats]
    lv, ph = r.get("niveaux") or [], int(r.get("phase") or 0)
    if not beats or not lv:
        return [(0.0, 1)]
    out = []
    for a, b, n in _runs(lv):
        pas = PAS.get(n, max(1, int(densite)))
        last = None
        for j in range(a, b):
            if j == a or (j - ph) % pas == 0:
                if last is not None and j - last < min(2, pas):
                    continue
                out.append((0.0 if not out else beats[j], n))
                last = j
    ibi = float(np.median(np.diff(beats))) if len(beats) > 1 else 0.5
    for t, f in r.get("pics") or []:
        if f < PIC_COUPE or any(abs(t - c) < 0.6 * ibi for c, _ in out):
            continue
        j = int(np.argmin([abs(b - t) for b in beats]))
        tt = beats[j] if abs(beats[j] - t) <= 0.1 else t
        out.append((tt, lv[min(j, len(lv) - 1)]))
    out.sort()
    garde = []
    for t, n in out:
        if not garde or t - garde[-1][0] >= COUPE_MIN:
            garde.append((round(t, 3), n))
    return garde


def repartition(n, cuts):
    """Niveau de chacune des n images, au prorata des coupes de chaque niveau (au moins 3 par niveau présent)."""
    compte = {k: sum(1 for _, x in cuts if x == k) for k in (0, 1, 2)}
    pres = [k for k in (0, 1, 2) if compte[k]] or [1]
    base = {k: min(3, n // len(pres)) for k in pres}
    reste = n - sum(base.values())
    tot = sum(compte[k] for k in pres) or 1
    part = {k: reste * compte[k] / tot for k in pres}
    for k in pres:
        base[k] += int(part[k])
    for k in sorted(pres, key=lambda k: part[k] - int(part[k]), reverse=True)[:n - sum(base.values())]:
        base[k] += 1
    return [k for k in pres for _ in range(base[k])]


def nombre_images(cfg):
    return int(min(IMAGES[1], max(IMAGES[0], int(cfg.get("images_instrumental") or 30))))


def shotlist(cfg, beats, r):
    """Shotlist d'images abstraites : chaque image porte son niveau d'énergie."""
    from .shots import build
    sl = build([], ambiance=nombre_images(cfg))
    lv = repartition(len(sl["shots"]), coupes(beats, r, cfg.get("densite_coupes", 2)))
    for s, n in zip(sl["shots"], lv):
        s["niveau"] = n
    return sl


def _ts(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def label(cfg, s, beats, r):
    """Libellé d'une image abstraite pour Claude : niveau d'énergie et passages où elle sert."""
    from .i18n import langue_projet
    lg = langue_projet(cfg)
    n = s.get("niveau", 1)
    ps = [x for x in passages(beats, r) if x["niveau"] == n][:3] if r else []
    quand = ", ".join(f"{_ts(x['debut'])}–{_ts(x['fin'])}" for x in ps)
    return tp(cfg, f"image abstraite — énergie {NIVEAUX[lg][n]}" + (f" (passages {quand})" if quand else ""),
              f"abstract image — {NIVEAUX[lg][n]} energy" + (f" (parts {quand})" if quand else ""))


def plan(beats, r, shots, cfg):
    """Timeline : à chaque coupe, la prochaine image du niveau d'énergie (jamais deux fois de suite la même);
    chaque retour d'une image a un numéro de variante (0 = original)."""
    from .i18n import langue_projet
    noms = NIVEAUX[langue_projet(cfg)]
    ids = [s["id"] for s in shots]
    pools = {k: [s["id"] for s in shots if s.get("niveau", 1) == k] for k in (0, 1, 2)}
    rang, vus, ev, prev = {0: 0, 1: 0, 2: 0}, {}, [], None
    for t, n in coupes(beats, r, cfg.get("densite_coupes", 2)):
        pool = pools.get(n) or ids
        if not pool:
            break
        img = pool[rang[n] % len(pool)]
        rang[n] += 1
        if img == prev and len(pool) > 1:
            img = pool[rang[n] % len(pool)]
            rang[n] += 1
        e = {"t": t, "img": img, "note": noms[n]}
        v = vus.get(img, 0)
        vus[img] = v + 1
        if v:
            e["variante"] = v
        ev.append(e)
        prev = img
    return ev


def segments_chapitres(beats, r, langue="fr"):
    """Passages d'énergie sous forme de « vers » pour les chapitres YouTube (publish.chapitres)."""
    return [{"section": CHAPITRES[langue][x["niveau"]], "start": x["debut"], "end": x["fin"]}
            for x in passages(beats, r)]


def resume(beats, r, cfg):
    """Pour l'interface : tempo, passages, nombre de pics et de coupes."""
    cuts = coupes(beats, r, cfg.get("densite_coupes", 2))
    ibi = np.diff(np.asarray(beats, dtype=float))
    return {"bpm": round(60 / float(np.median(ibi)), 1) if len(ibi) else None,
            "passages": passages(beats, r), "pics": len(r.get("pics") or []),
            "pics_coupe": sum(1 for _, f in r.get("pics") or [] if f >= PIC_COUPE),
            "coupes": len(cuts), "images": nombre_images(cfg)}
