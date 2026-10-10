"""Détection de texte lisible dans les cases (RapidOCR : modèles PaddleOCR via onnxruntime, Windows et Linux) :
légendes, enseignes, t-shirts imprimés que le générateur d'images a écrits malgré le prompt. Avertissement seulement,
jamais bloquant. Le but est de repérer qu'il y a du texte, pas de le lire exactement."""
import json
from pathlib import Path

from .i18n import tr

LARGEUR = 1280      # analyse en 1280 px : 2× plus rapide qu'en pleine taille, même détection (mesuré)
SEUIL = 0.5         # confiance minimale d'une ligne (0,55 éliminait de vrais textes)
_MOTEUR = None


def _utile(ligne):
    """Ignore les bribes (« 00 », « a ») que l'OCR lit parfois dans les textures."""
    return sum(c.isalpha() for c in ligne) >= 3


def _moteur():
    """Moteur RapidOCR, créé une fois ; None si la bibliothèque n'est pas installée."""
    global _MOTEUR
    if _MOTEUR is None:
        try:
            import os
            # pas de télémétrie Microsoft : sous Linux, onnxruntime crée sinon un identifiant d'appareil
            # (~/.cache/Microsoft/DeveloperTools) et peut envoyer des données ; la variable doit précéder l'import
            os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
            import onnxruntime
            onnxruntime.disable_telemetry_events()       # équivalent pour la télémétrie Windows
            from rapidocr import RapidOCR
            _MOTEUR = RapidOCR(params={"Global.log_level": "critical"})    # bavard : un message par image sinon
        except Exception:
            _MOTEUR = False
    return _MOTEUR or None


def lignes(image):
    """Lignes de texte lisibles dans une image (chemin ou PIL.Image)."""
    from PIL import Image
    m = _moteur()
    if m is None:
        return None
    im = image if isinstance(image, Image.Image) else Image.open(image)
    im = im.convert("RGB")
    if im.width > LARGEUR:
        im = im.resize((LARGEUR, round(im.height * LARGEUR / im.width)), Image.LANCZOS)
    r = m(im)
    return [t for t, s in zip(r.txts or (), r.scores or ()) if s >= SEUIL and _utile(t)]


def textes(images):
    """{nom de l'image: [lignes de texte lisibles]} ; None si RapidOCR n'est pas installé."""
    if _moteur() is None:
        return None
    out = {}
    for f in images:
        try:
            found = lignes(f)
        except Exception:                                 # image illisible : on l'ignore
            continue
        if found:
            out[Path(f).stem.lower()] = found
    return out


def verifier(projet_dir, noms=None):
    """Analyse cases/*.png, écrit build/texte_detecte.json et affiche les cases à retoucher."""
    projet_dir = Path(projet_dir)
    files = sorted((projet_dir / "cases").glob("p*_c*.png"))
    if noms is not None:
        files = [f for f in files if f.stem.lower() in noms]
    found = textes(files)
    if found is None:
        print(tr("  (détection de texte indisponible : RapidOCR n'est pas installé; vérifie les cases à l'œil)",
                 "  (text detection unavailable: RapidOCR is not installed; check the cells by eye)"))
        return {}
    (projet_dir / "build").mkdir(exist_ok=True)
    (projet_dir / "build" / "texte_detecte.json").write_text(json.dumps(found, indent=1, ensure_ascii=False),
                                                              encoding="utf-8")
    if found:
        print(tr(f"  ⚠ Texte lisible dans {len(found)} case(s) — à retoucher si ce n'est pas voulu :",
                 f"  ⚠ Readable text in {len(found)} cell(s) — retouch them if it is not intended:"))
        for k, v in found.items():
            print(f"     {k} : « {' / '.join(v)[:80]} »")
    else:
        print(tr("  Aucun texte lisible détecté dans les cases.", "  No readable text detected in the cells."))
    return found
