"""Langue des messages (français par défaut, anglais) : tr("texte français", "English text").

- Interface web : la page envoie sa langue dans l'en-tête X-Lang ; le serveur la fixe pour la requête (fil d'exécution)
  et la transmet aux commandes lancées (variable CLIP_LANG).
- Ligne de commande : CLIP_LANG=en pour l'anglais.

La langue d'un projet (paroles, textes rédigés par Claude, prompts d'images) est un autre réglage : « langue » dans
projet.json, voir langue_projet()."""
import os
import threading

LANGUES = ("fr", "en")
_local = threading.local()


def _norm(v):
    return "en" if str(v or "").lower().startswith("en") else "fr" if v else None


def langue():
    """Langue des messages : celle fixée pour la requête en cours, sinon CLIP_LANG, sinon le français."""
    return getattr(_local, "langue", None) or _norm(os.environ.get("CLIP_LANG")) or "fr"


def fixer(v):
    """Fixe la langue des messages pour le fil d'exécution courant (une requête du serveur web)."""
    _local.langue = _norm(v)


def tr(fr, en):
    return en if langue() == "en" else fr


def langue_projet(cfg):
    """Langue de la chanson et des textes du projet ("fr" | "en")."""
    return _norm(cfg.get("langue")) or "fr"


def tp(cfg, fr, en):
    """Texte dans la langue du projet (demandes à Claude, prompts, textes publiés)."""
    return en if langue_projet(cfg) == "en" else fr
