"""Paroles : lecture du .txt, alignement forcé mot-à-mot (stable-ts)."""
import json
import re

from . import ecrire
from .i18n import tr

SECTION_RE = re.compile(r"^\s*\[(.+?)\]\s*$")


def _bis(name, lines):
    """Nom de la section qui commence : « (bis) » si la précédente porte déjà ce nom."""
    return f"{name} (bis)" if lines and lines[-1][0] == name else name


def read_lyrics(path):
    """Retourne [(section, vers)] en ignorant les lignes vides.
    Sans aucun en-tête [Section] : chaque bloc séparé par une ligne vide devient une section ;
    un bloc répété à l'identique est un refrain (« Chorus »), les autres des couplets.
    Deux sections de même nom qui se suivent (refrain chanté deux fois, souvent séparé par un solo)
    sont distinguées (« Chorus (bis) ») : sinon elles forment un seul bloc et l'alignement les tasse."""
    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
    if any(SECTION_RE.match(r) for r in raw_lines):
        section, lines = None, []
        for raw in raw_lines:
            m = SECTION_RE.match(raw)
            if m:
                section = _bis(m.group(1), lines)
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
        lines += [(_bis(name, lines), t) for t in b]
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
        print(tr(f"  ⚠ {len(owner)} caractères attendus, {pos} alignés", f"  ⚠ {len(owner)} characters expected, {pos} aligned"))
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
        print(tr(f"  vers recalé : « {cur['text']} » {old_s:.2f}s → {cur['start']:.2f}s",
                 f"  line realigned: “{cur['text']}” {old_s:.2f}s → {cur['start']:.2f}s"))
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
            print(tr(f"  vers recalé (début du chant {t0} s) : « {s['text']} » → {s['start']:.2f}s",
                     f"  line realigned (singing start {t0} s): “{s['text']}” → {s['start']:.2f}s"))
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
        print(tr(f"  vers recalé (début du chant {t0} s) : « {s['text']} » → {s['start']:.2f}s",
                 f"  line realigned (singing start {t0} s): “{s['text']}” → {s['start']:.2f}s"))
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
        print(tr(f"  vers recalé (début du chant {t0} s) : « {s['text']} » → {s['start']:.2f}s",
                 f"  line realigned (singing start {t0} s): “{s['text']}” → {s['start']:.2f}s"))
        moved += len(s["words"])
        prev = s
    return moved


SHORT = 0.06        # mot plus court que ça : écrasé par l'alignement
SQUASHED = 0.5      # part de mots écrasés au-delà de laquelle un vers est raté


def bad_lines(segments):
    """Indices des vers ratés par l'alignement global : non placés, ou dont la majorité des mots sont écrasés
    (durée quasi nulle, typiquement plusieurs vers tassés au même instant)."""
    bad = []
    for i, seg in enumerate(segments):
        ws = [w for w in seg["words"] if _norm(w["w"])]
        if not ws:
            continue
        if any(w["s"] is None for w in ws) or \
                sum(w["e"] - w["s"] < SHORT for w in ws) >= SQUASHED * len(ws):
            bad.append(i)
    return bad


def _norm(w):
    """Mot comparable : minuscules, sans accents ni ponctuation (« Ayoye, » → « ayoye »)."""
    import unicodedata
    w = unicodedata.normalize("NFKD", w.lower())
    return "".join(c for c in w if c.isalnum())


def blocks(lines):
    """Sections consécutives : [[indices des vers]]. Une étiquette répétée plus loin (refrain) ouvre un
    nouveau bloc; sans étiquette, chaque vers est son propre bloc."""
    out, prev = [], object()
    for i, (sec, _) in enumerate(lines):
        if sec is None or sec != prev:
            out.append([])
        out[-1].append(i)
        prev = sec
    return out


def match_windows(lines, heard, duration, debut_chant=0, margin=1.5):
    """Fenêtre (début, fin) de chaque bloc de vers, d'après une transcription libre `heard` [(mot, début, fin)].
    Les mots des paroles et ceux entendus sont appariés dans l'ordre (alignement de séquences, mots proches
    acceptés); un bloc sans mot reconnu prend l'espace libre entre ses voisins. Retourne [(début, fin)] par bloc."""
    from difflib import SequenceMatcher
    lw = [(li, _norm(tok)) for li, (_, text) in enumerate(lines) for tok in text.split() if _norm(tok)]
    hw = [(_norm(w), s, e) for w, s, e in heard if _norm(w)]
    n, m = len(lw), len(hw)
    gap = 0.4

    def sim(a, b):
        return 1.0 if a == b else SequenceMatcher(None, a, b).ratio()

    # programmation dynamique (Needleman-Wunsch) : +sim pour un appariement, −gap pour un mot sauté
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = -gap * i
    for j in range(1, m + 1):
        score[0][j] = -gap * j
    for i in range(1, n + 1):
        a = lw[i - 1][1]
        row, prev = score[i], score[i - 1]
        for j in range(1, m + 1):
            row[j] = max(prev[j - 1] + 2 * sim(a, hw[j - 1][0]) - 1, prev[j] - gap, row[j - 1] - gap)
    times = {}                                   # vers → [instants des mots reconnus]
    i, j = n, m
    while i > 0 and j > 0:
        s = sim(lw[i - 1][1], hw[j - 1][0])
        if score[i][j] == score[i - 1][j - 1] + 2 * s - 1:
            if s >= 0.6:
                times.setdefault(lw[i - 1][0], []).extend(hw[j - 1][1:])
            i, j = i - 1, j - 1
        elif score[i][j] == score[i - 1][j] - gap:
            i -= 1
        else:
            j -= 1
    found = []
    for b in blocks(lines):
        ts = [t for li in b for t in times.get(li, [])]
        found.append((min(ts), max(ts)) if ts else None)
    start0 = max(0.0, debut_chant - 0.5) if debut_chant > 0 else 0.0
    wins = []
    for k, f in enumerate(found):
        prev_end = next((x[1] for x in reversed(found[:k]) if x), start0)
        next_start = next((x[0] for x in found[k + 1:] if x), duration)
        if f:
            a, b = max(prev_end + 0.05, f[0] - margin, start0), min(next_start - 0.05, f[1] + margin, duration)
        else:
            a, b = prev_end + 0.05, next_start - 0.05
        wins.append((round(a, 3), round(max(b, a + 0.5), 3)))
    return wins


def _segments(lines, times):
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
    return segments


def _align_by_blocks(model, audio, lines, windows, language):
    """Aligne chaque bloc de vers seul, dans sa fenêtre de l'audio (16 kHz; None : bloc ignoré).
    → [(mot, début, fin, probabilité)]
    et le dictionnaire des temps par (vers, token)."""
    times, aligned = {}, []
    for b, w in zip(blocks(lines), windows):
        if w is None:                            # bloc laissé tel quel
            continue
        a, e = w
        sub = [lines[i] for i in b]
        r = model.align(audio[int(a * 16000):int(e * 16000)], "\n".join(t for _, t in sub), language=language)
        al = [(w.word, float(w.start) + a, float(w.end) + a, float(getattr(w, "probability", 1.0) or 0))
              for seg in r.segments for w in seg.words]
        aligned += al
        for (li, ti), t in _map_words(sub, [(w, s, en) for w, s, en, _ in al]).items():
            times[(b[li], ti)] = t
    return aligned, times


def local_windows(lines, segments, duration):
    """Fenêtre des blocs qui contiennent des vers ratés, bornée par les vers bien calés voisins (None pour
    les autres blocs) : le calage global est souvent bon jusqu'à un solo, puis tasse tout ce qui suit."""
    bad = set(bad_lines(segments))
    good = [i for i, s in enumerate(segments) if i not in bad and s["start"] is not None]
    wins = []
    for b in blocks(lines):
        a = max((segments[i]["end"] for i in good if i < b[0]), default=0.0)
        e = min((segments[i]["start"] for i in good if i > b[-1]), default=duration)
        wins.append((round(a, 3), round(e, 3)) if bad & set(b) and e - a > 0.5 * len(b) else None)
    return wins


def align(audio_path, lyrics_path, out_path, model_name="medium", language="fr", debut_chant=0):
    import stable_whisper
    lines = read_lyrics(lyrics_path)
    text = "\n".join(t for _, t in lines)
    from pathlib import Path
    cache = Path.home() / ".cache" / "whisper" / f"{model_name}.pt"
    print(tr(f"  {len(lines)} vers, modèle whisper « {model_name} », langue « {language} »",
             f"  {len(lines)} lines, whisper model “{model_name}”, language “{language}”")
          + ("" if cache.exists() else tr(" (1er usage : téléchargement unique du modèle, ~1,5 Go pour medium)",
                                          " (first use: one-time model download, ~1.5 GB for medium)")))
    model = stable_whisper.load_model(model_name, device="cpu")
    result = model.align(str(audio_path), text, language=language)
    aligned = [(w.word, float(w.start), float(w.end), float(getattr(w, "probability", 1.0) or 0))
               for seg in result.segments for w in seg.words]
    segments = _segments(lines, _map_words(lines, [(w, s, e) for w, s, e, _ in aligned]))

    bad = bad_lines(segments)
    audio = stable_whisper.audio.load_audio(str(audio_path)) if bad and len(blocks(lines)) > 1 else None
    windows = local_windows(lines, segments, len(audio) / 16000) if audio is not None else []
    if any(windows):
        # sections ratées recalées seules entre les vers bien calés voisins (ex. dernier refrain après un solo)
        aligned2, times2 = _align_by_blocks(model, audio, lines, windows, language)
        seg2 = _segments(lines, times2)
        for b, w in zip(blocks(lines), windows):
            if w is None:
                for i in b:
                    seg2[i] = segments[i]
        if len(bad_lines(seg2)) < len(bad):
            print(tr(f"  sections ratées recalées seules : {len(bad_lines(seg2))} vers mal calé(s) au lieu de {len(bad)}",
                     f"  failed sections realigned alone: {len(bad_lines(seg2))} badly aligned line(s) instead of {len(bad)}"))
            segments, aligned, bad = seg2, aligned + aligned2, bad_lines(seg2)
    if bad and audio is not None:
        # alignement global raté (longue intro, pauses instrumentales) : on écoute la chanson, on repère
        # chaque section, puis on l'aligne seule dans sa fenêtre
        print(tr(f"  {len(bad)} vers mal calés : écoute de la chanson pour caler section par section…",
                 f"  {len(bad)} badly aligned lines: listening to the song to align section by section…"))
        heard = [(w.word, float(w.start), float(w.end))
                 for seg in model.transcribe(audio, language=language, verbose=None).segments for w in seg.words]
        windows = match_windows(lines, heard, len(audio) / 16000, debut_chant)
        aligned2, times2 = _align_by_blocks(model, audio, lines, windows, language)
        seg2 = _segments(lines, times2)
        if len(bad_lines(seg2)) < len(bad):
            segments, aligned = seg2, aligned2
            print(tr(f"  calage par sections : {len(bad_lines(seg2))} vers mal calé(s) au lieu de {len(bad)}",
                     f"  section alignment: {len(bad_lines(seg2))} badly aligned line(s) instead of {len(bad)}"))
        else:
            print(tr("  calage par sections pas meilleur : calage d'origine conservé",
                     "  section alignment not better: original alignment kept"))
    if debut_chant > 0:                          # avant la réparation automatique
        force_start(segments, debut_chant)
    n = repair(segments, debut_chant)
    print(tr(f"  réparation : {n} mot(s) recollé(s)", f"  repair: {n} word(s) re-attached"))
    ecrire(out_path, json.dumps({"segments": segments}, indent=1, ensure_ascii=False))

    doubtful = [(w, s, p) for w, s, e, p in aligned if p < 0.3 or e - s < 0.05]
    print(tr(f"  → {out_path.name} : {len(segments)} vers, {len(aligned)} mots, {len(doubtful)} douteux",
             f"  → {out_path.name}: {len(segments)} lines, {len(aligned)} words, {len(doubtful)} doubtful"))
    for w, s, p in doubtful[:20]:
        print(f"     {s:7.2f}s  {w.strip():20s} p={p:.2f}")
    return segments
