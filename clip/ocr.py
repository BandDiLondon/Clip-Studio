"""Détection de texte lisible dans les cases (OCR intégré à Windows, via ocr.ps1) : légendes, enseignes,
numéros que le générateur d'images a écrits malgré le prompt. Avertissement seulement, jamais bloquant."""
import json
import subprocess
import sys
from pathlib import Path

PS1 = Path(__file__).with_name("ocr.ps1")
LOT = 60          # images par appel PowerShell (longueur max de la ligne de commande)


def _utile(ligne):
    """Ignore les bribes (« 00 », « a ») que l'OCR lit parfois dans les textures."""
    lettres = sum(c.isalpha() for c in ligne)
    return lettres >= 3


def textes(images):
    """{nom de l'image: [lignes de texte lisibles]} ; {} si l'OCR Windows est indisponible."""
    if sys.platform != "win32" or not images:
        return {}
    out = {}
    images = [str(Path(i)) for i in images]
    for k in range(0, len(images), LOT):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
                                *images[k:k + LOT]], capture_output=True, text=True, encoding="utf-8", timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            return out
        for line in r.stdout.splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("erreur") and not d.get("f"):
                return out
            lignes = [x for x in d.get("lignes") or [] if _utile(x)]
            if lignes:
                out[Path(d["f"]).stem.lower()] = lignes
    return out


def verifier(projet_dir, noms=None):
    """Analyse cases/*.png, écrit build/texte_detecte.json et affiche les cases à retoucher."""
    projet_dir = Path(projet_dir)
    files = sorted((projet_dir / "cases").glob("p*_c*.png"))
    if noms is not None:
        files = [f for f in files if f.stem.lower() in noms]
    found = textes(files)
    (projet_dir / "build").mkdir(exist_ok=True)
    (projet_dir / "build" / "texte_detecte.json").write_text(json.dumps(found, indent=1, ensure_ascii=False),
                                                              encoding="utf-8")
    if found:
        print(f"  ⚠ Texte lisible dans {len(found)} case(s) — à retoucher si ce n'est pas voulu :")
        for k, v in found.items():
            print(f"     {k} : « {' / '.join(v)[:80]} »")
    else:
        print("  Aucun texte lisible détecté dans les cases.")
    return found
