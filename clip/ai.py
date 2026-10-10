"""Rédaction par Claude via Claude Code (abonnement Claude Pro / Max de l'utilisateur, pas l'API).
Claude Code est appelé en mode non interactif (`claude -p`) depuis un dossier temporaire neutre,
pour qu'il ne charge pas le contexte du projet (AGENTS.md…) et ne consomme que la demande."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .i18n import tr


def _version_key(p):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(p))
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def find_claude():
    """Chemin de Claude Code : PATH, installation autonome, npm, puis extension VS Code (la plus récente).
    CLIP_SANS_CLAUDE=1 : fait comme s'il était absent (essais automatiques, sans consommer l'abonnement)."""
    if os.environ.get("CLIP_SANS_CLAUDE"):
        return None
    found = shutil.which("claude")
    if found:
        return found
    home = Path(os.environ.get("USERPROFILE", Path.home()))
    for c in (home / ".local" / "bin" / "claude.exe", home / ".local" / "bin" / "claude",
              home / ".claude" / "local" / "claude",
              Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"):
        if c.is_file():
            return str(c)
    exe = "claude.exe" if os.name == "nt" else "claude"
    for ext_dir in (home / ".vscode" / "extensions", home / ".vscode-server" / "extensions",
                    home / ".cursor" / "extensions"):
        bins = list(ext_dir.glob(f"anthropic.claude-code-*/resources/native-binary/{exe}"))
        if bins:
            return str(max(bins, key=_version_key))
    return None


# Appel « nu » : nos demandes sont du texte seul. Sans outils, connecteurs MCP, réglages ni consignes de
# Claude Code, le contexte envoyé passe de ~34 500 à ~700 tokens par appel (mesuré), réponse identique.
# (--bare n'est pas utilisable : il ignore la connexion par abonnement.)
OPTIONS = ["-p", "--output-format", "json", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
           "--disable-slash-commands", "--no-session-persistence",
           "--system-prompt", "Tu es un assistant de rédaction. Réponds exactement à la demande."]


class ClaudeError(Exception):
    pass


def ask(prompt, timeout=600):
    """Envoie une demande à Claude Code et retourne le texte de la réponse."""
    exe = find_claude()
    if not exe:
        raise ClaudeError(tr("Claude Code introuvable. Installe l'extension Claude Code de VS Code "
                             "ou Claude Code, puis connecte-toi avec ton compte Claude.",
                             "Claude Code not found. Install the Claude Code extension for VS Code "
                             "or Claude Code, then sign in with your Claude account."))
    with tempfile.TemporaryDirectory(prefix="clip_claude_") as tmp:
        try:
            r = subprocess.run([exe, *OPTIONS], input=prompt, cwd=tmp,
                               capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            raise ClaudeError(tr("Claude n'a pas répondu à temps (limite dépassée).",
                                 "Claude did not answer in time (time limit exceeded)."))
    out = (r.stdout or "").strip()
    try:
        data = json.loads(out[out.index("{"):]) if "{" in out else {}
    except (ValueError, json.JSONDecodeError):
        data = {}
    if not data:
        msg = (r.stderr or out or tr("réponse vide", "empty answer")).strip()[-400:]
        if "login" in msg.lower() or "auth" in msg.lower():
            msg += tr("\n→ Connecte Claude Code à ton compte (ouvre Claude Code une fois et connecte-toi).",
                      "\n→ Sign Claude Code in to your account (open Claude Code once and sign in).")
        raise ClaudeError(tr(f"Claude Code a échoué : {msg}", f"Claude Code failed: {msg}"))
    if data.get("is_error"):
        raise ClaudeError(f"Claude : {data.get('result') or data.get('subtype') or tr('erreur', 'error')}")
    return data.get("result", "")


def ask_json(prompt, timeout=600):
    """Comme ask(), mais extrait l'objet JSON de la réponse (tolère ```json … ``` autour)."""
    txt = ask(prompt, timeout)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ClaudeError(tr("La réponse de Claude ne contient pas de JSON :\n", "Claude's answer contains no JSON:\n") + txt[:400])
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ClaudeError(tr(f"JSON invalide dans la réponse de Claude : {e}", f"Invalid JSON in Claude's answer: {e}"))
