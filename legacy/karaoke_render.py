#!/usr/bin/env python3
import json, subprocess, os
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1920, 1080
TXT_Y = H - 250
YELLOW = (255, 215, 0)
WHITE = (255, 255, 255)
OUT = "/tmp/v4"

def font(sz): return ImageFont.truetype(FONT, sz)

def tokenize(text):
    toks = []
    for w in text.split(" "):
        if w:
            toks.append(w)
    return toks

def layout(text, maxw, maxh):
    for sz in (56, 52, 48, 44, 40, 36, 32, 28, 24):
        f = font(sz)
        toks = tokenize(text)
        lines = [[]]
        for t in toks:
            trial = lines[-1] + [t]
            if f.getlength(" ".join(trial)) > maxw and lines[-1]:
                lines.append([t])
            else:
                lines[-1] = trial
        lh = int(sz * 1.4)
        totalh = lh * len(lines)
        maxw_line = max((f.getlength(" ".join(l)) for l in lines), default=0)
        if maxw_line <= maxw and totalh <= maxh:
            return sz, lines, lh
    f = font(24)
    toks = tokenize(text)
    return 24, [toks], 34

def make_overlay(text, highlight_idx, outpath):
    maxw = W - 220
    maxh = 270
    sz, lines, lh = layout(text, maxw, maxh)
    f = font(sz)
    img_w = int(max(f.getlength(" ".join(l)) for l in lines))
    img_h = int(lh * len(lines))
    img = Image.new("RGBA", (img_w + 32, img_h + 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img_w + 31, img_h + 31], radius=14, fill=(0, 0, 0, 120))
    gi = 0
    for li, line in enumerate(lines):
        y = li * lh + 16
        x = 16
        for w in line:
            col = YELLOW if gi == highlight_idx else WHITE
            d.text((x, y), w, font=f, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
            x += f.getlength(w) + f.getlength(" ")
            gi += 1
    img.save(outpath)
    return outpath, img_w, img_h

def build_plan():
    PLAN = []
    def add(img, s, e, txt): PLAN.append((img, s, e, txt))
    add("intro_farm", 0.0, 18.78, "Paye le Super")
    add("c1_fermier", 18.78, 23.72, "Le soleil s'lève à peine sur la terre du rang d'en haut")
    add("c1_f150", 23.72, 28.08, "Mon vieux F-150 tousse, y a le réservoir à sec et chaud")
    add("c1_remorque", 28.08, 33.12, "J'ai la remorque ben pleine, ça sent le fumier frais")
    add("c1_jardin", 33.12, 37.66, "Pour engraisser tes plate-bandes pis faire pousser tes bouquets")
    add("r_compost", 37.66, 42.46, "C'est du fumier de première, organique et ben costaud")
    add("c1_fermier", 42.46, 46.70, "Mais avant d'tourner la twist, j'ai une p'tite mise au point, mon gros")
    add("r_vache", 46.70, 49.00, "Oh! Tu veux du fumier, tu veux du beau compost")
    add("r_compost", 49.00, 51.44, "Du pur fumier de vache qui vient d'passer dans l'poste!")
    add("r_peanuts", 51.44, 53.74, "La garnotte est gratuite, le fumier est dans l'fond")
    add("r_gaz", 53.74, 56.32, "Mais icitte chez nous, on aime pas travailler pour des peanuts, non!")
    add("r_poignee", 56.32, 61.60, "Tu vas m'payer mon gaz pour la livraison, pis on s'serrera la main par après, mon champion!")
    add("c2_route", 61.60, 65.00, None)
    add("c2_route", 65.00, 69.50, "J'ai calculé la route, y a dix milles de gravelle")
    add("c2_super", 69.50, 74.32, "Mon pick-up boit du super, y est pus tout à fait neuve et belle")
    add("c2_taxi", 74.32, 78.82, "Tu t'attendais à quoi? Qu'j'arrive en taxi-brousse?")
    add("c2_engrais", 78.82, 83.58, "À distribuer l'engrais juste en échange d'une mousse?")
    add("c2_saintlaurent", 83.58, 88.54, "Non, mon pit, le Saint-Laurent y coule pas encore d'essence")
    add("c2_dixpiasses", 88.54, 92.82, "Faque sors ton dix piasse, pis montre un brin d'reconnaissance!")
    add("r_vache", 92.82, 95.12, "Oh! Tu veux du fumier, tu veux du beau compost")
    add("r_compost", 95.12, 97.52, "Du pur fumier de vache qui vient d'passer dans l'poste!")
    add("r_peanuts", 97.52, 99.82, "La garnotte est gratuite, le fumier est dans l'fond")
    add("r_gaz", 99.82, 102.44, "Mais icitte chez nous, on aime pas travailler pour des peanuts, non!")
    add("r_poignee", 102.44, 107.98, "Tu vas m'payer mon gaz pour la livraison, pis on s'serrera la main par après, mon champion!")
    add("p_ville", 107.98, 125.04, None)
    add("p_ville", 125.04, 129.96, "Y en a qui vendent du rêve dans la grande ville en béton")
    add("p_bouse", 129.96, 134.62, "Moi j'te vends d'la vraie bouse, mais j'pars pas sur le bras d'personne")
    add("p_pot", 134.62, 139.04, "Verse l'argent dans l'pot, pis décolle-moi la barrière")
    add("p_barriere", 139.04, 144.56, "Ou ben j'men r'tourne au rang avec mon fumier dans l'carré d'arrière!")
    add("s_route", 144.56, 165.98, None)
    add("r_vache", 165.98, 168.20, "Oh! Tu veux du fumier, tu veux du beau compost")
    add("r_compost", 168.20, 170.62, "Du pur fumier de vache qui vient d'passer dans l'poste!")
    add("r_peanuts", 170.62, 172.92, "La garnotte est gratuite, le fumier est dans l'fond")
    add("r_gaz", 172.92, 175.54, "Mais icitte chez nous, on aime pas travailler pour des peanuts, non!")
    add("r_poignee", 175.54, 181.50, "Tu vas m'payer mon gaz pour la livraison, pis on s'serrera la main par après, mon champion!")
    add("o_super", 181.50, 184.82, "Allez, paye le super...")
    add("o_soif", 184.82, 186.94, "Mon pick-up a soif pis moi aussi...")
    add("o_bottes", 187.50, 189.26, "Watch out tes bottes de rubber...")
    add("o_bottes", 189.26, 213.60, None)
    return PLAN

def word_times(trans, s, e):
    words = []
    for seg in trans:
        if seg["start"] < e and seg["end"] > s:
            for wd in seg["words"]:
                ws = max(wd["s"], s); we = min(wd["e"], e)
                if we > ws:
                    words.append((ws, we))
    return words

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(f"{OUT}/segs", exist_ok=True)
    trans = json.load(open("/tmp/transcript_m.json"))
    PLAN = build_plan()
    total = sum(e - s for _, s, e, _ in PLAN)
    print(f"PLAN {len(PLAN)} segments, total {total:.2f}s", flush=True)

    listfile = f"{OUT}/list.txt"
    lf = open(listfile, "w")
    for idx, (img, s, e, text) in enumerate(PLAN):
        dur = round(e - s, 3)
        imgpath = f"/tmp/v3/{img}.png"
        if not os.path.exists(imgpath):
            imgpath = f"/tmp/v3/{img}.webp"
        outseg = f"{OUT}/segs/s{idx:02d}.mp4"
        lf.write(f"file '{outseg}'\n")

        frames = max(1, int(dur * 25))
        z = (f"zoompan=z='min(zoom+0.0015,1.15)':d={frames}:"
             f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=25")
        vf = ("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
              f"{z},eq=contrast=1.08:saturation=1.15:brightness=0.01")

        cmd = ["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", imgpath]
        overlays = []
        if text is not None:
            words = word_times(trans, s, e)
            # base overlay (full line, all white)
            bp = f"{OUT}/o_{idx:02d}_base.png"
            make_overlay(text, -1, bp)
            b = Image.open(bp); bw, bh = b.size
            bx = int((W - bw) / 2); by = TXT_Y
            overlays.append((bp, "between(t,0.3,{:.2f})".format(max(0.31, dur - 0.45))))
            # per-word highlight
            for wi, (ws, we) in enumerate(words):
                wp = f"{OUT}/o_{idx:02d}_w{wi}.png"
                make_overlay(text, wi, wp)
                st = max(0.0, ws - s)
                en2 = min(dur, (words[wi + 1][0] - s)) if wi + 1 < len(words) else dur
                if en2 <= st: en2 = min(dur, st + 0.25)
                overlays.append((wp, "between(t,{:.2f},{:.2f})".format(st, en2)))
        # build filtergraph
        chain = "[0:v]" + vf + "[bg]"
        n = len(overlays)
        for i in range(n):
            chain += f";[{i+1}:v]format=rgba[ov{i}]"
        prev = "[bg]"
        for i in range(n):
            chain += f";{prev}[ov{i}]overlay=x={bx}:y={by}:enable='{overlays[i][1]}'[c{i}]"
            prev = f"[c{i}]"
        out_label = "c%d" % (n - 1) if n else "bg"
        fin = max(0.0, dur - 0.45)
        chain += f";{out_label}fade=t=in:st=0:d=0.3,fade=t=out:st={fin:.2f}:d=0.45[vout]"
        cmd += ["-filter_complex", chain, "-map", "[vout]",
                "-r", "25", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-pix_fmt", "yuv420p", outseg]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"ERR {idx} {img}: {r.stderr[-400:]}", flush=True)
        else:
            print(f"  seg {idx}: {img} {dur}s {'text' if text else 'inst'} words={len(word_times(trans,s,e)) if text else 0}", flush=True)
    lf.close()
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
