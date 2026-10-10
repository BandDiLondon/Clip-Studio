"""Captures d'écran de Clip Studio pour le README (docs/images/), prises automatiquement.
Usage : .venv\\Scripts\\python.exe scripts\\captures.py [projet]      (défaut : Henry)
Travaille sur une COPIE temporaire du projet (prompts régénérés avec le modèle actuel ; le vrai projet n'est pas
modifié), lance Clip Studio sur un port libre, photographie les étapes avec Edge (ou Chrome) sans fenêtre, en thème
sombre, en français puis en anglais (fichiers « -en »), puis extrait une image du clip rendu (karaoké). Refaire après
chaque évolution de l'interface."""
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "images"
TAILLE = (1400, 900)
# (fichier, étape, paramètres d'URL en plus, hauteur de la fenêtre)
CAPTURES = [
    ("etape-planches.jpg", "planches", "", 1100),
    ("etape-videos.jpg", "videos", "&sel=p1_c3", 1000),
    ("etape-options.jpg", "options", "", 1000),
]
NAVIGATEURS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "microsoft-edge", "google-chrome", "chromium",
]


def navigateur():
    for n in NAVIGATEURS:
        p = n if Path(n).exists() else shutil.which(n)
        if p:
            return p
    raise SystemExit("Edge ou Chrome introuvable")


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def capture(nav, url, dest, hauteur):
    """Capture PNG pleine taille puis JPEG compressé (≤ ~300 Ko)."""
    with tempfile.TemporaryDirectory() as d:
        png = Path(d) / "c.png"
        subprocess.run([nav, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-dark-mode",
                        f"--window-size={TAILLE[0]},{hauteur}", "--virtual-time-budget=8000",
                        f"--user-data-dir={d}", f"--screenshot={png}", url],
                       capture_output=True, timeout=120)
        # Edge rend la main avant d'avoir fini d'écrire la capture : attendre un fichier complet et stable
        taille = -1
        for _ in range(60):
            if png.exists() and png.stat().st_size > 0 and png.stat().st_size == taille:
                break
            taille = png.stat().st_size if png.exists() else -1
            time.sleep(0.5)
        else:
            raise SystemExit(f"Capture non produite par le navigateur : {url}")
        im = Image.open(png).convert("RGB")
    for q in (85, 78, 70, 62):
        im.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        if dest.stat().st_size < 300_000:
            break
    print(f"  {dest.name} : {im.size[0]}×{im.size[1]}, {dest.stat().st_size // 1024} Ko")


def image_du_clip(projet_dir, dest, t=None):
    """Une image du rendu final, au milieu d'un vers (karaoké visible)."""
    import json
    videos = sorted((projet_dir / "build").glob("*.mp4"), key=lambda f: f.stat().st_size, reverse=True)
    videos = [v for v in videos if not v.name.startswith("preview")]
    if not videos:
        print("  (aucun rendu final : pas d'image du clip)")
        return
    if t is None:
        segs = json.loads((projet_dir / "build" / "words.json").read_text(encoding="utf-8"))["segments"]
        seg = [s for s in segs if s["start"] is not None][len(segs) // 3]
        t = (seg["start"] + seg["end"]) / 2
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(videos[0]), "-frames:v", "1",
                    "-vf", "scale=1280:-2", "-q:v", "3", str(dest)], check=True)
    print(f"  {dest.name} : image du clip à {t:.1f} s ({videos[0].name}), {dest.stat().st_size // 1024} Ko")


def main():
    projet = sys.argv[1] if len(sys.argv) > 1 else "Henry"
    import argparse
    import clip
    from clip import cli
    src = clip.PROJETS / projet
    if not (src / "projet.json").exists():
        raise SystemExit(f"Projet introuvable : {projet}")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # copie sans les fichiers lourds ni recalculables ; même nom pour que l'interface affiche « Henry »
        shutil.copytree(src, Path(tmp) / projet, ignore=shutil.ignore_patterns(
            "*.mp4", "video_frames", "depth", "historique", "videos"))
        import clip.web as web
        clip.PROJETS = cli.PROJETS = web.PROJETS = Path(tmp)
        cli.cmd_prompts(argparse.Namespace(nom=projet))            # prompts avec le modèle actuel
        web.PORT = port_libre()
        threading.Thread(target=web.serve, kwargs={"open_browser": False}, daemon=True).start()
        time.sleep(1.5)
        nav = navigateur()
        print(f"Captures de « {projet} » → {OUT}")
        for lg, suffixe in (("fr", ""), ("en", "-en")):
            for nom, etape, extra, h in CAPTURES:
                dest = OUT / nom.replace(".jpg", f"{suffixe}.jpg")
                capture(nav, f"http://127.0.0.1:{web.PORT}/?projet={projet}&lang={lg}{extra}#{etape}", dest, h)
    image_du_clip(src, OUT / "clip-karaoke.jpg")


if __name__ == "__main__":
    main()
