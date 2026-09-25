#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Adaptive beat tracking: DP tracker with time-varying tempo (local period).
import numpy as np

sr = 44100
x = np.fromfile('/tmp/v3/beats.raw', dtype=np.float32)
print('audio sec', round(len(x)/sr, 2))

win = 2048; hop = 512
n = (len(x)-win)//hop
mags = []
for i in range(n):
    frame = x[i*hop:i*hop+win]*np.hanning(win)
    mags.append(np.abs(np.fft.rfft(frame)))
M = np.stack(mags)
flux = np.maximum(0, M[1:]-M[:-1]).sum(axis=1)
flux = np.concatenate([[0], flux])
flux = flux/(flux.max()+1e-9)
k = np.ones(5)/5
flux = np.convolve(flux, k, 'same')

t_hop = hop/sr  # ~0.01161s
FR = 1.0/t_hop   # ~86.1 Hz

# ---- local tempo (period in frames) via short-time autocorrelation ----
wl = int(6.0/t_hop)
hl = int(1.0/t_hop)
lags = np.arange(int(0.25/t_hop), int(1.5/t_hop))
period = np.empty(len(flux))
period[:] = np.nan
starts = list(range(0, len(flux)-wl, hl))
for st in starts:
    seg = flux[st:st+wl]
    seg = seg - np.mean(seg)
    d = seg.std()
    if d < 1e-9:
        continue
    ac = np.array([np.corrcoef(seg[:-l], seg[l:])[0,1] for l in lags])
    # choose first local max in autocorr (avoids octave doubling)
    # pick the lag of global max
    lag = lags[np.argmax(ac)]
    period[st:st+wl] = lag
# fill gaps
valid = ~np.isnan(period)
period[~valid] = period[valid][0] if valid.any() else lags[0]

# ---- DP beat tracking with time-varying period ----
N = len(flux)
sigma = 0.20
wmax = int(2.0/t_hop)   # 2s max inter-beat
wmin = int(0.15/t_hop)  # 0.15s min inter-beat
C = np.full(N, -np.inf)
back = np.full(N, -1, dtype=np.int64)
prev_idx = np.zeros(N, dtype=np.int64)
prev_vals = np.zeros(N)

for i in range(N):
    lo = max(0, i-wmax)
    hi = i-wmin
    if hi <= lo:
        C[i] = flux[i]; back[i] = i; prev_idx[i]=i; prev_vals[i]=flux[i]; continue
    t0s = np.arange(lo, hi+1)
    dt = (i - t0s).astype(float)
    T = np.maximum(period[t0s], 1.0)
    trans = -0.5*((np.log(dt) - np.log(T))**2)/(sigma**2)
    vals = C[t0s] + trans
    j = int(np.argmax(vals))
    C[i] = flux[i] + 0.9*C[t0s[j]]
    back[i] = t0s[j]

# backtrack from strongest C in last 2s
tail = np.arange(N-int(2.0/t_hop), N)
start = int(tail[np.argmax(C[tail])])
beats = []
i = start
guard = 0
while i > 0 and guard < N:
    beats.append(i)
    ni = back[i]
    if ni == i or ni < 0:
        break
    i = ni
    guard += 1
beats = np.array(sorted(beats))
bt = np.round(beats*t_hop, 3)
np.save('/tmp/v3/beats_adapt.npy', bt)
print('adaptive beats:', len(bt))

# ---- tempo profile per section ----
sections = [
 ('Intro',0.0,11.18),('Couplet1',11.18,25.42),('Chorus1',25.42,46.2),
 ('Pont',46.2,64.66),('Chorus2',64.66,81.32),('Outro',81.32,107.3)]
for name,a,b in sections:
    sel = bt[(bt>=a)&(bt<b)]
    if len(sel)<2:
        print(f'{name}: {len(sel)} beats'); continue
    ibi = np.median(np.diff(sel))
    print(f'{name}: {len(sel)} beats, med IBI {ibi*1000:.0f}ms = {60.0/ibi:.1f} BPM')
print('beats sample:', bt[:15].tolist())
print('beats tail:', bt[-8:].tolist())
