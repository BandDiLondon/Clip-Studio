"""Paroles : lecture du .txt, alignement forcé mot-à-mot (stable-ts)."""
import json
import re

SECTION_RE = re.compile(r"^\s*\[(.+?)\]\s*$")


def read_lyrics(path):
    """Retourne [(section, vers)] en ignorant les lignes vides.
    Sans aucun en-tête [Section] : chaque bloc séparé par une ligne vide devient une section ;
    un bloc répété à l'identique est un refrain (« Chorus »), les autres des couplets."""
    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
    if any(SECTION_RE.match(r) for r in raw_lines):
        section, lines = None, []
        for raw in raw_lines:
            m = SECTION_RE.match(raw)
            if m:
                section = m.group(1)
            elif raw.strip():
                lines.append((section, raw.strip()))
        return lines
    blocks, cur = [], []
    for raw in raw_lines + [""]:
        if raw.strip():
            cur.append(raw.strip())
        elif cur:
            blocks.append(cur)
            cur = []
    keys = [" / ".join(b).lower() for b in blocks]
    lines, verse = [], 0
    for b, k in zip(blocks, keys):
        if keys.count(k) > 1:
            name = "Chorus"
        else:
            verse += 1
            name = f"Verse {verse}"
        lines += [(name, t) for t in b]
    return lines


def _chars(s):
    return re.sub(r"\s+", "", s)


def _map_words(lines, aligned):
    """Associe les mots alignés (texte, début, fin) aux tokens affichés de chaque vers,
    par position de caractère : robuste aux découpages différents de stable-ts."""
    # position de chaque caractère non-blanc → (vers, token)
    owner = []
    for li, (_, text) in enumerate(lines):
        for ti, tok in enumerate(text.split()):
            owner += [(li, ti)] * len(tok)
    times = {}
    pos = 0
    for w, s, e in aligned:
        n = len(_chars(w))
        for k in range(pos, min(pos + n, len(owner))):
            li, ti = owner[k]
            t0, t1 = times.get((li, ti), (s, e))
            times[(li, ti)] = (min(t0, s), max(t1, e))
        pos += n
    if pos != len(owner):
        print(f"  ⚠ {len(owner)} caractères attendus, {pos} alignés")
    return times


GAP = 2.5        # écart (s) au-delà duquel un mot est séparé du groupe de son vers
STEP = 0.35      # durée assignée à un mot recollé
MAX_WORD = 1.2   # durée max d'un mot


def repair(segments, debut_chant=0):
    """Recolle les mots isolés de l'autre côté d'un solo au groupe principal du vers,
    borne la durée des mots et recalcule start/end. Retourne le nombre de mots déplacés.
    debut_chant : la section qui commence à ce moment-là est fixée par l'auteur, on n'y touche pas."""
    moved = 0
    for seg in segments:
        ws = seg["words"]
        if not ws or any(w["s"] is None for w in ws):
            continue
        # groupes de mots contigus (écart ≤ GAP)
        groups, cur = [], [0]
        for i in range(1, len(ws)):
            if ws[i]["s"] - ws[i - 1]["e"] > GAP:
                groups.append(cur)
                cur = []
            cur.append(i)
        groups.append(cur)
        if len(groups) > 1:
            main = max(groups, key=len)
            a, b = main[0], main[-1]
            for i in range(a - 1, -1, -1):
                ws[i]["s"] = round(ws[i + 1]["s"] - STEP, 3)
                ws[i]["e"] = ws[i + 1]["s"]
                moved += 1
            for i in range(b + 1, len(ws)):
                ws[i]["s"] = round(min(ws[i - 1]["e"], ws[i - 1]["s"] + STEP), 3)
                ws[i]["e"] = round(ws[i]["s"] + STEP, 3)
                moved += 1
        for i, w in enumerate(ws):
            e = min(w["e"], w["s"] + MAX_WORD)
            if i + 1 < len(ws) and ws[i + 1]["s"] > w["s"]:
                e = min(e, ws[i + 1]["s"])
            w["e"] = round(max(e, w["s"] + 0.05), 3)
        seg["start"], seg["end"] = ws[0]["s"], ws[-1]["e"]
    moved += _regroup(segments, debut_chant)
    return moved


SECTION_GAP = 12.0   # deux vers d'une même section ne sont jamais séparés de plus que ça


def _regroup(segments, debut_chant=0):
    """Un vers isolé loin du suivant de la même section (typiquement le 1er vers aspiré dans
    l'intro) est recollé juste avant ce suivant, avec une durée de vers médiane."""
    segs = [s for s in segments if s["start"] is not None and all(w["s"] is not None for w in s["words"])]
    if len(segs) < 3:
        return 0
    med = sorted(s["end"] - s["start"] for s in segs)[len(segs) // 2]
    # 1re section calée sur le début du chant indiqué : elle ne bouge pas
    fixe = segs[0]["section"] if debut_chant > 0 and abs(segs[0]["start"] - debut_chant) < 1.0 else None
    moved = 0
    # à rebours : un bloc de plusieurs vers perdus dans l'intro se recale en cascade
    for idx in range(len(segs) - 2, -1, -1):
        cur, nxt = segs[idx], segs[idx + 1]
        # sans en-tête [Section], on ne sait pas si deux vers vont ensemble : ne rien déplacer
        if not cur["section"] or cur["section"] != nxt["section"] or nxt["start"] - cur["end"] <= SECTION_GAP:
            continue
        if fixe and cur["section"] == fixe:
            continue
        old_s = cur["start"]
        # rythme des mots : celui du même vers chanté ailleurs (même mélodie), sinon longueur des mots
        twin = next((s for s in segs if s is not cur and s["text"].lower() == cur["text"].lower()
                     and len({w["s"] for w in s["words"]}) == len(s["words"])), None)
        if twin:
            dur = twin["end"] - twin["start"]
            rel = [((w["s"] - twin["start"]) / dur, (w["e"] - twin["start"]) / dur) for w in twin["words"]]
        else:
            dur = med
            n = [len(w["w"]) + 1 for w in cur["words"]]
            acc = [sum(n[:i]) / sum(n) for i in range(len(n) + 1)]
            rel = list(zip(acc[:-1], acc[1:]))
        new_s = nxt["start"] - dur
        for w, (a, b) in zip(cur["words"], rel):
            w["s"], w["e"] = round(new_s + a * dur, 3), round(new_s + b * dur, 3)
        cur["start"], cur["end"] = cur["words"][0]["s"], cur["words"][-1]["e"]
        print(f"  vers recalé : « {cur['text']} » {old_s:.2f}s → {cur['start']:.2f}s")
        moved += len(cur["words"])
    return moved


def _rhythm(seg, segs):
    """Rythme relatif des mots d'un vers : celui du même vers chanté ailleurs s'il est bien calé,
    sinon proportionnel à la longueur des mots. Retourne [(début, fin)] entre 0 et 1."""
    twin = next((s for s in segs if s is not seg and s["text"].lower() == seg["text"].lower()
                 and s["start"] is not None and len({w["s"] for w in s["words"]}) == len(s["words"])), None)
    if twin:
        d = max(twin["end"] - twin["start"], 0.1)
        return [((w["s"] - twin["start"]) / d, (w["e"] - twin["start"]) / d) for w in twin["words"]]
    n = [len(w["w"]) + 1 for w in seg["words"]]
    acc = [sum(n[:i]) / sum(n) for i in range(len(n) + 1)]
    return list(zip(acc[:-1], acc[1:]))


def force_start(segments, t0):
    """« Le chant commence à t0 » : les vers placés avant t0 (ratés de l'alignement, aspirés dans l'intro)
    sont recalés entre t0 et le premier vers bien placé, au prorata de leur longueur."""
    segs = [s for s in segments if s["start"] is not None]
    early = [s for s in segs if s["start"] < t0 - 0.3]
    later = [s for s in segs if s["start"] >= t0 - 0.3]
    if not early:
        # 1re section placée trop tard (tassée contre la suivante) : on l'avance d'un bloc jusqu'à t0
        if not segs or segs[0]["start"] <= t0 + 1.0:
            return 0
        first = [s for s in segs if s["section"] == segs[0]["section"]] if segs[0]["section"] else segs[:1]
        delta = t0 - first[0]["start"]
        for s in first:
            for w in s["words"]:
                if w["s"] is not None:
                    w["s"], w["e"] = round(w["s"] + delta, 3), round(w["e"] + delta, 3)
            s["start"], s["end"] = round(s["start"] + delta, 3), round(s["end"] + delta, 3)
            print(f"  vers recalé (début du chant {t0} s) : « {s['text']} » → {s['start']:.2f}s")
        return sum(len(s["words"]) for s in first)
    stop = later[0]["start"] if later else t0 + 3.0 * len(early)
    if stop - t0 < 0.5 * len(early):                       # pas la place : 2,5 s par vers
        stop = t0 + 2.5 * len(early)
    # durée naturelle : celle du même vers chanté ailleurs, sinon débit médian des vers bien placés
    rates = sorted((s["end"] - s["start"]) / max(1, len(s["text"])) for s in later if s["end"] > s["start"])
    rate = rates[len(rates) // 2] if rates else 0.12
    durs = []
    for s in early:
        twin = next((o for o in later if o["text"].lower() == s["text"].lower() and o["end"] > o["start"]), None)
        durs.append(twin["end"] - twin["start"] if twin else rate * max(1, len(s["text"])))
    scale = min(1.0, (stop - t0) / sum(durs))              # jamais étirés, tassés seulement s'il le faut
    pos = t0
    for s, dur in zip(early, durs):
        dur *= scale
        for w, (a, b) in zip(s["words"], _rhythm(s, segs)):
            w["s"], w["e"] = round(pos + a * dur, 3), round(pos + b * dur, 3)
        s["start"], s["end"] = s["words"][0]["s"], s["words"][-1]["e"]
        print(f"  vers recalé (début du chant {t0} s) : « {s['text']} » → {s['start']:.2f}s")
        pos += dur
    moved = sum(len(s["words"]) for s in early)
    # vers suivants de la même section restés loin derrière : ils suivent (sinon la réparation
    # recollerait tout le couplet contre eux)
    prev = early[-1]
    for s in later:
        if not s["section"] or s["section"] != prev["section"] or s["start"] - prev["end"] <= SECTION_GAP:
            break
        delta = prev["end"] - s["start"]
        for w in s["words"]:
            if w["s"] is not None:
                w["s"], w["e"] = round(w["s"] + delta, 3), round(w["e"] + delta, 3)
        s["start"], s["end"] = round(s["start"] + delta, 3), round(s["end"] + delta, 3)
        print(f"  vers recalé (début du chant {t0} s) : « {s['text']} » → {s['start']:.2f}s")
        moved += len(s["words"])
        prev = s
    return moved


def align(audio_path, lyrics_path, out_path, model_name="medium", language="fr", debut_chant=0):
    import stable_whisper
    lines = read_lyrics(lyrics_path)
    text = "\n".join(t for _, t in lines)
    from pathlib import Path
    cache = Path.home() / ".cache" / "whisper" / f"{model_name}.pt"
    print(f"  {len(lines)} vers, modèle whisper « {model_name} »"
          + ("" if cache.exists() else " (1er usage : téléchargement unique du modèle, ~1,5 Go pour medium)"))
    model = stable_whisper.load_model(model_name, device="cpu")
    result = model.align(str(audio_path), text, language=language)
    aligned = [(w.word, float(w.start), float(w.end), float(getattr(w, "probability", 1.0) or 0))
               for seg in result.segments for w in seg.words]
    times = _map_words(lines, [(w, s, e) for w, s, e, _ in aligned])

    segments = []
    for li, (section, text) in enumerate(lines):
        words = []
        for ti, tok in enumerate(text.split()):
            s, e = times.get((li, ti), (None, None))
            words.append({"w": tok, "s": round(s, 3) if s is not None else None,
                          "e": round(e, 3) if e is not None else None})
        ts = [w["s"] for w in words if w["s"] is not None]
        te = [w["e"] for w in words if w["e"] is not None]
        segments.append({"section": section, "text": text,
                         "start": min(ts) if ts else None, "end": max(te) if te else None,
                         "words": words})
    if debut_chant > 0:                          # avant la réparation automatique
        force_start(segments, debut_chant)
    print(f"  réparation : {repair(segments, debut_chant)} mot(s) recollé(s)")
    out_path.write_text(json.dumps({"segments": segments}, indent=1, ensure_ascii=False), encoding="utf-8")

    doubtful = [(w, s, p) for w, s, e, p in aligned if p < 0.3 or e - s < 0.05]
    print(f"  → {out_path.name} : {len(segments)} vers, {len(aligned)} mots, {len(doubtful)} douteux")
    for w, s, p in doubtful[:20]:
        print(f"     {s:7.2f}s  {w.strip():20s} p={p:.2f}")
    return segments
