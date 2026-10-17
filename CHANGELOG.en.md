# Changelog

[Français](CHANGELOG.md) | **English**

The changes of each Clip Studio version. The section of a version is also used as the notes of its GitHub Release.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); version numbers `major.minor.patch`.

## [Unreleased]

### Added
- Step 2, **Check the alignment** card: sections with their times, badly aligned lines flagged (⚠), alert when the
  lyrics end well before the end of the audio (“It's normal” for an instrumental outro). Fix tools per section:
  **▶ listen**, **Realign** from a given second (Whisper realigns the section alone) and **Shift**. `section` command.
  “Prepare” lists the lines still badly aligned in its log.

### Fixed
- Render: impossible alignment times (end before start) are fixed before writing the karaoke.

## [1.5.0] - 2026-10-16

### Added
- Publishing: options of step 8, saved in the project. **Credits and links** (lyrics, music, performance, video, Clip
  Studio mention, links, official link for fan-made) added as is; **writing** (tone, short or normal hook, emojis,
  description blocks to keep); **thumbnail**: 3 ideas written at once, reference image (characters as they are in the
  video), banner text and color, square and vertical formats. **Profiles** reusable from one project to another (e.g.
  "KPR", "Fan-made").
- Publishing: two **Fan-made** origins (another artist's official song, or an AI cover of their song): "Fan-made"
  notice in the title and the thumbnail, description stating that you own no rights to the song (a fan working with
  Clip Studio, no profit intended, removal on request), rights left to the artist, and a reminder about YouTube's
  Content ID.

### Fixed
- Lyrics alignment: a chorus sung twice in a row (often with a solo in between) is no longer treated as a single
  block (the second becomes “Chorus (bis)”), and a failed section is first realigned on its own between the
  well-aligned lines around it. Before, the last chorus after a solo was squashed into a fraction of a second.

## [1.4.1] - 2026-10-14

### Fixed
- Lyrics alignment: when the global alignment misses lines (several lines squeezed into an instant after a long intro
  or a solo), Clip Studio listens to the song, locates each section and aligns it separately.
- The alignment repair was applied twice (while printing its message).

## [1.4.0] - 2026-10-10

### Added
- **Clip Studio in English**: interface, messages, installers, launchers, command line and documentation in French and
  English. Language chosen at the top right of the interface (by default, the browser's); elsewhere, the system's, or
  `CLIP_LANG=fr` / `en`.
- **Song language** (step 1, `"langue"` in `projet.json`): lyrics aligned by Whisper in the right language, and texts
  written in that language (scene descriptions, image prompts, solos, videos, evaluation, YouTube publishing with
  chapters and AI notice). Independent from the interface language. Existing projects stay in French and are not
  realigned.
- Automatic effects (particles, smoke, flames, lightning, rays, camera move): English keywords in addition to the French
  ones in the descriptions.

### Changed
- French of the interface and documentation: Quebec typography (no space before `;` `?` `!`).

## [1.3.9] - 2026-10-10

### Added
- **macOS (experimental)**: `installer.sh` also installs on macOS (Homebrew: Python 3.12 and ffmpeg; universal
  Real-ESRGAN for Intel / Apple chips), `Clip Studio.command` launcher, Arial font and free memory on macOS.
  `…-macOS.zip` in every Release. Validated automatically on GitHub's Macs, not yet on a real Mac.
- Automatic end-to-end test (`scripts/essai_complet.py`): synthetic song → checked preview video, run on GitHub on Linux
  and macOS after `installer.sh`.
- Step 2: choice of the lyrics alignment model. "Accurate" (Whisper medium, ~5 GB of memory, default) or "Limited
  memory" (Whisper small, ~2 GB, twice as fast but less accurate karaoke). The choice is kept in the project
  (`whisper`); changing it realigns the lyrics at the next "Prepare". Existing projects are not realigned.

## [1.3.8] - 2026-10-10

### Fixed
- `projet.json`, the descriptions, the lyrics alignment (`words.json`) and the image list are written in one go
  (temporary file then replace): an interruption during the write leaves the previous version intact instead of an
  empty file.

### Changed
- README: states what runs locally and what goes through the Internet (image generator, Claude).

## [1.3.7] - 2026-10-10

### Security
- `setuptools` 83.0.0 (instead of 78.1.0): fixes two flaws reported by Dependabot, which did not affect Clip Studio
  (functions not used).

### Added
- `Installer.bat` stops with a clear message if the Clip Studio folder has a path too long for Windows (over 100
  characters, unless long paths are enabled), instead of failing in the middle of the installation.
- Automatic tests on Windows and Linux on GitHub at every push and every pull request.

### Fixed
- Commands no longer crash when their output is redirected to a file on Windows (characters like "→" that cp1252
  cannot write).

## [1.3.6] - 2026-10-10

### Fixed
- `Installer.bat` (1.3.5): the installation stopped at the ffmpeg step ("... was unexpected") when ffmpeg was not
  already installed, because of parentheses in a message.

## [1.3.5] - 2026-10-10

### Security
- Local server: requests coming from another site (foreign `Host` or `Origin` header) are refused. A web page open at
  the same time can no longer drive Clip Studio.
- Installers: every downloaded file (Python, ffmpeg, Real-ESRGAN) is checked against its SHA256 checksum.

### Changed
- `Installer.bat` installs ffmpeg 8.0.1 (tested version) instead of the latest published version.
- README: the measures that limit Claude's token usage are explained, as well as the project's scope (personal
  project, best-effort help).

## [1.3.4] - 2026-10-10

### Fixed
- "Singing start": also applies when the alignment places the 1st verse too late (squeezed against the chorus); that
  verse is moved forward as a block to the given start.
- "Singing start": the automatic repair no longer moves the 1st section aligned on that start; the lines pulled into
  the intro are placed from that start at their natural length (no longer stretched up to the chorus).

## [1.3.3] - 2026-09-25

### Removed
- Old `Clip.bat` console menu (replaced by Clip Studio; the `python -m clip` command line is still available).
- `legacy/` folder (old scripts from before Clip Studio, no longer used).

## [1.3.2] - 2026-09-25

### Added
- README: "How Clip Studio was made" section (human design, code written largely with Claude).

### Changed
- Calls to Claude much cheaper in usage limit: Claude Code is started without tools, connectors or settings (~700
  tokens of context instead of ~34,500 per call), for the same answer.

## [1.3.1] - 2026-09-25

### Added
- Clip Studio logo: browser tab icon (`favicon.ico`) and logo in the interface header.

### Fixed
- `scripts/captures.py` waits for the browser to finish writing each screenshot (random failures).

## [1.3.0] - 2026-09-25

### Changed
- **Text detection in the cells**: RapidOCR replaces the built-in Windows OCR, and now also works on Linux. It finds
  text in images much better (on 165 cells: 14 real texts found instead of 3, including printed t-shirts, neons and
  signs). onnxruntime telemetry disabled.
  **Updating an existing installation: run `Installer.bat` or `installer.sh` again** (installs RapidOCR).

## [1.2.0] - 2026-09-25

### Fixed
- **Render about 2× faster** on many-core processors: each render process started as many compute threads as there are
  cores, and they got in each other's way (1080p: 2 min → 1 min for a 3-minute song, on 16 cores).

### Changed
- Durations shown in the guide and in the interface replaced by measured times (new "Processing times" section of the
  guide, powerful PC and ordinary PC).

## [1.1.0] - 2026-09-25

### Added
- Reorganized documentation:
  - [docs/GUIDE.md](docs/GUIDE.md) for usage (getting started, image generators, tips, troubleshooting);
  - [docs/TECHNIQUE.md](docs/TECHNIQUE.md) for the code (architecture, commands, `projet.json`, conventions);
  - `AGENTS.md` rewritten for any user's AI assistant.
- Illustrated README (screenshots of the steps and a frame of a video); `scripts/captures.py` regenerates them.
- Videos step: `?sel=p1_c3` in the address preselects an image.

### Changed
- The notes of each Release come from this changelog.

## [1.0.0] - 2026-09-24

First published version.

### Added
- **Clip Studio**, local web interface in 8 steps: Project, Prepare, Descriptions, Panels, Videos, Options, Render,
  Publishing.
- Automatic word-by-word alignment of the lyrics (Whisper / stable-ts) and of the rhythm (beats, automatic tempo).
- Panels: 1 image per unique lyric line, packed into the fewest generations; cutting and ×4 upscaling (Real-ESRGAN);
  retouching a single cell; stray text detection (Windows).
- Videos (Flow, Veo…) in place of any image.
- About a hundred settings: camera, 3D parallax, looks, particles, smoke, flames, lightning, transitions, karaoke,
  16:9 / 4K / 9:16 / 1:1 formats, presets.
- Claude Code (subscription) on request: descriptions, storyboard evaluation, solo and video prompts, YouTube
  publishing with chapters and AI notice.
- Reliability: changed mp3, lyrics or singing start detected and analyses redone, edit recomputed when needed, settings
  history, project backup, render adapted to the free memory.
- Windows (`Installer.bat`, without administrator rights) and Linux (`installer.sh`); separate zips in the Releases.
- 21 automatic tests.
