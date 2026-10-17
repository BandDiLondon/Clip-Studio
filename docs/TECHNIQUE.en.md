# Clip Studio technical documentation

[Français](TECHNIQUE.md) | **English**

For anyone who wants to understand, change or troubleshoot the code (human or AI). Usage is described in
[GUIDE.en.md](GUIDE.en.md), the working rules for an AI in [AGENTS.md](../AGENTS.md).

The code (names of functions, variables, `projet.json` keys, command options) is written in French; the comments too.
This page explains it in English.

- [Architecture](#architecture)
- [Commands](#commands)
- [Project files](#project-files)
- [Storyboard and panels](#storyboard-and-panels)
- [projet.json settings](#projetjson-settings)
- [Processing](#processing)
- [Change detection](#change-detection)
- [Claude](#claude)
- [Languages](#languages)
- [Windows / Linux / macOS portability](#windows--linux--macos-portability)
- [Tests, screenshots, versions](#tests-screenshots-versions)

---

## Architecture

```
Clip Studio.bat / clip-studio.sh ──► python -m clip web ──► clip/web.py (local server 127.0.0.1)
                                                             │  page: clip/web/index.html + style.css + app.js
                                                             │  each action = a whitelisted command,
                                                             ▼  run as a subprocess (log streamed to the page)
                                                        python -m clip <command> <project>   (clip/cli.py)
```

| Module | Role |
|---|---|
| `clip/cli.py` | commands, `projet.json` template (`PROJET_TEMPLATE`), signatures (out of date?), history |
| `clip/web.py` | local server: project status (`status`), whitelist of commands and arguments, file uploads; refuses requests whose `Host` or `Origin` is not 127.0.0.1 / localhost (`_etranger`) |
| `clip/web/app.js` | interface: one render function per step (`V.<step>`), presets (`PRESETS`), options |
| `clip/i18n.py` | message language (`tr`), project language (`langue_projet`, `tp`) |
| `clip/audio.py` | tempo and beats |
| `clip/lyrics.py` | reading the lyrics, word-by-word alignment (stable-ts), repair |
| `clip/shots.py` | shotlist: 1 image per unique lyric line, packing into panels |
| `clip/prompts.py` | panel prompts |
| `clip/panels.py` | panel check, cutting, Real-ESRGAN, contact sheet |
| `clip/plan.py` | edit (timeline) synced to the beats |
| `clip/render.py` + `clip/effects.py` | frame-by-frame rendering, effects (pure functions), ASS karaoke, encoding |
| `clip/depth.py` | depth maps (parallax, background blur) |
| `clip/ai.py` + `clip/demandes.py` | calling Claude Code; request texts (descriptions, solos, videos) |
| `clip/evaluate.py` / `clip/publish.py` | storyboard evaluation / YouTube publishing (requests included) |
| `clip/ocr.py` | readable text in the cells (RapidOCR, all systems) |
| `tests/test_clip.py` | quick tests |
| `scripts/captures.py` | README screenshots |
| `scripts/essai_complet.py` | end-to-end test (synthetic song → preview video) |

---

## Commands
`python -m clip <command> <project> [options]` (`.venv\Scripts\python.exe` on Windows, `.venv/bin/python` on Linux and
macOS). Messages in English with `CLIP_LANG=en`.

| Command | Role | Output |
|---|---|---|
| `check` | checks the environment | — |
| `web` / `list` / `new` | Clip Studio / list / new project | `projets/<name>/` |
| `prepare [--force]` | beats + alignment + evaluation + prompts | `build/` |
| `beats` | beats and tempo | `build/beats.npy` |
| `align [--repair-only]` | stable-ts alignment + repair | `build/words.json` |
| `section --index N (--debut T \| --decaler D)` | fixes one section of the alignment: realigned alone from T, or shifted | `build/words.json` |
| `evaluate [--appliquer]` | storyboard evaluation (Claude) | `build/evaluation.json` |
| `prompts` | shotlist + panel prompts | `build/shotlist.json`, `prompts_planches.md` |
| `describe [--ids --consigne --tout]` | descriptions (Claude) | `build/descriptions.json` |
| `solos [--nombre --consigne]` | solo photo prompts (Claude) | `build/solos.json`, `prompts_solos.md` |
| `videos [--ids / --nombre, --consigne]` | video prompts, on request (Claude) | `build/videos.json`, `prompts_videos.md` |
| `verify` / `cut [--scale 1]` | check / cutting + upscaling + OCR | `cases/`, `build/planche_contact.jpg` |
| `plan [--force]` | edit | `projet.json` → `"timeline"` |
| `preview [--start --duration]` / `render [--out]` | preview / render only | `build/preview.mp4`, `build/<name>.mp4` |
| `build-preview` / `build [--force]` | check + cut + plan + preview / render | same |
| `publish [--consigne]` | YouTube publishing (Claude) | `build/publication.md` |

A command added to the interface must also be added to `COMMANDS` (and its arguments to `ARG_VALUES`) in
`clip/web.py`.

---

## Project files
```
projets/<name>/
  projet.json          settings + edit (timeline) + signatures
  <song>.mp3, <lyrics>.txt
  planches/P1.png…     generated images (grids)
  cases/p1_c1.png…     cut and upscaled cells (can be recomputed)
  retouches/p1_c2.png  replaces a cell (takes priority over cutting)
  solos/solo1.png…     panoramas of the instrumental parts
  videos/p1_c3.mp4…    replaces an image in the edit
  build/               words.json, beats.npy, shotlist.json, descriptions.json, prompts_*.md, evaluation.json,
                       videos.json, publication.md, texte_detecte.json, karaoke.ass, historique/, .mp4 renders
```
- `words.json`: `{"segments": [{"section", "text", "start", "end", "words": [{"w", "s", "e"}]}]}`.
- `timeline`: `[{"t": 20.13, "img": "p1_c1"}, {"t": 35.5, "travel": "solo4.png"}]`, each event lasts until the next.
- `build/descriptions.json`: `{"p1_c1": "Shot: … ; Subject: … ; Action: … ; Setting: … ; Lighting: …"}` (in French:
  `Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …`). The `"descriptions"` key of `projet.json` takes
  priority.

---

## Storyboard and panels
**Golden rule: panels exist to limit the number of image generations.** The exact number of images required by the
text is computed, then they are packed into the fewest panels.
- **1 image per unique lyric line** (normalized key: case, accents, punctuation), `"dedupe": false` to disable it.
  **Ambiance** images are added (`"ambiance": N`, total number); the free cells of the last panel also become ambiance.
- **Packing** (`shots._pack`): panels of 6 (2×3 grid, 32:27 image); the last one takes the smallest sufficient grid:
  4 → 2×2 (16:9), 2 → 1×2 (8:9), 1 → single image. Cells always 16:9. Adding ambiance does not change the panels that
  are already full.
- Ids `p1_c1 … pN_cK`: row 1 from left to right, then row 2…
- Parts without lyrics: solo photos and ambiance images **alternate** (`plan._Filler`), starting with a solo.

**Panel prompt** (`clip/prompts.py`), in the project language:
- Header "One single image made of EXACTLY N distinct cinematic photographs… NO caption…". Never the word
  "storyboard": a storyboard has captions, which the generator then writes.
- Each cell = "Photo i (position): …". The description is turned into a sentence **without the labels**
  Shot / Subject / Action… (French or English), which would end up written as captions (`prose`).
- Bottom quarter of each cell left free (lyrics area). Negative: text, caption, subtitle, numbers, readable sign,
  square or vertical cells, extra cell.
- **Never the lyrics in a prompt**: a text between quotes ends up written in the image.

---

## `projet.json` settings
All present in `PROJET_TEMPLATE` (`clip/cli.py`, with comments) and editable at step 6 (`app.js`). Kept from one render
to the next; all effects are off by default.
- **Framing**: `fit` (`cover` | `contain` on a blurred background), `cy` (0 = top, 1 = bottom). Per image:
  `"ajustements": {"p1_c2": {"cy": 0.1, "fit": "contain", "camera": "…", "particules": "…", "fumee": "…", "parallaxe": false}}`.
- **Rhythm**: `pulse`, `pulse_mesure`, `fondu`, `transition` (fondu | coupe | noir | flash | glissement | zoom),
  `duree_max_image`, `bpm_hint` (`"auto"` or forced BPM).
- **Camera**: `camera` (`zoom` | `auto` based on the "Shot"), `camera_intensite`, `parallaxe`.
- **Look**: `look` (aucun | cinema | nb | sepia | vhs | neon | froid), `grain`, `vignettage`, `luminosite`,
  `contraste`, `letterbox`, `harmonisation`, `variantes`, `look_sections`.
- **Atmosphere**: `particules` (auto | neige | poussiere | braises | pluie | confettis | bokeh | etincelles),
  `particules_densite`, `particules_sections`, `fumee` + `fumee_densite`, `flammes` + `flammes_hauteur` /
  `flammes_intensite`, `eclairs`, `rayons` + `rayons_intensite`, `flou_fond`, `brume_profondeur`.
  "auto" = based on the words of the description (French and English keywords, `render.py`).
- **Light and beat**: `fuites_lumiere`, `projecteurs`, `tremblement` + `tremblement_zone`, `rvb_beat`, `glitch` +
  `glitch_intensite`, `vieux_film`, `visualiseur` + `visualiseur_zone` / `_couleur` / `_hauteur`.
- **Karaoke**: `karaoke_mode` (mot | ligne | aucun), `font`, `karaoke_taille`, `karaoke_couleur`, `karaoke_texte`,
  `karaoke_position`, `karaoke_animation`, `karaoke_suivante`, `karaoke_majuscules`, `karaoke_decalage`, `bar_alpha`.
- **Texts**: `titre`, `artiste`, `generique`, `logo` + `logo_position`, `mention_ia_ecran` / `_texte` (empty = "Version
  IA" or "AI Version" depending on the project language) / `_position`, `origine` (`suno` | `images` | `complete` | `fan` |
  `fan_ia`, for the notice of the publishing; `fan*`: "no rights" statement, rights left to the artist),
  `publication` (options of step 8: `credits` {`paroles`, `musique`, `interpretation`, `clip`}, `clip_studio`, `liens`,
  `lien_officiel`, `ton`, `accroche`, `emojis`, `blocs`, `vignette`, `bandeau`, `bandeau_couleur`, `formats`; defaults:
  `REGLAGES` in `clip/publish.py`). Profiles shared by all projects: `projets/_profils_publication.json`
  (`GET` / `POST /api/profils`).
- **Lyrics**: `langue` (`fr` | `en`: Whisper alignment, texts written by Claude, prompts, publishing),
  `debut_chant` (s), `whisper` (`medium` | `small`, alignment model; `--model` of `prepare` / `align` wins and is
  saved), `intention`, `style`, `personnages`, `calage_fin_ok` (end of the last line for which the "End of song"
  alert was dismissed).
- **Format and sound**: `format` (16:9 | 4k | 9:16 | 1:1), `volume_normalise` (-14 LUFS), `debut` / `fin`, `fade_out`,
  `fps`, `encoder` (auto | amf | x264).
- **Managed by the code** (do not edit): `timeline`, `timeline_sig`, `beats_sig`, `paroles_sig`, `bpm_detecte`,
  `solos_list`.

---

## Processing
- **Beats** (`audio.py`): tempo estimated by tempogram, "octave family" brought between 72 and 144 BPM, then tracked by
  dynamic programming with a local period.
- **Alignment** (`lyrics.py`): stable-ts forced alignment (Whisper medium, CPU, ~4.7 GB of memory at most; small:
  ~1.7 GB) on the known lyrics, in the project language. **Section alignment** when lines are missed (`bad_lines`:
  half of the words or more last under 0.06 s, or are not placed): free transcription of the song (used only to locate
  the sections), matching of the lyrics words to the heard ones (`match_windows`, sequence alignment, close words
  accepted), then forced alignment of each section alone in its window; kept only if it misses fewer lines (about
  1.5 min more with medium). Repair: isolated words re-attached to their line, a line lost in the intro realigned
  before the next one of the same section (rhythm of the same line sung elsewhere), `force_start` for `debut_chant`.
  Check (`sections`, `fin_trop_tot` ≥ 30 s, shown in step 2) and fix of one section (`section_window` bounded by the
  next well-aligned lines, `realign_section`, `shift_section`). At render time, `sanitize` fixes impossible times (end
  before start) before writing the karaoke.
- **Cutting** (`panels.py`): gutters detected at the 90th percentile (strict threshold 12, then 30), 1.5% margin,
  Real-ESRGAN ×4 capped at 2560 px. Without Vulkan or without the binary: Lanczos upscaling with a warning (never
  blocking). Retouches ≥ 1400 px are not upscaled.
- **Text detection** (`ocr.py`): RapidOCR (PaddleOCR models through onnxruntime), image reduced to 1280 px, lines with
  confidence ≥ 0.5 and at least 3 letters; result in `build/texte_detecte.json`, never blocking. Comparison on
  165 cells: 14 real texts found (t-shirts, neons, signs) versus 3 for the built-in Windows OCR used before, 1 false
  alarm; Tesseract discarded (25 false alarms). onnxruntime telemetry turned off (`ORT_DISABLE_TELEMETRY=1` before the
  import: otherwise, on Linux, a device id in `~/.cache/Microsoft` and possible uploads). RapidOCR is installed with
  `--no-deps`: it requires `opencv-python`, which conflicts with `opencv-python-headless`.
- **Edit** (`plan.py`): 1 lyric line = its image, cuts synced to the beat, parts without lyrics filled.
- **Render** (`render.py`): PIL frames computed in parallel (processes started with "spawn" on every system, bounded
  queue, ≤ 12 processes depending on the free memory, ~450 MB each; numpy / OpenCV threads per process = cores ÷
  processes, rounded up, otherwise the processes get in each other's way and the render is 2× slower), sent as rawvideo
  to ffmpeg. Karaoke as burned-in ASS subtitles, AAC 192k audio muxed, `+faststart`. H.264 `yuv420p` 30 fps: h264_amf
  (AMD GPU) if available, otherwise libx264 `fast` CRF 20; bitrate capped at ~12 Mb/s. Preview 960×540 at 15 fps,
  `ultrafast`.
- Adding the audio to a video produced outside Clip Studio:
  `ffmpeg -i video.mp4 -i song.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart final.mp4`
- **Videos**: `videos/<id>.mp4` replaces the image `<id>`; frames extracted once into `build/video_frames/`, stretched if
  the shot is longer.

---

## Change detection
- **Beats / alignment**: `beats_sig` and `paroles_sig` signatures (mp3: name + size + date; lyrics: normalized content;
  forced tempo; singing start; Whisper model and project language, only when different from `medium` / `fr` so that
  older projects are not realigned). `perimes()` compares; `prepare`, `build` and `render` redo what is out of date.
  Without a signature (old project), the dates are compared.
- **Edit**: `timeline_sig` (mp3, `words.json`, `beats.npy`, shotlist, solos, intro / outro images). Recomputed before
  each render if different.
- **History**: `_save()` keeps the previous version of `projet.json` in `build/historique/` (30 max, at most one per
  minute; always on a restore). Writing is atomic (`clip.ecrire`: temporary file then replace).
- **Server**: `code_perime()` tells the page that the code changed since startup (orange banner).

---

## Claude
- `clip/ai.py` calls **Claude Code** (`claude -p`, JSON output) with the request on standard input, from a temporary
  folder: no project context is loaded. Lookup: PATH, `~/.local/bin`, npm, VS Code / Cursor extension.
  `CLIP_SANS_CLAUDE=1` acts as if it were absent (automatic tests).
- "Bare" call (`OPTIONS` in `ai.py`): without Claude Code's tools, MCP connectors, user settings or instructions
  (`--tools ""`, `--strict-mcp-config`, `--setting-sources ""`, one-line `--system-prompt`). The fixed overhead goes from
  ~34,500 to ~700 tokens per call (measured), same answer. `--bare` is excluded: it ignores the subscription login.
- **Called only on user action**, except the evaluation run by `prepare`. Never add an automatic call.
- Request texts: `clip/demandes.py`, `clip/evaluate.py`, `clip/publish.py`, in French and English (project language).
  Answers in strict JSON.
- Without Claude: `build/a_decrire.md` to paste into an assistant, JSON answer in `build/descriptions.json`.

---

## Languages
Two independent languages:
- **Message language** (interface, console, errors, command line): chosen in the interface (top right, stored in the
  browser; by default the browser language). The page sends it in the `X-Lang` header; the server sets it for the
  request (`i18n.fixer`) and passes it to the commands it starts (`CLIP_LANG`). On the command line and in the
  installers / launchers: `CLIP_LANG`, otherwise the system language.
- **Project language** (`projet.json` → `"langue"`): Whisper alignment, texts written by Claude, panel prompts, YouTube
  publishing, default AI notice. Chosen at step 1; a new project takes the interface language.

Writing rules:
- Python: `tr("français", "English")` for messages, `tp(cfg, "français", "English")` for what depends on the project
  (requests to Claude, prompts); long texts as `{"fr": …, "en": …}` dictionaries.
- `app.js`: `tr("français", "English")` everywhere, never a bare text.
- `.bat`: `call :msg "français" "English"` (outside any `if ( … )` block: parentheses in an `echo` inside a block break
  the batch file); no accents. `.sh`: `m "français" "English"`.
- Documentation: each page exists in French and in English (`README.md` / `README.en.md`, `docs/GUIDE.md` /
  `GUIDE.en.md`, `docs/TECHNIQUE.md` / `TECHNIQUE.en.md`, `CHANGELOG.md` / `CHANGELOG.en.md`). **Any change is made in
  both languages.**
- French: Quebec typography (no space before `;` `?` `!`, a space before `:`); informal "tu".

---

## Windows / Linux / macOS portability
The same code runs on the three systems (macOS: experimental, validated only by the GitHub action):
- opening a file: `_ouvrir()` (`web.py`);
- fonts: `_font()` (`panels.py`) and `FONT_CANDIDATES` (`cli.py`);
- Real-ESRGAN binary depending on `sys.platform` (universal Intel / Apple chips on macOS);
- free memory: `_memoire_dispo()` (`render.py`, `/proc/meminfo`, Windows API or `vm_stat`);
- ffmpeg installed by Clip Studio (`tools/ffmpeg/bin`) put first in the PATH by `clip/__init__.py`;
- rendering with "spawn".

`installer.sh` is used for Linux and macOS (Homebrew: Python 3.12 and `ffmpeg-full`, because Homebrew's basic ffmpeg
has no libass; torch from PyPI). macOS launcher: `Clip Studio.command`, which calls `clip-studio.sh`.

To avoid: `os.startfile`, `explorer`, `.exe` paths or Windows fonts without a fallback, hard-coded `/tmp`. Launchers:
`.bat` (CRLF), `.sh` and `.command` (LF, executable), see `.gitattributes`.

---

## Tests, screenshots, versions
- **Tests**: `python -m unittest` (in `tests/`, under 2 s). Run them after any change; add a test for every logic bug
  fixed (shotlist, lyrics, edit, signatures, cutting). On GitHub, the "Tests" action runs them on Windows, Linux and
  macOS at every push to `main` and every pull request.
- **End-to-end test**: `python scripts/essai_complet.py voice.wav` builds a song from a voice (speech synthesis of the
  script's lyrics), prepares with Whisper "small", creates fake panels, cuts, edits and renders a preview, then checks
  the mp4. No call to Claude (`CLIP_SANS_CLAUDE=1`). The "Tests" action runs it after `installer.sh` on Linux
  (`espeak-ng` voice) and macOS (`say` voice).
- **README screenshots**: `python scripts/captures.py [project]` (French and English). The script works on a temporary
  copy of the project; `?sel=p1_c3` in the address preselects an image at the Videos step, `?lang=en` forces the
  language.
- **Versions**:
  1. write the changes in [CHANGELOG.md](../CHANGELOG.md) and [CHANGELOG.en.md](../CHANGELOG.en.md), under a
     `## [x.y.z] - YYYY-MM-DD` title;
  2. `git tag vx.y.z && git push origin vx.y.z`.

  The `.github/workflows/release.yml` action then creates the Release with three zips (`…-Windows.zip` without the
  `.sh`, `…-Linux.zip` without the `.bat`, `…-macOS.zip` like Linux plus `Clip Studio.command`) and uses the section of
  both changelogs as notes.
- **Performance**: times measured in [GUIDE.en.md](GUIDE.en.md#processing-times) (3 min 14 song, 16 cores and 4
  simulated cores). The render depends mostly on the processor: the GPU encoder (h264_amf) gains only about 10% over
  libx264. To measure, `CLIP_WORKERS` and `CLIP_THREADS` force the number of render processes and of threads per
  process (12 processes were optimal on 32 threads; 16 → +10%, 24 → +25%). A script that starts the render must protect
  its code with `if __name__ == "__main__":` ("spawn" start).
- **Origin of the code**: the code was written largely with an AI assistant (Claude, Anthropic), under the author's
  direction (see the README). Contributions made with an AI are welcome, as long as they are reviewed, tested
  (`python -m unittest`) and flagged as such.
- **Dependencies**: versions pinned in `requirements.txt` (full tested environment: `requirements-complet.txt`); CPU
  torch and `rapidocr` (`--no-deps`) installed separately by the installers. Without RapidOCR, text detection is simply
  disabled (`textes()` returns `None`).
