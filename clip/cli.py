"""Point d'entrée : python -m clip <commande> [args]."""
import argparse
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import PROJETS, ecrire
from .demandes import A_DECRIRE, REFAIRE, SOLOS, VIDEOS

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),   # Linux : équivalent d'Arial
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),                # macOS
    Path("/Library/Fonts/Arial Bold.ttf"),
]
AUDIO_EXT = (".mp3", ".wav", ".flac", ".m4a", ".ogg")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")

PROJET_TEMPLATE = {
    "audio": None,            # None = premier fichier audio trouvé dans le projet
    "paroles": None,          # None = premier .txt trouvé dans le projet
    "planches": "planches",
    "solos": "solos",
    "solos_list": [],         # [] = toutes les images de solos/
    "style": "photoréaliste rock brut satirique, grain cinéma, contraste élevé, éclairage dramatique, palette sombre",
    "intention": "",          # ambiance / sens / contexte de la chanson, décrit par l'auteur
    "personnages": {},
    "descriptions": {},
    "dedupe": True,
    "intro_image": None,
    "outro_image": None,
    "ajustements": {},
    "debut_chant": 0,         # début du chant (s) si l'alignement place les premiers vers trop tôt
    "whisper": "medium",      # calage des paroles : "medium" (~5 Go de mémoire) ou "small" (~2 Go, moins précis)
    "bpm_hint": "auto",       # "auto" = tempo estimé automatiquement, sinon un nombre (BPM) imposé
    "fps": 30,
    "size": [1920, 1080],
    "fit": "cover",
    "cy": 0.4,
    "fade_out": 2.5,
    "bar_alpha": 150,
    "pulse": 1.0,             # 0 = aucun effet au beat (ballade)
    "fondu": 0.15,            # durée du fondu enchaîné entre images (s)
    "camera": "zoom",         # auto = mouvement selon le « Plan » de chaque description
    "look": "aucun",          # cinema = étalonnage + grain + vignettage
    "letterbox": False,       # bandes noires cinéma 2,39:1 (paroles dans la bande du bas)
    "harmonisation": False,   # couleurs des planches rapprochées entre elles
    "variantes": False,       # images répétées : sens / miroir alternés, dernière en N&B
    "look_sections": False,   # refrain plus lumineux, couplets plus sombres, pont désaturé
    "particules": None,       # auto = neige / poussière selon la description, ou "neige"…
    "pulse_mesure": False,    # effet beat seulement sur le 1er temps de chaque mesure
    "titre": None,            # titre d'ouverture (fondu sur l'intro)
    "artiste": None,
    "origine": "suno",        # suno | images | complete : mention IA de la publication
    "generique": True,        # titre — artiste sur les dernières secondes
    "format": "16:9",         # 16:9 | 4k | 9:16 (Shorts/TikTok/Reels) | 1:1
    "volume_normalise": False,  # volume YouTube (-14 LUFS)
    "debut": 0,               # couper le début de la chanson (s)
    "fin": 0,                 # couper la fin (s, 0 = jusqu'au bout)
    "karaoke_mode": "mot",    # mot | ligne | aucun
    "karaoke_taille": 46,
    "karaoke_couleur": "#FFDC50",  # mot chanté
    "karaoke_texte": "#FFFFFF",
    "karaoke_position": "bas",  # bas | haut | centre
    "karaoke_animation": "aucune",  # aucune | grossir | remplir
    "karaoke_suivante": False,  # afficher la ligne suivante
    "karaoke_majuscules": False,
    "karaoke_decalage": 0.0,  # décalage global des paroles (s, + = plus tard)
    "logo": None,             # image du logo (dans le dossier du projet)
    "logo_position": "haut-droite",
    "mention_ia_ecran": False,
    "mention_ia_texte": "Version IA",
    "mention_ia_position": "bas-droite",
    "transition": "fondu",    # fondu | coupe | noir | flash | glissement | zoom
    "duree_max_image": 0,     # découpe les plans plus longs (s, 0 = non)
    "grain": None,            # None = valeur du look
    "vignettage": None,
    "luminosite": 0.0,
    "contraste": 1.0,
    "camera_intensite": 1.0,
    "particules_densite": 1.0,
    "particules_sections": {},  # {"refrain": "braises", "couplet": "aucune", …}
    "fumee": None,            # None | auto | fumee | brouillard
    "fumee_densite": 1.0,
    "flammes": None,          # None | auto | partout (feu au pied de l'image)
    "flammes_hauteur": 0.3,
    "flammes_intensite": 1.0,
    "eclairs": None,          # None | auto | partout
    "rayons": None,           # None | auto | partout (rayons de lumière)
    "rayons_intensite": 1.0,
    "fuites_lumiere": 0.0,    # 0-1
    "projecteurs": 0.0,       # 0-1, flashs colorés au beat
    "tremblement": 0.0,       # 0-1, au beat
    "tremblement_zone": "partout",  # partout | refrains
    "rvb_beat": 0.0,          # 0-1, décalage des couleurs au beat
    "glitch": None,           # None | beats | transitions | les_deux
    "glitch_intensite": 1.0,
    "vieux_film": 0.0,        # 0-1
    "visualiseur": None,      # None | barres | onde
    "visualiseur_zone": "instrumentaux",  # instrumentaux | partout
    "visualiseur_couleur": "#FFDC50",
    "visualiseur_hauteur": 0.12,
    "flou_fond": 0.0,         # 0-1 (utilise les cartes de profondeur)
    "brume_profondeur": 0.0,  # 0-1
    "encoder": "auto",
    "font": None,
    "timeline": [],
}


class Stop(Exception):
    pass


def _ok(label, good, detail=""):
    print(f"  [{'OK' if good else 'XX'}] {label}" + (f" — {detail}" if detail else ""))
    return good


def _ffmpeg_has(kind, name):
    r = subprocess.run(["ffmpeg", "-hide_banner", f"-{kind}"], capture_output=True, text=True)
    return any(line.split()[1:2] == [name] for line in r.stdout.splitlines() if line.strip())


def _amf_works():
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "color=s=640x360:d=0.2",
         "-c:v", "h264_amf", "-f", "null", "-"],
        capture_output=True, text=True)
    return r.returncode == 0


# ------------------------------------------------------------------ projet

def _projet(nom):
    """Charge projet.json et complète automatiquement audio / paroles / solos."""
    p = PROJETS / nom
    f = p / "projet.json"
    if not f.exists():
        raise Stop(f"projet.json introuvable dans {p}")
    cfg = {**PROJET_TEMPLATE, **json.loads(f.read_text(encoding="utf-8-sig"))}
    changed = False
    if not cfg["audio"] or not (p / cfg["audio"]).exists():
        found = sorted(x.name for x in p.iterdir() if x.suffix.lower() in AUDIO_EXT)
        if found:
            cfg["audio"], changed = found[0], True
    if not cfg["paroles"] or not (p / cfg["paroles"]).exists():
        found = sorted(x.name for x in p.iterdir() if x.suffix.lower() == ".txt")
        if found:
            cfg["paroles"], changed = found[0], True
    if not cfg["solos_list"] and (p / cfg["solos"]).is_dir():
        found = sorted(x.name for x in (p / cfg["solos"]).iterdir()
                       if x.suffix.lower() in IMG_EXT and x.stem.lower().startswith("solo"))
        if found:
            cfg["solos_list"], changed = found, True
    if changed:
        _save(p, cfg)
    return p, cfg


def _style(cfg):
    """Style visuel + intention de l'auteur (ambiance, sens, contexte) pour les demandes à Claude.
    L'intention n'est pas envoyée au générateur d'images : seules les descriptions en tiennent compte."""
    s = cfg.get("style", "") or ""
    it = (cfg.get("intention") or "").strip()
    return f"{s}\nIntention de l'auteur (ambiance, sens, contexte — à respecter) : {it}" if it else s


HISTO_MAX = 30          # versions de projet.json gardées dans build/historique/


def _save(p, cfg, garder=False):
    """Écrit projet.json en gardant l'ancienne version dans build/historique/ (au plus une par minute)."""
    f = p / "projet.json"
    txt = json.dumps(cfg, indent=2, ensure_ascii=False)
    if f.exists():
        old = f.read_text(encoding="utf-8-sig")
        if old == txt:
            return
        h = p / "build" / "historique"
        h.mkdir(parents=True, exist_ok=True)
        prev = sorted(h.glob("projet_*.json"))
        import time
        if garder or not prev or time.time() - prev[-1].stat().st_mtime > 60:
            name = time.strftime("projet_%Y%m%d_%H%M%S.json")
            if not (h / name).exists():
                (h / name).write_text(old, encoding="utf-8")
            for x in sorted(h.glob("projet_*.json"))[:-HISTO_MAX]:
                x.unlink()
    ecrire(f, txt)


def _fsig(f):
    """Empreinte d'un fichier d'entrée : nom + taille + date (mp3) ou contenu (texte)."""
    if not f.exists():
        return None
    if f.suffix.lower() == ".txt":
        import hashlib
        import re
        txt = "\n".join(l.strip() for l in f.read_text(encoding="utf-8-sig", errors="replace").splitlines())
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
        return f"{f.name}:{hashlib.sha1(txt.encode()).hexdigest()[:12]}"
    st = f.stat()
    return f"{f.name}:{st.st_size}:{st.st_mtime_ns}"


WHISPER = ("medium", "small")


def _whisper(args, cfg):
    """Modèle Whisper : --model s'il est donné, sinon le réglage du projet (medium par défaut)."""
    m = getattr(args, "model", None) or cfg.get("whisper") or "medium"
    if m not in WHISPER:
        raise Stop(f"Modèle Whisper inconnu : {m} (choix : {', '.join(WHISPER)})")
    return m


def _sig(p, cfg, kind):
    audio = _fsig(p / cfg["audio"]) if cfg.get("audio") else None
    if kind == "beats":
        return f"{audio}|{cfg.get('bpm_hint', 'auto')}"
    paroles = _fsig(p / cfg["paroles"]) if cfg.get("paroles") else None
    m = cfg.get("whisper") or "medium"                # absent pour medium : empreintes d'avant ce réglage inchangées
    return f"{audio}|{paroles}{'' if m == 'medium' else '|' + m}|{float(cfg.get('debut_chant') or 0)}"


def perimes(p, cfg):
    """Analyses à refaire : "beats" et / ou "paroles" (mp3, paroles, tempo imposé, début du chant ou modèle Whisper
    modifiés)."""
    b, out = p / "build", []
    for kind, f in (("beats", b / "beats.npy"), ("paroles", b / "words.json")):
        if not f.exists():
            continue
        saved = cfg.get(f"{kind}_sig")
        if saved is not None:
            stale = saved != _sig(p, cfg, kind)
        else:                                     # projet d'avant les empreintes : comparer les dates
            srcs = [p / cfg[k] for k in (("audio",) if kind == "beats" else ("audio", "paroles")) if cfg.get(k)]
            stale = any(s.exists() and s.stat().st_mtime > f.stat().st_mtime for s in srcs)
        if stale:
            out.append(kind)
    return out


def _analyses_a_jour(p, cfg, args):
    """Refait beats / alignement si le mp3 ou les paroles ont changé depuis « Préparer »."""
    todo = perimes(p, cfg)
    if "beats" in todo:
        print("  ⚠ Le mp3 (ou le tempo imposé) a changé depuis « Préparer » : nouveaux beats")
        cmd_beats(argparse.Namespace(nom=p.name))
    if "paroles" in todo:
        print("  ⚠ Le mp3, les paroles, le début du chant ou le modèle Whisper ont changé depuis « Préparer » : "
              "nouvel alignement")
        cmd_align(argparse.Namespace(nom=p.name, model=getattr(args, "model", None), repair_only=False))
    return _projet(p.name)[1] if todo else cfg


def _need(p, cfg, *keys):
    for k in keys:
        if not cfg.get(k) or not (p / cfg[k]).exists():
            what = "fichier audio (.mp3)" if k == "audio" else "paroles (.txt)"
            raise Stop(f"{what} introuvable dans {p}")


def _duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout)


def _shotlist(p):
    from .shots import load
    sl = load(p / "build" / "shotlist.json")
    if sl is None:
        raise Stop("build/shotlist.json absent : lancer d'abord « prepare » (ou « prompts »)")
    return sl


# ------------------------------------------------------------------ commandes

def cmd_check(_args):
    print("Environnement :")
    good = _ok("Python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0])
    for mod in ("numpy", "PIL", "librosa", "soundfile"):
        try:
            m = importlib.import_module(mod)
            good &= _ok(mod, True, getattr(m, "__version__", ""))
        except ImportError:
            good &= _ok(mod, False, "pip install -r requirements.txt")
    try:
        importlib.import_module("stable_whisper")
        good &= _ok("stable-ts (alignement)", True)
    except ImportError:
        good &= _ok("stable-ts (alignement)", False, "voir requirements.txt")
    try:
        importlib.import_module("rapidocr")
        importlib.import_module("onnxruntime")
        _ok("RapidOCR (texte dans les cases)", True)
    except ImportError:
        print("  [--] RapidOCR (texte dans les cases, optionnel) — relancer l'installateur")
    from .panels import ESRGAN
    good &= _ok("Real-ESRGAN (upscale)", ESRGAN.exists(), str(ESRGAN))
    ff = shutil.which("ffmpeg")
    good &= _ok("ffmpeg dans le PATH", bool(ff), ff or "introuvable")
    if ff:
        good &= _ok("encodeur libx264", _ffmpeg_has("encoders", "libx264"))
        good &= _ok("filtre ass (karaoké)", _ffmpeg_has("filters", "ass"))
        good &= _ok("filtre xfade", _ffmpeg_has("filters", "xfade"))
        print(f"  [{'OK' if _amf_works() else '--'}] h264_amf (GPU AMD, optionnel)")
    font = next((f for f in FONT_CANDIDATES if f.exists()), None)
    good &= _ok("police karaoké", bool(font), str(font) if font else "aucune trouvée")
    print("\nTout est prêt." if good else "\nÉléments manquants ci-dessus.")
    return 0 if good else 1


def cmd_list(_args):
    PROJETS.mkdir(exist_ok=True)
    for d in sorted(x for x in PROJETS.iterdir() if (x / "projet.json").exists()):
        print(d.name)
    return 0


def cmd_new(args):
    p = PROJETS / args.nom
    if p.exists():
        raise Stop(f"Existe déjà : {p}")
    for sub in ("planches", "solos", "retouches", "cases", "build"):
        (p / sub).mkdir(parents=True)
    _save(p, PROJET_TEMPLATE)
    print(f"Projet créé : {p}\n"
          f"Déposer : la chanson (.mp3) et les paroles (.txt) dans le dossier du projet,\n"
          f"          les photos de solo (solo1.png…) dans solos/ (optionnel).")
    return 0


def cmd_beats(args):
    from .audio import detect
    p, cfg = _projet(args.nom)
    _need(p, cfg, "audio")
    (p / "build").mkdir(exist_ok=True)
    _, bpm = detect(p / cfg["audio"], p / "build" / "beats.npy", cfg.get("bpm_hint", "auto"))
    cfg = _projet(args.nom)[1]
    cfg["bpm_detecte"] = bpm                      # affiché dans Clip Studio
    cfg["beats_sig"] = _sig(p, cfg, "beats")
    _save(p, cfg)
    return 0


def cmd_align(args):
    from .lyrics import align, repair
    p, cfg = _projet(args.nom)
    (p / "build").mkdir(exist_ok=True)
    from .lyrics import force_start
    t0 = float(cfg.get("debut_chant") or 0)
    if getattr(args, "repair_only", False):
        f = p / "build" / "words.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        if t0 > 0:                                # début du chant : avant la réparation automatique
            force_start(data["segments"], t0)
        print(f"  réparation : {repair(data['segments'], t0)} mot(s) recollé(s)")
        ecrire(f, json.dumps(data, indent=1, ensure_ascii=False))
        new = _sig(p, cfg, "paroles")             # même mp3 et mêmes paroles : seul le début du chant a bougé
        if (cfg.get("paroles_sig") or "").rsplit("|", 1)[0] == new.rsplit("|", 1)[0]:
            cfg["paroles_sig"] = new
            _save(p, cfg)
        return 0
    _need(p, cfg, "audio", "paroles")
    m = _whisper(args, cfg)
    align(p / cfg["audio"], p / cfg["paroles"], p / "build" / "words.json", model_name=m, debut_chant=t0)
    cfg = _projet(args.nom)[1]
    cfg["whisper"] = m                            # modèle réellement utilisé (--model compris)
    cfg["paroles_sig"] = _sig(p, cfg, "paroles")
    _save(p, cfg)
    return 0


def cmd_prompts(args):
    from .prompts import skeleton
    from .shots import save
    p, cfg = _projet(args.nom)
    _need(p, cfg, "paroles")
    (p / "build").mkdir(exist_ok=True)
    # descriptions : projet.json "descriptions" + build/descriptions.json (réponse de Claude)
    desc = dict(cfg.get("descriptions") or {})
    fj = p / "build" / "descriptions.json"
    if fj.exists():
        try:
            desc.update(json.loads(fj.read_text(encoding="utf-8-sig")))
        except json.JSONDecodeError as e:
            raise Stop(f"build/descriptions.json invalide : {e}")
        pers = desc.pop("_personnages", None)
        if pers and not cfg.get("personnages"):
            cfg["personnages"] = pers
            _save(p, cfg)
            print(f"  {len(pers)} personnage(s) récurrent(s) importé(s) dans projet.json")
    sl, md = skeleton(cfg, p / cfg["paroles"], desc)
    save(sl, p / "build" / "shotlist.json")
    todo = [s for s in sl["shots"] if s["id"] not in desc]
    amb = sum(1 for s in sl["shots"] if s.get("ambiance"))
    print(f"  {len(sl['shots']) - amb} images de vers + {amb} d'ambiance → {len(sl['planches'])} planche(s)")
    for pl in sl["planches"]:
        print(f"    {pl['id'].upper()} : grille {pl['grid'][0]}×{pl['grid'][1]}, format {pl['ratio']}")
    if todo:
        pers = "; ".join(f"{k} = {v}" for k, v in (cfg.get("personnages") or {}).items()) or "(aucun)"
        idees = cfg.get("ambiance_idees") or []
        amb = [s["id"] for s in sl["shots"] if s.get("ambiance")]
        items = "\n".join(f"{s['id']} : {s['text']}" if s["text"] else
                          f"{s['id']} : (ambiance : passage instrumental, liée au thème de la chanson"
                          + (f" ; idée : {idees[amb.index(s['id'])]}" if amb.index(s['id']) < len(idees) else "") + ")"
                          for s in todo)
        pers_todo = "" if cfg.get("personnages") else (
            "\n- Aucun personnage défini : propose 1 à 3 personnages récurrents (apparence précise) "
            "dans la clé \"_personnages\": {\"nom\": \"description\"} du même JSON.")
        (p / "build" / "a_decrire.md").write_text(
            A_DECRIRE.format(style=_style(cfg), pers=pers, items=items, pers_todo=pers_todo),
            encoding="utf-8")
        (p / "build" / "prompts_planches.md").unlink(missing_ok=True)
        print(f"  {len(todo)} image(s) à décrire → {p / 'build' / 'a_decrire.md'}\n"
              f"  (à coller à Claude ; enregistrer sa réponse dans build/descriptions.json, "
              f"puis relancer « prepare »)")
    else:
        (p / "build" / "a_decrire.md").unlink(missing_ok=True)
        (p / "build" / "prompts_planches.md").write_text(md, encoding="utf-8")
        print(f"  Prompts prêts → {p / 'build' / 'prompts_planches.md'}")
    return 0


def cmd_describe(args):
    """Fait rédiger les descriptions par Claude via Claude Code (abonnement de l'utilisateur)."""
    from .ai import ClaudeError, ask_json
    from .lyrics import read_lyrics
    from .shots import build as build_shots
    p, cfg = _projet(args.nom)
    _need(p, cfg, "paroles")
    (p / "build").mkdir(exist_ok=True)
    fj = p / "build" / "descriptions.json"
    desc = json.loads(fj.read_text(encoding="utf-8-sig")) if fj.exists() else {}
    known = {**(cfg.get("descriptions") or {}), **desc}
    sl = build_shots(read_lyrics(p / cfg["paroles"]), dedupe=cfg.get("dedupe", True),
                     ambiance=cfg.get("ambiance", 0))
    shots = {s["id"]: s for s in sl["shots"]}
    pers_dict = cfg.get("personnages") or desc.get("_personnages") or {}
    pers = "; ".join(f"{k} = {v}" for k, v in pers_dict.items()) or "(aucun)"
    consigne = (getattr(args, "consigne", None) or "").strip()
    idees = cfg.get("ambiance_idees") or []
    amb_ids = [s["id"] for s in sl["shots"] if s.get("ambiance")]

    def label(s):
        if s["text"]:
            return s["text"]
        j = amb_ids.index(s["id"])
        idee = f" ; idée : {idees[j]}" if j < len(idees) else ""
        return f"(ambiance : passage instrumental, liée au thème de la chanson{idee})"

    ids = [i.strip().lower() for i in (getattr(args, "ids", None) or "").split(",") if i.strip()]
    if ids:                                                   # refaire des images précises
        bad = [i for i in ids if i not in shots]
        if bad:
            raise Stop(f"Image(s) inconnue(s) : {', '.join(bad)}")
        items = "\n".join(f"{i} : vers « {label(shots[i])} » — description actuelle : "
                          f"{known.get(i, '(aucune)')}" for i in ids)
        prompt = REFAIRE.format(style=_style(cfg), pers=pers, items=items,
                                consigne=f"\n- Consigne de l'utilisateur : {consigne}" if consigne else "")
        print(f"  Claude réécrit {len(ids)} description(s)…")
    else:                                                     # rédiger ce qui manque (ou tout)
        todo = [s for s in sl["shots"] if getattr(args, "tout", False) or s["id"] not in known]
        if not todo:
            print("  Toutes les images sont déjà décrites (option « tout refaire » pour recommencer).")
            return cmd_prompts(args)
        pers_todo = "" if pers_dict else (
            "\n- Aucun personnage défini : propose 1 à 3 personnages récurrents (apparence précise) "
            "dans la clé \"_personnages\": {\"nom\": \"description\"} du même JSON.")
        if consigne:
            pers_todo += f"\n- Consigne de l'utilisateur : {consigne}"
        items = "\n".join(f"{s['id']} : {label(s)}" for s in todo)
        prompt = A_DECRIRE.format(style=_style(cfg), pers=pers, items=items, pers_todo=pers_todo)
        ids = [s["id"] for s in todo]
        print(f"  Claude rédige {len(todo)} description(s) (environ 30 s à 2 min)…")
    try:
        data = ask_json(prompt)
    except ClaudeError as e:
        raise Stop(str(e))
    got = {k: v for k, v in data.items() if k in shots and isinstance(v, str) and v.strip()}
    missing = [i for i in ids if i not in got]
    desc.update(got)
    if isinstance(data.get("_personnages"), dict) and not pers_dict:
        desc["_personnages"] = data["_personnages"]
    ecrire(fj, json.dumps(desc, indent=1, ensure_ascii=False))
    for i in sorted(got):
        print(f"  {i} : {got[i][:110]}{'…' if len(got[i]) > 110 else ''}")
    if missing:
        print(f"  ⚠ sans réponse pour : {', '.join(missing)} (relancer pour les compléter)")
    print(f"  {len(got)} description(s) enregistrée(s)")
    return cmd_prompts(args)


def cmd_publish(args):
    """Titre, description et prompts de miniature YouTube (Claude via l'abonnement + code exact)."""
    from .ai import ClaudeError, ask_json
    from . import publish as pub_mod
    p, cfg = _projet(args.nom)
    _need(p, cfg, "audio", "paroles")
    if not cfg.get("titre") or not cfg.get("artiste"):
        raise Stop("Renseigne d'abord le titre et l'artiste (étape 7 ou Options).")
    paroles = pub_mod.paroles_propres((p / cfg["paroles"]).read_text(encoding="utf-8-sig"))
    wf = p / "build" / "words.json"
    segs = json.loads(wf.read_text(encoding="utf-8"))["segments"] if wf.exists() else []
    chaps = pub_mod.chapitres(segs, _duration(p / cfg["audio"]))
    print(f"  {len(chaps)} chapitre(s) calculé(s) à partir du calage des paroles" if chaps
          else "  Chapitres omis (calage des paroles absent ou chanson trop courte)")
    print("  Claude rédige le titre, l'accroche, les hashtags et la miniature…")
    try:
        ia = ask_json(pub_mod.demande(cfg, paroles, (getattr(args, "consigne", None) or "").strip()))
    except ClaudeError as e:
        raise Stop(str(e))
    pub = {"titre": (ia.get("titre") or "").strip()[:100],
           "description": pub_mod.description(cfg, ia, chaps, paroles),
           "miniature": (ia.get("miniature") or "").strip(),
           "miniature_sans_texte": (ia.get("miniature_sans_texte") or "").strip(),
           "chapitres": chaps}
    (p / "build").mkdir(exist_ok=True)
    pub_mod.save(p / "build", pub)
    print(f"  Titre : {pub['titre']}")
    for c in chaps:
        print(f"    {c}")
    print(f"  → {p / 'build' / 'publication.md'}")
    return 0


def cmd_evaluate(args):
    """Claude évalue le storyboard : images d'ambiance nécessaires, idées, préréglage conseillé."""
    import numpy as np
    from .ai import ClaudeError, ask_json
    from . import evaluate as ev
    from .lyrics import read_lyrics
    from .publish import paroles_propres
    p, cfg = _projet(args.nom)
    _need(p, cfg, "audio", "paroles")
    ef = p / "build" / "evaluation.json"
    if getattr(args, "appliquer", False) and ef.exists():     # applique l'évaluation affichée, sans rappeler Claude
        ia = json.loads(ef.read_text(encoding="utf-8"))["ia"]
        cfg["ambiance"], cfg["ambiance_idees"] = ia["ambiance"], ia.get("idees_ambiance", [])
        _save(p, cfg)
        print(f"  Appliqué : {ia['ambiance']} image(s) d'ambiance")
        return cmd_prompts(args)
    wf = p / "build" / "words.json"
    if not wf.exists():
        raise Stop("Paroles pas encore calées : lance d'abord « Préparer ».")
    segs = json.loads(wf.read_text(encoding="utf-8"))["segments"]
    bf = p / "build" / "beats.npy"
    bpm = None
    if bf.exists():
        b = np.load(bf)
        bpm = 60 / float(np.median(np.diff(b))) if len(b) > 2 else None
    f = ev.faits(segs, _duration(p / cfg["audio"]), read_lyrics(p / cfg["paroles"]),
                 cfg.get("ambiance", 0), len(cfg.get("solos_list") or []), bpm)
    print(f"  {f['vers']} vers, {f['images_de_vers']} images de vers, {f['instrumental_total']} s sans paroles "
          f"en {len(f['passages_sans_paroles'])} passage(s), {f['photos_de_solo']} photo(s) de solo")
    print("  Claude évalue le storyboard…")
    try:
        ia = ask_json(ev.demande(cfg, paroles_propres((p / cfg["paroles"]).read_text(encoding="utf-8-sig")), f))
    except ClaudeError as e:
        raise Stop(str(e))
    n = max(0, min(12, int(ia.get("ambiance", 0) or 0)))
    ia["ambiance"] = n
    ia["idees_ambiance"] = [str(x) for x in (ia.get("idees_ambiance") or [])][:n]
    (p / "build" / "evaluation.json").write_text(json.dumps({"faits": f, "ia": ia}, indent=1, ensure_ascii=False),
                                                 encoding="utf-8")
    from .shots import _pack
    print(f"  Recommandation : {n} image(s) d'ambiance → {f['images_de_vers'] + n} images, "
          f"{len(_pack(f['images_de_vers'] + n))} planche(s) ; préréglage « {ia.get('preset', '?')} »")
    print(f"  {ia.get('raison', '')}")
    for r in ia.get("remarques") or []:
        print(f"  • {r}")
    if getattr(args, "appliquer", False):
        cfg["ambiance"], cfg["ambiance_idees"] = n, ia["idees_ambiance"]
        _save(p, cfg)
        print(f"  Appliqué : {n} image(s) d'ambiance")
        return cmd_prompts(args)
    return 0


def cmd_solos(args):
    """Prompts d'images panoramiques pour les passages instrumentaux (Claude via l'abonnement)."""
    from .ai import ClaudeError, ask_json
    from .publish import paroles_propres
    p, cfg = _projet(args.nom)
    _need(p, cfg, "paroles")
    n = max(1, min(8, int(getattr(args, "nombre", None) or 3)))
    ef = p / "build" / "evaluation.json"
    passages = "inconnus"
    if ef.exists():
        f = json.loads(ef.read_text(encoding="utf-8"))["faits"]
        passages = ", ".join(f"{t['type']} {t['duree']} s" for t in f["passages_sans_paroles"]) or "aucun"
    pers = "; ".join(f"{k} = {v}" for k, v in (cfg.get("personnages") or {}).items()) or "(aucun)"
    consigne = (getattr(args, "consigne", None) or "").strip()
    prompt = SOLOS.format(titre=cfg.get("titre") or "(sans titre)", artiste=cfg.get("artiste") or "",
                          style=_style(cfg), pers=pers, passages=passages, n=n,
                          paroles=paroles_propres((p / cfg["paroles"]).read_text(encoding="utf-8-sig")),
                          consigne=f"\nConsigne de l'utilisateur : {consigne}" if consigne else "")
    print(f"  Claude écrit {n} prompt(s) de photo de solo…")
    try:
        data = ask_json(prompt)
    except ClaudeError as e:
        raise Stop(str(e))
    solos = [s for s in (data.get("solos") or []) if isinstance(s, dict) and s.get("prompt")][:n]
    if not solos:
        raise Stop("Claude n'a renvoyé aucun prompt exploitable")
    (p / "build").mkdir(exist_ok=True)
    (p / "build" / "solos.json").write_text(json.dumps({"solos": solos}, indent=1, ensure_ascii=False), encoding="utf-8")
    md = ["# Prompts des photos de solo (panoramiques 21:9)\n",
          "Enregistrer chaque image sous `solos/solo1.png`, `solo2.png`… (ou la déposer dans Clip Studio, étape 2).\n"]
    for i, s in enumerate(solos, 1):
        md += [f"## solo{i} — {s.get('titre', '')}\n", "```", s["prompt"].strip(), "```\n"]
        print(f"  solo{i} : {s.get('titre', '')}")
    (p / "build" / "prompts_solos.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  → {p / 'build' / 'prompts_solos.md'}")
    return 0


def _screen_time(p, cfg):
    """Temps d'écran par image (cases et photos de solo) d'après la timeline : {id: [(début, durée), …]}."""
    from collections import defaultdict
    tl = sorted(cfg.get("timeline") or [], key=lambda e: e["t"])
    dur = _duration(p / cfg["audio"])
    occ = defaultdict(list)
    for i, e in enumerate(tl):
        end = tl[i + 1]["t"] if i + 1 < len(tl) else dur
        k = e.get("img") or Path(e.get("travel", "")).stem.lower()
        if k:
            occ[k].append((round(e["t"], 1), round(end - e["t"], 1)))
    return occ


def cmd_videos(args):
    """Prompts vidéo (Flow / Veo) pour les images les plus longtemps à l'écran — uniquement à la demande."""
    from .ai import ClaudeError, ask_json
    p, cfg = _projet(args.nom)
    ids = [i.strip().lower() for i in (getattr(args, "ids", None) or "").split(",") if i.strip()]
    if not ids and not cfg.get("timeline"):
        raise Stop("Pas encore de montage : fais d'abord un aperçu ou un rendu (étape Rendu), ou choisis une image précise.")
    if cfg.get("timeline"):
        cfg = _plan_a_jour(p, cfg)
    occ = _screen_time(p, cfg) if cfg.get("timeline") else {}
    desc = {}
    fj = p / "build" / "descriptions.json"
    if fj.exists():
        desc.update(json.loads(fj.read_text(encoding="utf-8-sig")))
    desc.update(cfg.get("descriptions") or {})
    fs = p / "build" / "solos.json"
    if fs.exists():
        for i, s in enumerate(json.loads(fs.read_text(encoding="utf-8-sig")).get("solos", []), 1):
            desc.setdefault(f"solo{i}", s.get("prompt", ""))
    if not ids:                                   # les plus longtemps à l'écran (plans d'au moins ~4 s)
        n = max(1, min(8, int(getattr(args, "nombre", None) or 5)))
        cand = [k for k, v in occ.items() if max(d for _, d in v) >= 4.0] or list(occ)
        ids = sorted(cand, key=lambda k: -sum(d for _, d in occ[k]))[:n]
    sd = p / cfg.get("solos", "solos")
    solos = {f.stem.lower() for f in sd.glob("*")} if sd.is_dir() else set()
    bad = [i for i in ids if i not in desc and i not in solos and not (p / "cases" / f"{i}.png").exists()]
    if bad:
        raise Stop(f"Image(s) inconnue(s) : {', '.join(bad)}")
    fmt = lambda k: " + ".join(f"{d} s à {int(t // 60)}:{int(t % 60):02d}" for t, d in occ.get(k, []))
    items = "\n".join(f"- {k} — {fmt(k)} — {desc.get(k, '(pas de description : photo de solo)')[:600]}" for k in ids)
    pers = "; ".join(f"{k} = {v}" for k, v in (cfg.get("personnages") or {}).items()) or "(aucun)"
    consigne = (getattr(args, "consigne", None) or "").strip()
    print(f"  Claude écrit {len(ids)} prompt(s) vidéo : {', '.join(ids)}")
    try:
        data = ask_json(VIDEOS.format(titre=cfg.get("titre") or "(sans titre)", artiste=cfg.get("artiste") or "",
                                      style=_style(cfg), pers=pers, items=items,
                                      consigne=f"\nConsigne de l'utilisateur : {consigne}" if consigne else ""))
    except ClaudeError as e:
        raise Stop(str(e))
    vids = [dict(v, ecran=fmt(v["id"])) for v in (data.get("videos") or [])
            if isinstance(v, dict) and v.get("id") in ids and v.get("prompt")]
    if not vids:
        raise Stop("Claude n'a renvoyé aucun prompt exploitable")
    fv = p / "build" / "videos.json"
    if getattr(args, "ids", None) and fv.exists():  # image précise : on garde les autres prompts
        keep = [v for v in json.loads(fv.read_text(encoding="utf-8-sig")).get("videos", []) if v.get("id") not in ids]
        vids = keep + vids
    (p / "build" / "videos.json").write_text(json.dumps({"videos": vids}, indent=1, ensure_ascii=False), encoding="utf-8")
    md = ["# Prompts vidéo pour Flow (image vers vidéo, ~10 s)\n",
          "Dans Flow : « Images vers vidéo », image de départ = l'image indiquée, format 16:9, puis coller le prompt.",
          "Déposer chaque vidéo dans `videos/` avec le même nom que l'image (`solo1.mp4`, `p4_c4.mp4`…).\n"]
    for v in vids:
        src = f"solos/{v['id']}.png" if v["id"].startswith("solo") else f"cases/{v['id']}.png"
        md += [f"## {v['id']} — {v.get('titre', '')}", f"Image de départ : `{src}` · à l'écran : {v['ecran']}\n",
               "```", v["prompt"].strip(), "```\n"]
        print(f"  {v['id']} : {v.get('titre', '')}")
    (p / "build" / "prompts_videos.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  → {p / 'build' / 'prompts_videos.md'}")
    return 0


def cmd_prepare(args):
    """beats + alignement (si absents ou --force) + prompts."""
    p, cfg = _projet(args.nom)
    _need(p, cfg, "audio", "paroles")
    b = p / "build"
    old = perimes(p, cfg)
    if args.force or not (b / "beats.npy").exists() or "beats" in old:
        print("[1/4] Beats" + (" (mp3 modifié)" if "beats" in old else "")); cmd_beats(args)
    else:
        print("[1/4] Beats : déjà faits")
    if args.force or not (b / "words.json").exists() or "paroles" in old:
        print("[2/4] Alignement des paroles" + (" (mp3, paroles, début du chant ou modèle modifiés)" if "paroles" in old else ""))
        cmd_align(args)
    else:
        print("[2/4] Alignement : déjà fait")
    from .ai import find_claude
    pdir = p / cfg.get("planches", "planches")
    planches_faites = pdir.is_dir() and any(pdir.glob("P*.*"))
    if find_claude() and (args.force or not (b / "evaluation.json").exists()):
        print("[3/4] Évaluation du storyboard par Claude")
        try:
            # appliquée automatiquement tant qu'aucune planche n'est générée (sinon : simple conseil)
            cmd_evaluate(argparse.Namespace(nom=args.nom, appliquer=False))
            if not planches_faites:
                ev = json.loads((b / "evaluation.json").read_text(encoding="utf-8"))["ia"]
                cfg = _projet(args.nom)[1]
                cfg["ambiance"], cfg["ambiance_idees"] = ev["ambiance"], ev["idees_ambiance"]
                _save(p, cfg)
                print(f"  Appliqué : {ev['ambiance']} image(s) d'ambiance")
            else:
                print("  Planches déjà générées : recommandation non appliquée (voir l'étape 2)")
        except Stop as e:
            print(f"  ⚠ Évaluation impossible : {e}")
    else:
        print("[3/4] Évaluation : " + ("déjà faite" if find_claude() else "Claude Code introuvable, ignorée"))
    print("[4/4] Prompts"); cmd_prompts(args)
    return 0


def cmd_verify(args):
    from .panels import verify
    p, cfg = _projet(args.nom)
    problems = verify(p, cfg.get("planches", "planches"), _shotlist(p))
    print("\nPlanches OK." if not problems else f"\n{len(problems)} problème(s) : régénérer les planches concernées "
          f"ou continuer quand même (recadrage).")
    return 0 if not problems else 2


def cmd_cut(args):
    from .panels import cut_all
    p, cfg = _projet(args.nom)
    (p / "build").mkdir(exist_ok=True)
    sl = _shotlist(p)
    cut_all(p, cfg.get("planches", "planches"), scale=getattr(args, "scale", 4),
            grids={pl["id"]: tuple(pl["grid"]) for pl in sl["planches"]})
    missing = [s["id"] for s in sl["shots"]
               if not (p / "cases" / f"{s['id']}.png").exists()]
    if missing:
        print(f"  ⚠ cases manquantes : {', '.join(missing)}")
    from .ocr import verifier
    verifier(p, {s["id"] for s in sl["shots"]})           # légendes, enseignes… (avertissement seulement)
    return 0


def _plan_sig(p, cfg):
    """Empreinte des entrées du montage : s'il change, la timeline est périmée."""
    b = p / "build"
    parts = [cfg.get("audio"), *(f"{f.name}:{f.stat().st_mtime_ns}" for f in
             (p / (cfg.get("audio") or "-"), b / "words.json", b / "beats.npy", b / "shotlist.json") if f.exists()),
             cfg.get("solos_list"), cfg.get("intro_image"), cfg.get("outro_image")]
    return json.dumps(parts, ensure_ascii=False)


def _plan_a_jour(p, cfg):
    """Refait la timeline si elle ne correspond plus au mp3 / paroles calées / beats / planches / solos."""
    if cfg.get("timeline") and cfg.get("timeline_sig") == _plan_sig(p, cfg):
        return cfg
    print("  Montage périmé (mp3, paroles, beats, planches ou solos modifiés) : recalcul du plan")
    cmd_plan(argparse.Namespace(nom=p.name, force=True, quiet=True))
    return _projet(p.name)[1]


def cmd_plan(args):
    import numpy as np
    from .plan import build
    p, cfg = _projet(args.nom)
    if cfg.get("timeline") and not args.force:
        raise Stop("projet.json a déjà une timeline (--force pour la régénérer ; "
                   "les « ajustements », intro_image et outro_image sont conservés)")
    sl = _shotlist(p)
    segs = json.loads((p / "build" / "words.json").read_text(encoding="utf-8"))["segments"]
    beats = np.load(p / "build" / "beats.npy").tolist()
    cfg["timeline"] = build(segs, beats, cfg, _duration(p / cfg["audio"]), sl)
    cfg["timeline_sig"] = _plan_sig(p, cfg)
    _save(p, cfg)
    if not getattr(args, "quiet", False):
        for e in cfg["timeline"]:
            print(f"  {e['t']:7.2f}  {e.get('img') or '~ ' + e['travel']:14s} {e['note']}")
    print(f"  {len(cfg['timeline'])} plans")
    return 0


def cmd_render(args):
    from .render import render
    p, cfg = _projet(args.nom)
    cfg = _plan_a_jour(p, _analyses_a_jour(p, cfg, args))
    out = render(p, cfg, preview=args.preview, start=args.start, duration=args.duration,
                 out_name=getattr(args, "out", None))
    print(f"  → {out}")
    return 0


def cmd_build(args):
    """vérification + découpe + plan + rendu (aperçu ou final)."""
    p, cfg = _projet(args.nom)
    _analyses_a_jour(p, cfg, args)
    print("[1/4] Vérification des planches")
    if cmd_verify(args) != 0 and not args.force:
        raise Stop("Planches à corriger (ou relancer avec --force pour continuer malgré tout)")
    print("[2/4] Découpe + upscale"); cmd_cut(args)
    print("[3/4] Plan"); cmd_plan(argparse.Namespace(nom=args.nom, force=True, quiet=True))
    print("[4/4] Rendu"); cmd_render(args)
    return 0


def main():
    ap = argparse.ArgumentParser(prog="clip")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_, nom=True):
        s = sub.add_parser(name, help=help_)
        if nom:
            s.add_argument("nom")
        s.set_defaults(fn=fn)
        return s

    add("check", cmd_check, "Vérifie l'environnement", nom=False)
    add("web", lambda a: __import__("clip.web", fromlist=["serve"]).serve() or 0,
        "Ouvre Clip Studio (interface web locale)", nom=False)
    add("list", cmd_list, "Liste les projets", nom=False)
    add("new", cmd_new, "Crée un projet dans projets/<nom>")
    s = add("prepare", cmd_prepare, "Beats + alignement + prompts (tout ce qui précède les planches)")
    s.add_argument("--force", action="store_true", help="Refait beats et alignement")
    s.add_argument("--model", default=None, choices=WHISPER, help="Modèle Whisper (défaut : réglage du projet)")
    for name, prev, h in (("build", False, "Vérif + découpe + plan + rendu final"),
                          ("build-preview", True, "Vérif + découpe + plan + aperçu")):
        s = add(name, cmd_build, h)
        s.add_argument("--force", action="store_true", help="Continue malgré les problèmes de planches")
        s.set_defaults(preview=prev, start=None, duration=None, scale=4)
    s = add("describe", cmd_describe, "Descriptions rédigées par Claude (Claude Code, abonnement)")
    s.add_argument("--ids", default=None, help="Images à refaire, ex. p1_c2,p3_c1")
    s.add_argument("--consigne", default=None, help="Consigne libre, ex. « plus sombre »")
    s.add_argument("--tout", action="store_true", help="Réécrire toutes les descriptions")
    s = add("evaluate", cmd_evaluate, "Claude évalue le storyboard (images d'ambiance, préréglage)")
    s.add_argument("--appliquer", action="store_true", help="Applique le nombre d'images recommandé")
    s = add("videos", cmd_videos, "Prompts vidéo Flow/Veo (à la demande seulement, Claude)")
    s.add_argument("--nombre", type=int, default=5)
    s.add_argument("--ids", default=None, help="Images précises, ex. solo1,p4_c4")
    s.add_argument("--consigne", default=None)
    s = add("solos", cmd_solos, "Prompts de photos de solo panoramiques (Claude, abonnement)")
    s.add_argument("--nombre", type=int, default=3)
    s.add_argument("--consigne", default=None)
    s = add("publish", cmd_publish, "Titre, description et miniature YouTube (Claude, abonnement)")
    s.add_argument("--consigne", default=None)
    add("verify", cmd_verify, "Contrôle les planches (format, grille, taille)")
    s = add("cut", cmd_cut, "Découpe les planches en cases + retouches + upscale")
    s.add_argument("--scale", type=int, default=4, help="1 = sans upscale")
    add("beats", cmd_beats, "Détecte les beats → build/beats.npy")
    s = add("align", cmd_align, "Alignement mot-à-mot des paroles → build/words.json")
    s.add_argument("--model", default=None, choices=WHISPER, help="Modèle Whisper (défaut : réglage du projet)")
    s.add_argument("--repair-only", action="store_true", help="Répare words.json sans réaligner")
    add("prompts", cmd_prompts, "Shotlist + prompts (ou liste à décrire) → build/")
    s = add("plan", cmd_plan, "Génère la timeline dans projet.json")
    s.add_argument("--force", action="store_true")
    for name, prev in (("render", False), ("preview", True)):
        s = add(name, cmd_render, ("Aperçu 960×540@15" if prev else "Rendu final") + " avec audio")
        s.add_argument("--start", type=float, default=None)
        s.add_argument("--duration", type=float, default=None)
        s.add_argument("--out", default=None, help="Nom du fichier de sortie dans build/")
        s.set_defaults(preview=prev)
    args = ap.parse_args()
    try:
        sys.exit(args.fn(args))
    except Stop as e:
        print(f"\n✗ {e}")
        sys.exit(1)
