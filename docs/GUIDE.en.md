# Clip Studio user guide

[Français](GUIDE.md) | **English**

This guide explains how to make a music video with Clip Studio, from the song to the published video, and what to do
when something gets stuck. For the installation, see the [README](../README.en.md). For the internals, see
[TECHNICAL.en.md](TECHNIQUE.en.md).

- [What you need](#what-you-need)
- [Getting started: your first song](#getting-started-your-first-song)
- [The 8 steps in detail](#the-8-steps-in-detail)
- [Tips for good panels](#tips-for-good-panels)
- [Processing times](#processing-times)
- [Backup and history](#backup-and-history)
- [Troubleshooting](#troubleshooting)

---

## What you need

| | Required? | Role |
|---|---|---|
| **The song** (mp3, wav, m4a…) | yes | the soundtrack of the video |
| **The exact lyrics** (text) | yes | one lyric line per line; they are aligned automatically with the voice |
| **An image generator** | yes | you generate the images yourself, from the prompts Clip Studio prepares |
| **Claude Code** (Claude Pro/Max subscription) | no, but very useful | writes the scene descriptions and other texts, **only when you click** |
| **A video generator** (Google Flow / Veo…) | no | to animate some images |
| About **5 GB of free memory** | yes | to align the lyrics (Whisper "medium" model); 2 GB are enough with the "small" model, less accurate (step 2) |

**The image generator** must accept long prompts and, if possible, the **32:27** format (otherwise square). It must be
able to produce an image made of **6 photos in a grid**. Recent generators (Seedream, Qwen-Image, ChatGPT, Gemini,
Midjourney…) can do it, with more or less accuracy: make a test with the first panel. Clip Studio then checks the grid
and reports stray text.

**Without Claude**, everything is still possible: Clip Studio prepares a request (`build/a_decrire.md`) that you can
paste into any AI assistant, then you paste its answer back.

**Language**: the interface is in French or English (selector at the top right; by default, the language of your
browser). Each project also has a **song language** (step 1), used to align the lyrics and to write the texts in that
language: scene descriptions, image prompts, YouTube publishing. The two are independent: you can use the English
interface for a song in French.

---

## Getting started: your first song

Allow **15 to 25 minutes** for a 3-minute song: about 4 minutes of processing for Clip Studio, the rest to generate the
panels in your generator (1 to 2 minutes per panel, plus tries) and to review. Details in
[Processing times](#processing-times).

1. **Start Clip Studio** (`Clip Studio.bat` on Windows, `./clip-studio.sh` on Linux, `Clip Studio.command` on macOS):
   the page opens in your browser. Click **"+ New project"** and give it a name without spaces (e.g. `my_song`).
2. **Step 1 · Project**: drop the mp3, paste the lyrics in the box and save. Check the **song language**.
3. **Step 2 · Prepare**: write in a few lines the **intent** of the song (what it is really about, the tone, the era)
   and the wanted **visual style**, then click **Prepare**. Allow about 1 minute (rhythm, lyrics alignment, number of
   images to generate), plus a one-time 1.5 GB download the very first time.
4. **Step 3 · Descriptions**: click **"✨ Write with Claude"**. Review the scenes and redo the ones you don't like
   (↻ button).
5. **Step 4 · Panels**: for each panel, **copy the prompt**, generate the image in your generator (new conversation each
   time), then **paste it** (Ctrl+V) or drop it on its panel. Then click **Cut**.
6. **Step 7 · Render**: run a **Preview** (small quick video) to check. If all is well, run the **Final render**.
7. **Step 8 · Publishing** (optional): title, YouTube description with chapters, and thumbnail prompts.

Steps 5 (Videos) and 6 (Options) are optional: the default settings already give a clean video. Then try a preset
(Ballad, Rock…) at step 6.

---

## The 8 steps in detail

### 1. Project
- **Song**: mp3, wav, m4a, flac or ogg.
- **Lyrics**: the **exact** sung text, one lyric line per line, an empty line between verses. The `[Verse 1]`,
  `[Chorus]`, `[Bridge]` headers are optional. Without headers, a block repeated identically is recognized as a chorus.
- **Song language** (French or English): used by the lyrics alignment and by the texts written for this project. If
  you change it after "Prepare", the lyrics are realigned at the next "Prepare" or render.
- If you replace the mp3 or change the lyrics later, Clip Studio detects it: a warning is shown and the alignment is
  redone by itself at the next "Prepare" or render.

### 2. Prepare
- **Intent**: what the lyrics don't say (irony, tribute, anger, context, things to avoid). It guides Claude. The
  **style** (e.g. "photorealistic 80s, VHS grain") is included in every image prompt.
- **Prepare** detects the rhythm, aligns each word with the voice, then computes the number of images: **one image per
  unique lyric line** (a repeated chorus reuses its images).
- **Evaluation by Claude**: it recommends how many **ambiance** images to add for the parts without lyrics (intro,
  solos, ending) and a preset. As long as no panel is generated, the recommendation is applied automatically.
- **Lyrics alignment**: "Accurate" (Whisper medium, about 5 GB of memory, default) or "Limited memory" (Whisper small,
  about 2 GB, less accurate). Use "small" only if the alignment crashes for lack of memory.
- **Singing start**: if the karaoke starts too early (the 1st line shown during the intro), enter when the singing
  really starts (e.g. `0:34`): the first lines are realigned right away.
- **Solo photos** (optional): very wide panoramic images (21:9) the camera glides across during the instrumental
  parts. Claude can write their prompts. Solo photos and ambiance images alternate.

### 3. Descriptions
A short scene per image: shot type, subject, action, setting, lighting. The action must **literally illustrate the
lyric line**. Write them with Claude, fix them by hand, or redo one with an instruction ("darker", "outdoors").
The **recurring characters** are defined once (by Claude at the first writing, shown at the top of step 3, editable in
`projet.json` → `"personnages"`) and keep the same look from one image to the next.

### 4. Panels
A **panel** is a single generated image that contains **6 scenes** (2×3 grid). Clip Studio then cuts it into 6 images.
This is what makes it possible to make a whole video with only a few generations (e.g. 18 images → 3 panels).
- **Copy the prompt**, generate, then paste or drop the image on the right panel (P1, P2…).
- **Check** controls the format and the grid. **Cut** extracts and upscales the cells (×4 with Real-ESRGAN).
- **Stray text**: after cutting, readable captions, signs or printed t-shirts are reported. Retouch the cell if it is
  not intended.
- **Retouch a single cell**: generate a single 16:9 image for the failed cell and drop it. No need to redo the whole
  panel.

### 5. Videos (optional)
Click an image in the gallery to replace it with a **~10 s video**: Claude writes the prompt (only if you ask), you
generate the video in Flow ("Images to video", starting image = this image, 16:9 format), then you drop it. The video
replaces the image wherever it appears; the effects and the karaoke stay on top.

### 6. Options
Start with a **preset** (Ballad, Rock, Retro VHS, Plain), then adjust: camera moves, color grading, grain, particles
(snow, embers, rain…), smoke, flames, lightning, transitions, karaoke (font, colors, position, animation), title and
logo, "AI Version" notice, format (16:9, 4K, vertical 9:16, square). The settings stay from one render to the next.

The **automatic** effects (particles, smoke, lightning, light rays, camera move) read the scene descriptions, in French
or in English: "storm" brings rain and lightning, "fire" embers and smoke, "wide shot" a tracking shot, and so on.

### 7. Render
- **Quick preview**: 960×540 video to check the edit, in about 30 seconds for a 3-minute song.
- **Final render**: 1080p with sound, in 1 to 1.5 minutes for a 3-minute song; 4 to 6 minutes with many effects (3D
  parallax, smoke, background blur…); about 3× longer in 4K.
- **Preview of a part**: just an excerpt (e.g. from 0:30 to 0:50), to test a setting.
- **Variant**: a render under another name, to compare settings.
- The videos are in `projets/<name>/build/`. The buttons let you play, open or delete them.

### 8. Publishing
Claude writes a title, a YouTube description and two thumbnail prompts, in the song language. Clip Studio adds the
**chapters** (computed from the lyrics), the lyrics and the matching **AI notice**: original song reinterpreted by AI,
AI images only, or fully AI video.

---

## Tips for good panels
- **A new conversation per panel** in the generator: a "variation" of the previous image copies the same scenes.
- **Never the lyrics in the prompt**: a text between quotes ends up written in the image. Clip Studio never puts them
  in; don't add them.
- Avoid **documents, screens and signs** in the descriptions: they produce fake text.
- **Wide shots** work best in 16:9. For a close-up, think "whole head, room above".
- Keep a **copy of every generated image**: the generators' links expire.
- Panel almost right but one failed cell: **retouch the cell**, don't regenerate everything.

---

## Processing times

Measured on a **3 min 14** song (18 images, 3 panels), on two machines:
- **Powerful PC**: 16-core processor (Ryzen 9 9950X3D), AMD RX 9070 XT graphics card;
- **Ordinary PC**: the same PC limited to 4 cores / 8 threads, video encoding by the processor.

| Step | Powerful PC | Ordinary PC |
|---|---|---|
| Prepare: rhythm + lyrics alignment (without Claude) | 40 s | 55 s |
| First alignment only: Whisper model download | + 1.5 GB (depends on your connection) | same |
| Claude: evaluation / descriptions of 18 images / publishing | 20 s / 35 s / 20 s | same (depends on Claude) |
| Cutting the 3 panels (18 cells) | 12 s | 12 s with a graphics card; ~12 min without |
| Text detection in the cells (after cutting) | 3 to 6 s | ~5 s |
| Full quick preview | 35 s | 30 s |
| 1080p final render | 1 min | 1 min 25 |
| 1080p final render with heavy effects (3D parallax, smoke, particles, background blur) | 4 min | 6 min 15 |
| 4K final render | 3 min | — |

- Render times are **proportional to the length of the song**: for 4 minutes, allow about +25%.
- On a laptop or an old PC (2 cores, little memory), allow at least twice the "Ordinary PC" times (estimate, not
  measured).

---

## Backup and history
- Your projects (mp3, images, videos) are only on your computer. **`Sauvegarder les projets.bat`** (Windows) or
  **`./sauvegarder-projets.sh`** (Linux, macOS) copies them to the folder of your choice (OneDrive by default on
  Windows), without ever deleting anything in the backup. The video renders are not copied: they can be redone.
- Every change to a project's settings is kept: at step 1, **"🕘 Settings history"** lets you go back to a previous
  version.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **The karaoke starts too early** (1st line during the intro) | Step 2 → **Singing start**: enter when the voice starts. |
| **Lines flash by** or are sung elsewhere (after a long intro or a solo) | Normally fixed on its own: “Prepare” then listens to the song and aligns each section separately (about 1.5 min more, “section alignment” message in the log). If it persists, check that the .txt follows the sung order, with its [Section] headers. |
| **The karaoke is off everywhere** by the same amount | Step 6 → Karaoke → **Offset** (in seconds, + = later). |
| **The lyrics are badly aligned on a song in English** | Step 1 → check the **song language**, then run **Prepare** again. |
| **The images no longer follow the lyrics** after changing the mp3 | Run **Prepare** again (the alignment is redone automatically), then a render. |
| **Text shows up in an image** (caption, sign) | Step 4 → **Retouch a single cell** with an image without text. These cells are reported at step 4 after cutting. |
| **"Cells … instead of 16:9"** at the check | The generator did not respect the format: regenerate the panel in 32:27, or continue (the images will be slightly cropped). |
| **The grid is not recognized** (wrong cutting) | The generator made more or fewer than 6 photos, or without a clear separation: regenerate the panel. |
| **The lyrics alignment crashes** or the computer slows down | Whisper "medium" needs about 5 GB of free memory: close the other programs. Under WSL or Docker, increase the allocated memory. As a last resort, at step 2, choose "Lyrics alignment: Limited memory" ("small" model, about 2 GB): the karaoke will be less accurate (on a test song, 12 lines out of 30 off by more than half a second). |
| **"Real-ESRGAN unavailable"** | No Vulkan-compatible graphics card: the cells are upscaled another way, a bit less sharp. Nothing to do. |
| **A button answers "Unknown action"** / orange banner | Clip Studio was updated while it was running: close its window (or its terminal) and start it again. |
| **The "with Claude" buttons are missing** | Claude Code is not installed or not found: install it (see the README), then restart Clip Studio. |
| **"Tempo" obviously wrong** (effects twice too fast) | Step 6 → Technical → **Tempo (BPM)**: enter the right number, then run Prepare again. |
| **The page does not open** | Look at the address shown in the window (the port can be 8766, 8767… if 8765 is taken). |
| **The render is slow** | It depends mostly on the **processor** (number of cores) and the **effects**: 3D parallax, smoke and background blur multiply the time by about 4, 4K by 3. The graphics card changes little (~10%). For tests, use the **preview of a part**. |
| **The cutting is very slow** (several minutes) | No usable Vulkan graphics card (common under WSL or in a virtual machine): Real-ESRGAN runs on the processor, about 40 s per cell. It is normal; it is done only once per panel. |
| **The installer, console or command line messages are in the wrong language** | They follow the system language. To force it: `CLIP_LANG=en` (or `fr`) before the command, e.g. `set CLIP_LANG=en` in the Windows console. |

Still stuck? Check the installation with `python -m clip check` (from the Clip Studio folder:
`.venv\Scripts\python.exe -m clip check` or `.venv/bin/python -m clip check`).
