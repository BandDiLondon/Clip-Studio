"""Clip Studio : interface web locale (127.0.0.1 uniquement) qui pilote le pipeline `python -m clip`.
Aucune dépendance : http.server de la bibliothèque standard."""
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import PROJETS, ROOT

HERE = Path(__file__).resolve().parent / "web"
PORT = 8765
NOM_RE = re.compile(r"^[\w\-]+$")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
AUDIO_EXT = (".mp3", ".wav", ".flac", ".m4a", ".ogg")

# commandes autorisées depuis l'interface → options acceptées
COMMANDS = {
    "prepare": {"--force"}, "prompts": set(), "verify": set(), "cut": set(),
    "plan": {"--force"}, "build-preview": {"--force"}, "build": {"--force"},
    "render": {"--out"}, "preview": {"--start", "--duration"}, "align": {"--repair-only"},
    "describe": {"--ids", "--consigne", "--tout"},
    "publish": {"--consigne"},
    "evaluate": {"--appliquer"},
    "solos": {"--nombre", "--consigne"},
    "videos": {"--nombre", "--consigne", "--ids"},
}
# valeur attendue après une option qui en prend une
ARG_VALUES = {
    "--out": re.compile(r"^[\w\-]+\.mp4$"),
    "--ids": re.compile(r"^(p\d+_c\d+|solo\d+)(,(p\d+_c\d+|solo\d+))*$", re.I),
    "--consigne": re.compile(r"^[^\x00-\x1f]{1,300}$"),
    "--nombre": re.compile(r"^[1-8]$"),
    "--start": re.compile(r"^\d{1,4}(\.\d{1,2})?$"),
    "--duration": re.compile(r"^\d{1,4}(\.\d{1,2})?$"),
}
NOISE = ("Warning", "warn(", "symlinks", "developer mode", "Loading weights", "docs.microsoft",
         "order to activate", "UserWarning", "FutureWarning")


# ------------------------------------------------------------------ tâche en cours

class Job:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.reset("", "")

    def reset(self, nom, label):
        self.nom, self.label = nom, label
        self.lines, self.progress, self.total = [], "", 0
        self.frame, self.code, self.started = 0, None, time.time()

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, nom, cmd, args):
        with self.lock:
            if self.running():
                raise RuntimeError("Une tâche est déjà en cours")
            self.reset(nom, " ".join([cmd] + args))
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
            self.proc = subprocess.Popen([sys.executable, "-m", "clip", cmd, nom, *args], cwd=ROOT, env=env,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()

    def _read(self, proc):
        buf = b""
        while True:
            chunk = proc.stdout.read1(4096)
            if not chunk:
                break
            buf += chunk
            parts = re.split(rb"[\r\n]", buf)
            buf = parts.pop()
            for raw in parts:
                self._line(raw.decode("utf-8", "replace"))
        if buf:
            self._line(buf.decode("utf-8", "replace"))
        self.code = proc.wait()

    def _line(self, s):
        s = s.rstrip()
        if not s:
            return
        m = re.search(r"(\d+) frames", s)
        if m:
            self.total, self.frame = int(m.group(1)), 0
        if s.startswith("frame="):                     # progression ffmpeg : une seule ligne
            m = re.search(r"frame=\s*(\d+)", s)
            self.frame = int(m.group(1)) if m else self.frame
            self.progress = s
            return
        if any(k in s for k in NOISE) or "%|" in s:
            return
        self.lines.append(s)
        self.lines = self.lines[-400:]

    def state(self):
        return {"nom": self.nom, "label": self.label, "running": self.running(), "code": self.code,
                "lines": self.lines, "progress": self.progress,
                "pct": min(100.0, round(100 * self.frame / self.total, 1)) if self.total else None,
                "elapsed": round(time.time() - self.started)}


JOB = Job()
STARTED = time.time()


def _ouvrir(f, montrer=False):
    """Ouvre un fichier ou un dossier avec l'application du système ; montrer = dossier avec le fichier sélectionné."""
    if sys.platform == "win32":
        return subprocess.Popen(["explorer", "/select,", str(f)]) if montrer else os.startfile(f)
    if sys.platform == "darwin":
        return subprocess.Popen(["open", "-R", str(f)] if montrer else ["open", str(f)])
    try:                                              # Linux : pas de sélection, on ouvre le dossier
        subprocess.Popen(["xdg-open", str(f.parent if montrer else f)])
    except FileNotFoundError:
        raise ValueError(f"Impossible d'ouvrir automatiquement (xdg-open absent) : {f}")


def code_perime():
    """Vrai si le code Python a changé depuis le lancement : la page est relue à chaque visite,
    mais le serveur garde l'ancien code tant qu'il n'est pas relancé."""
    base = Path(__file__).resolve().parent
    return any(f.stat().st_mtime > STARTED for f in base.glob("*.py"))


# ------------------------------------------------------------------ état d'un projet

def _cfg(p):
    return json.loads((p / "projet.json").read_text(encoding="utf-8-sig"))


def _save_cfg(p, cfg):
    from .cli import _save                        # garde l'historique (build/historique/)
    _save(p, cfg)


def _project(nom):
    if not NOM_RE.match(nom or ""):
        raise ValueError("Nom de projet invalide (lettres, chiffres, - et _ seulement)")
    p = PROJETS / nom
    if not (p / "projet.json").exists():
        raise FileNotFoundError(f"Projet introuvable : {nom}")
    return p


def _read(f, default=""):
    return f.read_text(encoding="utf-8-sig") if f.exists() else default


def status(nom):
    from .cli import _projet, perimes             # complète audio / paroles / solos automatiquement
    p, cfg = _projet(nom)
    b = p / "build"
    sl = json.loads(_read(b / "shotlist.json", "null"))
    desc, desc_err = {}, False
    try:
        desc = json.loads(_read(b / "descriptions.json", "{}"))
    except json.JSONDecodeError:
        desc_err = True
    desc.update(cfg.get("descriptions") or {})
    pdir = p / cfg.get("planches", "planches")
    files = {f.stem.lower(): f.name for f in pdir.glob("*") if f.suffix.lower() in IMG_EXT} if pdir.is_dir() else {}
    planches = []
    if sl:
        for pl in sl["planches"]:
            ids = [s["id"] for s in sl["shots"] if s["id"].startswith(pl["id"] + "_")]
            planches.append({**pl, "fichier": files.get(pl["id"]),
                             "decoupees": sum((p / "cases" / f"{i}.png").exists() for i in ids)})
    retouches = sorted(f.stem.lower() for f in (p / "retouches").glob("*")
                       if f.suffix.lower() in IMG_EXT) if (p / "retouches").is_dir() else []
    shots = [{"id": s["id"], "texte": s.get("text"), "ambiance": bool(s.get("ambiance")),
              "sections": s.get("sections", []), "description": desc.get(s["id"], ""),
              "case": (p / "cases" / f"{s['id']}.png").exists(), "retouche": s["id"] in retouches}
             for s in (sl["shots"] if sl else [])]
    videos = sorted(({"nom": f.name, "taille": f.stat().st_size, "date": f.stat().st_mtime}
                     for f in b.glob("*.mp4")), key=lambda v: -v["date"]) if b.is_dir() else []
    solos_dir = p / cfg.get("solos", "solos")
    audio_ok = bool(cfg.get("audio") and (p / cfg["audio"]).exists())
    paroles_ok = bool(cfg.get("paroles") and (p / cfg["paroles"]).exists())
    return {
        "nom": nom, "cfg": cfg,
        "audio": cfg.get("audio") if audio_ok else None,
        "paroles": cfg.get("paroles") if paroles_ok else None,
        "paroles_texte": _read(p / cfg["paroles"]) if paroles_ok else "",
        "beats": (b / "beats.npy").exists(), "words": (b / "words.json").exists(),
        "shots": shots, "planches": planches,
        "a_decrire": _read(b / "a_decrire.md"), "prompts": _read(b / "prompts_planches.md"),
        "desc_erreur": desc_err, "contact": (b / "planche_contact.jpg").exists(),
        "timeline": len(cfg.get("timeline") or []),
        "solos": sorted(f.name for f in solos_dir.glob("*") if f.suffix.lower() in IMG_EXT
                        and f.stem.lower().startswith("solo")) if solos_dir.is_dir() else [],
        "videos": videos,
        "publication": json.loads(_read(b / "publication.json", "null")),
        "evaluation": json.loads(_read(b / "evaluation.json", "null")),
        "clips_prompts": (json.loads(_read(b / "videos.json", "null")) or {}).get("videos", []),
        "clips": sorted(f.name for f in (p / "videos").glob("*") if f.suffix.lower() in (".mp4", ".mov", ".webm", ".m4v"))
        if (p / "videos").is_dir() else [],
        "solos_prompts": (json.loads(_read(b / "solos.json", "null")) or {}).get("solos", []),
        "solos_dir": cfg.get("solos", "solos"),
        "perimes": perimes(p, cfg),
        "texte_detecte": json.loads(_read(b / "texte_detecte.json", "{}")),
        "historique": [{"nom": f.name, "date": time.strftime("%d/%m/%Y %H:%M", time.localtime(f.stat().st_mtime))}
                       for f in sorted((b / "historique").glob("projet_*.json"), reverse=True)]
        if (b / "historique").is_dir() else [],
    }


# ------------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _err(self, e, code=400):
        self._json({"erreur": str(e)}, code)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _file(self, f):
        if not f.is_file():
            return self._err("Fichier introuvable", 404)
        size = f.stat().st_size
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix in (".md", ".txt", ".json") or ctype.startswith("text/"):
            ctype = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}.get(f.suffix, "text/plain")                 + "; charset=utf-8"
        start, end = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        if m and size:                                  # lecture vidéo avec avance rapide
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), end) if m.group(2) else end
            else:
                start = max(0, size - int(m.group(2)))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(max(0, end - start + 1)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(f, "rb") as fh:
                fh.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def _etranger(self):
        """Refuse une requête venue d'un autre site : Host autre que 127.0.0.1 / localhost (rebinding DNS)
        ou Origin étranger (page web qui viserait le serveur local)."""
        port = self.server.server_address[1]
        hotes = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origine = self.headers.get("Origin")
        if (self.headers.get("Host") or "").lower() not in hotes or                 (origine is not None and origine.lower() not in {f"http://{h}" for h in hotes}):
            self._err("Requête refusée : elle ne vient pas de Clip Studio", 403)
            return True
        return False

    def _parts(self):
        u = urlparse(self.path)
        return [unquote(x) for x in u.path.strip("/").split("/") if x], \
            {k: v[0] for k, v in parse_qs(u.query).items()}

    def do_GET(self):
        if self._etranger():
            return
        parts, _ = self._parts()
        try:
            if not parts:
                return self._file(HERE / "index.html")
            if parts[0] == "web" and len(parts) == 2 and parts[1] in ("style.css", "app.js", "logo.png", "favicon.ico"):
                return self._file(HERE / parts[1])
            if parts == ["favicon.ico"]:                          # demandé d'office par les navigateurs
                return self._file(HERE / "favicon.ico")
            if parts[0] == "api":
                if parts[1:] == ["projets"]:
                    PROJETS.mkdir(exist_ok=True)
                    return self._json(sorted(d.name for d in PROJETS.iterdir() if (d / "projet.json").exists()))
                if parts[1:] == ["job"]:
                    return self._json(JOB.state())
                if parts[1:] == ["version"]:
                    return self._json({"perime": code_perime()})
                if parts[1:] == ["claude"]:
                    from .ai import find_claude
                    return self._json({"chemin": find_claude()})
                if len(parts) == 3 and parts[1] == "projet":
                    _project(parts[2])
                    return self._json(status(parts[2]))
            if parts[0] == "fichier" and len(parts) >= 3:
                p = _project(parts[1]).resolve()
                f = (p / "/".join(parts[2:])).resolve()
                if p not in f.parents:
                    return self._err("Accès refusé", 403)
                return self._file(f)
            self._err("Introuvable", 404)
        except (ValueError, FileNotFoundError) as e:
            self._err(e, 404)

    def do_POST(self):
        if self._etranger():
            return
        parts, q = self._parts()
        try:
            if parts == ["api", "projets"]:
                nom = json.loads(self._body() or b"{}").get("nom", "").strip()
                if not NOM_RE.match(nom):
                    raise ValueError("Nom invalide : lettres, chiffres, - et _ seulement (pas d'espaces)")
                if (PROJETS / nom).exists():
                    raise ValueError("Ce projet existe déjà")
                r = subprocess.run([sys.executable, "-m", "clip", "new", nom], cwd=ROOT, capture_output=True,
                                   text=True, env={**os.environ, "PYTHONUTF8": "1"})
                if r.returncode:
                    raise ValueError(r.stdout + r.stderr)
                return self._json({"ok": True})
            if len(parts) < 4 or parts[:2] != ["api", "projet"]:
                return self._err("Introuvable", 404)
            nom, action = parts[2], parts[3]
            p = _project(nom)
            if action == "run":
                data = json.loads(self._body() or b"{}")
                cmd, args = data.get("cmd"), data.get("args") or []
                if cmd not in COMMANDS:
                    raise ValueError(f"Commande non autorisée : {cmd}")
                i = 0
                while i < len(args):
                    a = args[i]
                    if a not in COMMANDS[cmd]:
                        raise ValueError(f"Argument non autorisé : {a}")
                    if a in ARG_VALUES:                       # l'option attend une valeur
                        if i + 1 >= len(args) or not ARG_VALUES[a].match(str(args[i + 1])):
                            raise ValueError(f"Valeur invalide pour {a}")
                        i += 1
                    i += 1
                JOB.start(nom, cmd, args)
                return self._json({"ok": True})
            if action == "stop":
                if JOB.running():
                    JOB.proc.kill()
                return self._json({"ok": True})
            if action == "config":
                cfg = _cfg(p)
                cfg.update(json.loads(self._body() or b"{}"))
                _save_cfg(p, cfg)
                return self._json({"ok": True})
            if action == "descriptions":
                txt = self._body().decode("utf-8-sig").strip()
                m = re.search(r"\{.*\}", txt, re.S)            # tolère ```json … ``` autour
                data = json.loads(m.group(0) if m else txt)
                if not isinstance(data, dict):
                    raise ValueError("Le JSON doit être un objet {\"p1_c1\": \"…\"}")
                (p / "build").mkdir(exist_ok=True)
                f = p / "build" / "descriptions.json"
                old = json.loads(_read(f, "{}"))
                old.update(data)
                f.write_text(json.dumps(old, indent=1, ensure_ascii=False), encoding="utf-8")
                return self._json({"ok": True, "n": len([k for k in data if not k.startswith("_")])})
            if action == "upload":
                return self._upload(p, q)
            if action == "restaurer":
                name = q.get("f", "")
                f = p / "build" / "historique" / name
                if not re.match(r"^projet_\d{8}_\d{6}\.json$", name) or not f.is_file():
                    raise ValueError("Version introuvable")
                from .cli import _save
                _save(p, json.loads(f.read_text(encoding="utf-8-sig")), garder=True)
                return self._json({"ok": True})
            if action == "retirer-clip":
                pid = q.get("id", "")
                if not re.match(r"^(p\d+_c\d+|solo\d+)$", pid, re.I):
                    raise ValueError("Identifiant invalide")
                for f in (p / "videos").glob(f"{pid.lower()}.*"):
                    f.unlink()
                return self._json({"ok": True})
            if action in ("reveler", "supprimer-video"):
                name = Path(q.get("nom", "")).name              # nom seul : pas de chemin
                f = (p / "build" / name).resolve()
                if not re.match(r"^[\w\-. ]+\.mp4$", name) or f.parent != (p / "build").resolve() or not f.is_file():
                    raise ValueError("Vidéo introuvable")
                if action == "reveler":                          # explorateur avec le fichier sélectionné
                    _ouvrir(f, montrer=True)
                else:
                    if JOB.running() and JOB.nom == p.name:
                        raise ValueError("Un rendu est en cours sur ce projet : attends la fin")
                    try:
                        f.unlink()
                    except PermissionError:
                        raise ValueError("La vidéo est encore ouverte (lecteur vidéo ?) : ferme-la puis réessaie")
                return self._json({"ok": True})
            if action == "ouvrir":
                f = (p / q.get("chemin", "")).resolve()
                if f != p.resolve() and p.resolve() not in f.parents:
                    raise ValueError("Accès refusé")
                _ouvrir(f)                                # explorateur / lecteur vidéo du système
                return self._json({"ok": True})
            self._err("Action inconnue", 404)
        except (ValueError, FileNotFoundError, RuntimeError, json.JSONDecodeError, OSError) as e:
            self._err(e)

    def _upload(self, p, q):
        kind, name = q.get("type"), Path(q.get("nom", "")).name
        data, ext, cfg = self._body(), Path(name).suffix.lower(), _cfg(p)
        pid = q.get("id", "")
        if kind == "audio" and ext in AUDIO_EXT:
            (p / name).write_bytes(data)
            cfg["audio"] = name
        elif kind == "paroles" and ext == ".txt":
            (p / name).write_bytes(data)
            cfg["paroles"] = name
        elif kind == "planche" and ext in IMG_EXT and re.match(r"^p\d+$", pid, re.I):
            d = p / cfg.get("planches", "planches")
            d.mkdir(exist_ok=True)
            for old in d.glob(f"{pid.upper()}.*"):
                old.unlink()
            (d / f"{pid.upper()}{ext}").write_bytes(data)
        elif kind == "solo" and ext in IMG_EXT:
            d = p / cfg.get("solos", "solos")
            d.mkdir(exist_ok=True)
            if re.match(r"^solo\d+$", pid, re.I):           # emplacement précis (solo1, solo2…) : remplace
                for old in d.glob(f"{pid.lower()}.*"):
                    old.unlink()
                (d / f"{pid.lower()}{ext}").write_bytes(data)
            else:
                (d / (name if Path(name).stem.lower().startswith("solo") else f"solo_{name}")).write_bytes(data)
            cfg["solos_list"] = []                         # re-détection automatique
        elif kind == "video" and ext in (".mp4", ".mov", ".webm", ".m4v") and re.match(r"^(p\d+_c\d+|solo\d+)$", pid, re.I):
            d = p / "videos"
            d.mkdir(exist_ok=True)
            for old in d.glob(f"{pid.lower()}.*"):
                old.unlink()
            (d / f"{pid.lower()}{ext}").write_bytes(data)
        elif kind == "logo" and ext in (".png", ".webp", ".jpg", ".jpeg"):
            for old in p.glob("logo.*"):
                old.unlink()
            (p / f"logo{ext}").write_bytes(data)
            cfg["logo"] = f"logo{ext}"
        elif kind == "retouche" and ext in IMG_EXT and re.match(r"^p\d+_c\d+$", pid, re.I):
            d = p / "retouches"
            d.mkdir(exist_ok=True)
            for old in d.glob(f"{pid.lower()}.*"):
                old.unlink()
            (d / f"{pid.lower()}{ext}").write_bytes(data)
        else:
            raise ValueError("Type de fichier non accepté ici")
        _save_cfg(p, cfg)
        return self._json({"ok": True})


class Server(ThreadingHTTPServer):
    # sous Windows, SO_REUSEADDR laisse ouvrir un 2e serveur sur un port déjà pris : on l'interdit
    allow_reuse_address = False
    daemon_threads = True


def serve(open_browser=True):
    import urllib.request
    srv = None
    for port in range(PORT, PORT + 10):               # port occupé par autre chose : on essaie le suivant
        url = f"http://127.0.0.1:{port}/"
        try:
            srv = Server(("127.0.0.1", port), Handler)
            break
        except OSError:
            try:                                      # déjà lancé : on ouvre juste la page
                with urllib.request.urlopen(url + "api/version", timeout=1.5) as r:
                    perime = json.loads(r.read()).get("perime")
            except Exception:
                continue
            print(f"Clip Studio tourne déjà : {url}")
            if perime:
                print("⚠ Il tourne avec une ancienne version du code : ferme son autre fenêtre noire, puis relance.")
            if open_browser:
                webbrowser.open(url)
            return
    if srv is None:
        print(f"Aucun port libre entre {PORT} et {PORT + 9}.")
        return
    print(f"Clip Studio : {url}\nGarder cette fenêtre ouverte ; la fermer arrête Clip Studio.")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
