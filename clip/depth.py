"""Cartes de profondeur (Depth Anything V2 Small, CPU) pour l'effet de parallaxe 3D.
Sortie : build/depth/<case>.png en 16 bits, 1 = proche, 0 = loin. Calculées une seule fois."""
from pathlib import Path

import numpy as np
from PIL import Image

from .i18n import tr

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
MAX_SIDE = 1024          # la profondeur n'a pas besoin de la pleine résolution


def compute(projet_dir, names, force=False):
    import cv2
    projet_dir = Path(projet_dir)
    out_dir = projet_dir / "build" / "depth"
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = []
    for n in sorted(set(names)):
        src = next((projet_dir / "cases").glob(f"{n}.*"), None)
        dst = out_dir / f"{n}.png"
        if src and (force or not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime):
            todo.append((n, src, dst))
    if not todo:
        return 0
    from transformers import pipeline
    print(tr(f"  profondeur : {len(todo)} image(s) (modèle {MODEL.split('/')[-1]}, 1er lancement : téléchargement)",
             f"  depth: {len(todo)} image(s) (model {MODEL.split('/')[-1]}, first run: download)"))
    pipe = pipeline(task="depth-estimation", model=MODEL, device=-1)
    for n, src, dst in todo:
        im = Image.open(src).convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        d = pipe(im)["predicted_depth"].squeeze().numpy().astype(np.float32)
        d = cv2.resize(d, im.size, interpolation=cv2.INTER_CUBIC)
        lo, hi = np.percentile(d, 1), np.percentile(d, 99)
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)          # 1 = proche
        cv2.imwrite(str(dst), (d * 65535).astype(np.uint16))
        print(f"    {n}")
    return len(todo)
