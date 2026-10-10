"""Pipeline de création de clips musicaux illustrés (karaoké + beat-sync)."""
import os
import sys
from pathlib import Path

# Sortie redirigée sous Windows (fichier, tube) : encodage cp1252 qui ne connaît pas « → » ni « ✨ ».
# Un caractère impossible devient « ? » au lieu de faire planter la commande.
for _flux in (sys.stdout, sys.stderr):
    if _flux and hasattr(_flux, "reconfigure") and (_flux.encoding or "").lower().replace("-", "") != "utf8":
        _flux.reconfigure(errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROJETS = ROOT / "projets"

# ffmpeg installé par Clip Studio (Windows : téléchargé ; macOS : liens vers ffmpeg-full) : prioritaire sur le PATH
_FFMPEG = ROOT / "tools" / "ffmpeg" / "bin"
if _FFMPEG.is_dir() and str(_FFMPEG) not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = str(_FFMPEG) + os.pathsep + os.environ.get("PATH", "")


def ecrire(path, txt):
    """Écrit un fichier texte d'un coup : fichier temporaire puis remplacement. Une coupure (plantage, courant)
    laisse l'ancienne version intacte au lieu d'un fichier vide ou tronqué."""
    import time
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(txt, encoding="utf-8")
    for essai in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:                   # Windows : fichier lu au même instant par un autre processus
            if essai == 4:
                raise
            time.sleep(0.1)
