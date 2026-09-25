"""Décodage audio + détection de beats adaptative (tempo local variable)."""
import subprocess
from pathlib import Path

import numpy as np

SR = 44100
HOP = 512


def load_mono(path, sr=SR):
    """Décode n'importe quel fichier audio en float32 mono via ffmpeg."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
                        "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def onset_envelope(x, sr=SR, hop=HOP):
    import librosa
    env = librosa.onset.onset_strength(y=x, sr=sr, hop_length=hop)
    return env / (env.max() + 1e-9)


def estimate_tempo(x, sr=SR, hop=HOP, center=100.0):
    """Tempo global (BPM, ramené entre 72 et 144) pour guider le suivi des beats.
    Chaque pic du tempogramme est ramené dans la plage 72-144 ; on retient le tempo dont la « famille
    d'octaves » (moitié, lui-même, double, quadruple) est la plus présente : les niveaux de rythme d'une
    chanson sont liés par 2, alors que les pics parasites (rapports 4/3, triolets) sont isolés.
    Léger a priori vers ~100 BPM. Validé sur 5 chansons (83 à 126 BPM)."""
    import librosa
    env = librosa.onset.onset_strength(y=x, sr=sr, hop_length=hop)
    tg = librosa.feature.tempogram(onset_envelope=env, sr=sr, hop_length=hop)
    bpms = librosa.tempo_frequencies(tg.shape[0], sr=sr, hop_length=hop)[1:]
    m = tg.mean(1)[1:]
    order = np.argsort(bpms)
    at = lambda b: float(np.interp(b, bpms[order], m[order], left=0, right=0))
    peaks = [bpms[i] for i in range(1, len(m) - 1)
             if 60 <= bpms[i] <= 400 and m[i] >= m[i - 1] and m[i] >= m[i + 1]]
    if not peaks:
        return center

    def fold(t):
        while t >= 144:
            t /= 2
        while t < 72:
            t *= 2
        return t

    def score(t):
        famille = sum(at(t * 2 ** j) for j in (-1, 0, 1, 2))
        return famille * np.exp(-0.5 * (np.log2(t / center) / 0.8) ** 2)
    return round(float(max({round(fold(p), 1) for p in peaks}, key=score)), 1)


def _local_period(flux, t_hop, bpm_hint=100, win_s=6.0, step_s=1.0, min_s=0.25, max_s=1.5):
    """Période de beat locale (en frames) par autocorrélation glissante,
    pondérée par un a priori log-gaussien autour de bpm_hint (évite double/moitié de tempo)."""
    wl, hl = int(win_s / t_hop), int(step_s / t_hop)
    lags = np.arange(int(min_s / t_hop), int(max_s / t_hop))
    prior = np.exp(-0.5 * (np.log2((60 / (lags * t_hop)) / bpm_hint) / 0.4) ** 2)
    period = np.full(len(flux), np.nan)
    for st in range(0, max(1, len(flux) - wl), hl):
        seg = flux[st:st + wl] - flux[st:st + wl].mean()
        if seg.std() < 1e-9:
            continue
        denom = (seg * seg).sum()
        ac = np.array([(seg[:-l] * seg[l:]).sum() / denom for l in lags])
        idx = int(np.argmax(np.maximum(ac, 0) * prior))
        c = st + wl // 2
        period[max(0, c - hl):c + hl] = lags[idx]
    valid = ~np.isnan(period)
    if not valid.any():
        return np.full(len(flux), lags[len(lags) // 2], dtype=float)
    # interpolation entre les centres de fenêtre
    idx = np.arange(len(flux))
    return np.interp(idx, idx[valid], period[valid])


def track_beats(flux, t_hop, bpm_hint=100, sigma=0.20, decay=0.9):
    """Suivi DP à période variable. Retourne les temps de beat (s)."""
    period = _local_period(flux, t_hop, bpm_hint)
    n = len(flux)
    wmin, wmax = int(0.15 / t_hop), int(2.0 / t_hop)
    score = np.full(n, -np.inf)
    back = np.full(n, -1, dtype=np.int64)
    for i in range(n):
        lo, hi = max(0, i - wmax), i - wmin
        if hi <= lo:
            score[i] = flux[i]
            continue
        prev = np.arange(lo, hi + 1)
        dt = (i - prev).astype(float)
        trans = -0.5 * ((np.log(dt) - np.log(np.maximum(period[prev], 1.0))) ** 2) / sigma ** 2
        vals = score[prev] + trans
        j = int(np.argmax(vals))
        score[i] = flux[i] + decay * vals[j]
        back[i] = prev[j]
    tail = np.arange(max(0, n - int(2.0 / t_hop)), n)
    i = int(tail[np.argmax(score[tail])])
    beats = []
    while i >= 0:
        beats.append(i)
        i = back[i]
    return np.round(np.array(beats[::-1]) * t_hop, 3)


def detect(audio_path, out_path, bpm_hint="auto"):
    x = load_mono(audio_path)
    t_hop = HOP / SR
    auto = bpm_hint in (None, "", "auto", 0)
    if auto:                                          # tempo global estimé automatiquement
        bpm_hint = estimate_tempo(x)
        print(f"  tempo estimé automatiquement : {bpm_hint} BPM")
    else:
        bpm_hint = float(bpm_hint)
        print(f"  tempo imposé : {bpm_hint} BPM")
    beats = track_beats(onset_envelope(x), t_hop, bpm_hint)
    np.save(out_path, beats)
    ibi = np.diff(beats)
    print(f"  {len(x) / SR:.2f} s audio, {len(beats)} beats, "
          f"tempo médian {60 / np.median(ibi):.1f} BPM (min {60 / ibi.max():.0f}, max {60 / ibi.min():.0f})")
    return beats, round(60 / float(np.median(ibi)), 1)


def tempo_report(beats, sections):
    """sections : [(nom, début, fin)]"""
    for name, a, b in sections:
        sel = beats[(beats >= a) & (beats < b)]
        if len(sel) < 2:
            print(f"  {name:10s} {len(sel)} beats")
            continue
        print(f"  {name:10s} {len(sel):3d} beats, {60 / np.median(np.diff(sel)):.1f} BPM")
