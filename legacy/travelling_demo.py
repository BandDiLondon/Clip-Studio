#!/usr/bin/env python3
"""Travelling sur image panoramique de concert (ref BDL) pour passages instrumentaux.
Glisse une fenetre 16:9 le long de l'image large avec leger zoom + pulse au beat."""
import numpy as np
from PIL import Image
import subprocess, os

W, H = 1920, 1080          # sortie 16:9
DUR = 6.0                  # duree de demo (s)
FPS = 30
BEAT = 0.618               # intervalle de beat (s) ~97 BPM
OUT = "/tmp/travelling_demo.mp4"
RAW = "/tmp/travelling_demo_raw.mp4"

def load_pano(path, scale):
    im = Image.open(path).convert("RGB")
    return im.resize((im.width*scale, im.height*scale), Image.LANCZOS)

pano = load_pano("/tmp/ref_concert.png", 6)   # 6144 x 1710
PW, PH = pano.size
print("pano", pano.size)

ch = PH
cw = int(ch * 16/9)
max_x = PW - cw
print("crop", cw, ch, "max_x", max_x)

nframes = int(DUR*FPS)
os.makedirs("/tmp/travframes", exist_ok=True)

for i in range(nframes):
    t = i / FPS
    period = DUR/2
    phase = (t % period) / period
    x = phase * max_x
    zoom = 1.0 + 0.06 * (t / DUR)
    beatp = (t % BEAT) / BEAT
    pulse = 1.0 + 0.015 * np.exp(-4*beatp)
    zoom *= pulse

    cwz = int(cw / zoom)
    chz = int(ch / zoom)
    y = (PH - chz)//2
    x = int(min(max(x,0), PW-cwz))
    box = (x, y, x+cwz, y+chz)
    frame = pano.crop(box).resize((W,H), Image.LANCZOS)
    frame.save(f"/tmp/travframes/f{i:05d}.png")
    if i % 30 == 0:
        print("frame", i)

subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i","/tmp/travframes/f%05d.png",
    "-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p",RAW],
    check=True, capture_output=True)
print("raw done")
