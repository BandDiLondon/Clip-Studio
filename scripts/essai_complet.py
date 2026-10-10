"""Essai complet du pipeline sur une chanson synthétique : sert à valider un système sans intervention
(GitHub Actions macOS / Linux). Préparer → fausses planches → découpe → plan → aperçu vidéo, puis contrôle du mp4.

  python scripts/essai_complet.py voix.wav [--langue en]      (voix chantée ou parlée des PAROLES ci-dessous)

La voix est mélangée à une pulsation à 120 BPM (pour la détection des beats). Le projet « essai_auto » est créé
dans projets/ puis supprimé (--garder pour le conserver). Code de sortie 0 = tout est passé."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.update(CLIP_SANS_CLAUDE="1", PYTHONUTF8="1")
sys.path.insert(0, str(ROOT))
import clip  # noqa: E402,F401  (met tools/ffmpeg/bin en tête du PATH, comme Clip Studio)
NOM = "essai_auto"
PAROLES = {"fr": """[Verse 1]
Le soleil se lève sur la ville
Les voitures roulent sans bruit
[Chorus]
Chante avec nous ce soir
Chante encore une fois
[Verse 2]
La pluie tombe sur les toits
Le vent souffle dans la nuit
[Chorus]
Chante avec nous ce soir
Chante encore une fois
""", "en": """[Verse 1]
The sun is rising on the town
The cars are rolling without a sound
[Chorus]
Sing along with us tonight
Sing it one more time
[Verse 2]
The rain is falling on the roofs
The wind is blowing through the night
[Chorus]
Sing along with us tonight
Sing it one more time
"""}
COULEURS = [(200, 60, 60), (60, 160, 70), (60, 90, 200), (210, 170, 40), (150, 60, 180), (40, 170, 170)]


def clip(*args):
    print(f"\n$ python -m clip {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, "-m", "clip", *args], cwd=ROOT)
    if r.returncode:
        sys.exit(f"ÉCHEC : python -m clip {' '.join(args)} (code {r.returncode})")


def planches(p):
    """Planches factices : vignettes 16:9 unies, gouttières noires, à la grille demandée par la shotlist."""
    from PIL import Image, ImageDraw
    sl = json.loads((p / "build" / "shotlist.json").read_text(encoding="utf-8"))
    for i, pl in enumerate(sl["planches"]):
        cols, rows = pl["grid"]
        w, h, g = 768, 432, 6
        im = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
        d = ImageDraw.Draw(im)
        for r in range(rows):
            for c in range(cols):
                col = COULEURS[(i * 6 + r * cols + c) % len(COULEURS)]
                x, y = c * w + g, r * h + g
                d.rectangle((x, y, x + w - 2 * g, y + h - 2 * g), fill=col)
                d.ellipse((x + 250, y + 110, x + 500, y + 310), fill=tuple(v // 2 for v in col))
        im.save(p / "planches" / f"{pl['id'].upper()}.png")
    print(f"  {len(sl['planches'])} planche(s) factice(s), {len(sl['shots'])} image(s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voix", type=Path)
    ap.add_argument("--model", default="small")
    ap.add_argument("--garder", action="store_true")
    ap.add_argument("--langue", default="fr", choices=("fr", "en"), help="langue de la chanson (paroles ci-dessus)")
    a = ap.parse_args()
    os.environ["CLIP_LANG"] = a.langue            # un nouveau projet prend la langue de l'interface
    p = ROOT / "projets" / NOM
    shutil.rmtree(p, ignore_errors=True)
    clip("new", NOM)
    if json.loads((p / "projet.json").read_text(encoding="utf-8"))["langue"] != a.langue:
        sys.exit("ÉCHEC : langue du projet")
    # voix + pulsation 120 BPM (grosse caisse synthétique), 2 s de silence avant le chant
    pulse = "aevalsrc=0.6*sin(2*PI*55*t)*exp(-25*mod(t\\,0.5)):s=44100:d=600"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a.voix), "-f", "lavfi", "-i", pulse,
                        "-filter_complex", "[0:a]adelay=2000|2000,aresample=44100[v];[v][1:a]amix=inputs=2:duration=first,"
                        "apad=pad_dur=2", "-ac", "2", "-b:a", "192k", str(p / "essai.mp3")])
    if r.returncode:
        sys.exit("ÉCHEC : fabrication du mp3")
    (p / "essai.txt").write_text(PAROLES[a.langue], encoding="utf-8")
    clip("prepare", NOM, "--model", a.model)
    words = json.loads((p / "build" / "words.json").read_text(encoding="utf-8"))["segments"]
    print(f"  calage : {len(words)} vers, premier à {words[0]['start']:.1f} s, dernier à {words[-1]['start']:.1f} s")
    planches(p)
    clip("build-preview", NOM)
    mp4 = sorted((p / "build").glob("*.mp4"), key=lambda f: f.stat().st_mtime)
    if not mp4:
        sys.exit("ÉCHEC : aucun mp4 produit")
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                                      str(mp4[-1])], capture_output=True, text=True).stdout)
    types = sorted(s["codec_type"] for s in info["streams"])
    duree = float(info["format"]["duration"])
    print(f"\n  vidéo : {mp4[-1].name}, {duree:.1f} s, flux {types}, {mp4[-1].stat().st_size // 1024} Ko")
    if types != ["audio", "video"] or duree < 5:
        sys.exit("ÉCHEC : vidéo incomplète")
    if not a.garder:
        shutil.rmtree(p)
    print("\nESSAI COMPLET RÉUSSI")


if __name__ == "__main__":
    main()
