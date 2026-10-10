"""Pipeline de création de clips musicaux illustrés (karaoké + beat-sync)."""
import sys
from pathlib import Path

# Sortie redirigée sous Windows (fichier, tube) : encodage cp1252 qui ne connaît pas « → » ni « ✨ ».
# Un caractère impossible devient « ? » au lieu de faire planter la commande.
for _flux in (sys.stdout, sys.stderr):
    if _flux and hasattr(_flux, "reconfigure") and (_flux.encoding or "").lower().replace("-", "") != "utf8":
        _flux.reconfigure(errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PROJETS = ROOT / "projets"
