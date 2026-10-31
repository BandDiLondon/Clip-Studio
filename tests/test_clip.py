"""Tests rapides du pipeline (sans audio, sans Claude, sans rendu).
Lancer : .venv\\Scripts\\python.exe -m unittest   (depuis le dossier du projet)"""
import json
import tempfile
import unittest
from pathlib import Path

from clip import cli, shots, lyrics, plan, prompts


def seg(text, start, dur=2.0, section="Verse 1"):
    ws = text.split()
    step = dur / len(ws)
    return {"section": section, "text": text, "start": start, "end": start + dur,
            "words": [{"w": w, "s": round(start + i * step, 3), "e": round(start + (i + 1) * step, 3)}
                      for i, w in enumerate(ws)]}


class Shotlist(unittest.TestCase):
    def test_pack(self):
        # 6 par planche, la dernière prend la plus petite grille suffisante
        self.assertEqual(shots._pack(6), [6])
        self.assertEqual(shots._pack(18), [6, 6, 6])
        self.assertEqual(shots._pack(28), [6, 6, 6, 6, 4])
        self.assertEqual(shots._pack(17), [6, 6, 6])
        self.assertEqual(shots._pack(13), [6, 6, 1])
        self.assertEqual(shots._pack(14), [6, 6, 2])

    def test_key(self):
        self.assertEqual(shots.key("Poignées d'main,  MAINS moites!"), shots.key("poignees d'main mains moites"))

    def test_dedupe_et_ambiance(self):
        lines = [("Verse 1", "Un"), ("Chorus", "Refrain"), ("Verse 2", "Deux"), ("Chorus", "refrain !")]
        sl = shots.build(lines, dedupe=True, ambiance=2)
        vers = [s for s in sl["shots"] if not s.get("ambiance")]
        self.assertEqual([s["text"] for s in vers], ["Un", "Refrain", "Deux"])
        self.assertEqual(vers[1]["sections"], ["Chorus", "Chorus"])
        self.assertEqual(len(sl["shots"]), 6)                     # 3 vers + 2 ambiance → planche de 6 (1 case libre)
        self.assertEqual([s["id"] for s in sl["shots"]][:2], ["p1_c1", "p1_c2"])

    def test_ajout_ambiance_garde_les_planches(self):
        # 18 vers = 3 planches pleines : ajouter de l'ambiance ne change pas P1-P3
        lines = [("Verse", f"vers {i}") for i in range(18)]
        a, b = shots.build(lines), shots.build(lines, ambiance=10)
        self.assertEqual([s["key"] for s in a["shots"]], [s["key"] for s in b["shots"][:18]])
        self.assertEqual(len(b["planches"]), 5)


class Paroles(unittest.TestCase):
    def test_sections_automatiques(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.txt"
            f.write_text("a\nb\n\nrefrain\nx\n\nc\n\nrefrain\nx\n", encoding="utf-8")
            secs = [s for s, _ in lyrics.read_lyrics(f)]
        self.assertEqual(secs, ["Verse 1", "Verse 1", "Chorus", "Chorus", "Verse 2", "Chorus", "Chorus"])

    def test_refrains_consecutifs_separes(self):
        # deux refrains qui se suivent (solo entre les deux) : deux blocs d'alignement, pas un seul
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.txt"
            f.write_text("a\n\nrefrain\n\nrefrain\n", encoding="utf-8")
            sans = lyrics.read_lyrics(f)
            f.write_text("[Verse]\na\n[Chorus]\nrefrain\n[Chorus]\nrefrain\n", encoding="utf-8")
            avec = lyrics.read_lyrics(f)
        for lines in (sans, avec):
            self.assertEqual([s for s, _ in lines][1:], ["Chorus", "Chorus (bis)"])
            self.assertEqual(len(lyrics.blocks(lines)), 3)

    def test_verification_du_calage(self):
        # dernier refrain tassé à 14 s : section signalée, fin suspecte, fenêtre de recalage, décalage, temps impossibles
        segs = [seg("a b", 10.0, 2.0, "Chorus"), seg("c d", 12.0, 2.0, "Chorus"),
                seg("a b", 14.0, 0.02, "Chorus (bis)"), seg("c d", 14.0, 0.02, "Chorus (bis)")]
        secs = lyrics.sections(segs)
        self.assertEqual([(x["section"], x["vers"], x["mal_cales"]) for x in secs], [("Chorus", 2, 0), ("Chorus (bis)", 2, 2)])
        self.assertEqual(lyrics.fin_trop_tot(segs, 60.0), 46.0)
        self.assertEqual(lyrics.fin_trop_tot(segs, 30.0), 0)
        self.assertEqual(lyrics.section_window(segs, 1, 40.0, 60.0), (40.0, 60.0))
        self.assertEqual(lyrics.section_window(segs, 0, 9.0, 60.0), (9.0, 60.0))      # vers tassés avant : ignorés
        with self.assertRaises(ValueError):
            lyrics.section_window(segs, 1, 59.8, 60.0)                                   # pas la place
        with self.assertRaises(ValueError):
            lyrics.shift_section(segs, 5, 1.0)
        lyrics.shift_section(segs, 0, -1.5)
        self.assertEqual((segs[0]["start"], segs[1]["end"]), (8.5, 12.5))
        segs[2]["words"][1].update(s=13.0, e=12.0)                   # commence avant le précédent, finit avant de commencer
        self.assertEqual(lyrics.sanitize(segs), 1)
        w0, w1 = segs[2]["words"]
        self.assertTrue(w1["s"] >= w0["s"] and w1["e"] >= w1["s"])
        self.assertEqual(lyrics.sanitize(segs), 0)

    def test_fenetres_locales_apres_solo(self):
        # dernier refrain tassé à la fin du solo : seul son bloc est recalé, entre le dernier vers bien calé et la fin
        lines = [("Chorus", "a b"), ("Chorus", "c d"), ("Chorus (bis)", "a b"), ("Chorus (bis)", "c d")]
        segs = [seg("a b", 10.0, 2.0, "Chorus"), seg("c d", 12.0, 2.0, "Chorus"),
                seg("a b", 14.0, 0.02, "Chorus (bis)"), seg("c d", 14.0, 0.02, "Chorus (bis)")]
        self.assertEqual(lyrics.local_windows(lines, segs, 60.0), [None, (14.0, 60.0)])

    def test_repair_mot_isole(self):
        s = seg("un deux trois quatre", 50.0)
        s["words"][0]["s"], s["words"][0]["e"] = 20.0, 20.3          # 1er mot aspiré 30 s plus tôt
        s["start"] = 20.0
        lyrics.repair([s])
        self.assertGreater(s["words"][0]["s"], 49.0)
        self.assertEqual(s["start"], s["words"][0]["s"])

    def test_force_start(self):
        segs = [seg("premier vers ici", 2.0), seg("deuxieme vers", 4.0), seg("troisieme vers", 40.0)]
        lyrics.force_start(segs, 34.0)
        self.assertGreaterEqual(segs[0]["start"], 34.0)
        self.assertLess(segs[1]["end"], 40.01)
        self.assertEqual(segs[2]["start"], 40.0)

    def test_force_start_premier_couplet_en_retard(self):
        segs = [seg("premier vers", 33.0), seg("deuxieme vers", 35.0), seg("refrain", 45.0, section="Verse 2")]
        lyrics.force_start(segs, 20.0)
        self.assertEqual((segs[0]["start"], segs[1]["start"]), (20.0, 22.0))
        self.assertEqual(segs[1]["words"][0]["s"], 22.0)
        self.assertEqual(segs[2]["start"], 45.0)

    def test_reparation_respecte_debut_chant(self):
        segs = [seg("un deux", 20.0), seg("trois quatre", 22.0), seg("cinq six", 44.0),
                seg("refrain ici", 46.0, section="Verse 2"), seg("refrain la", 48.0, section="Verse 2")]
        lyrics.repair(segs, 20.0)
        self.assertEqual((segs[0]["start"], segs[1]["start"]), (20.0, 22.0))

    def test_vers_ecrases_detectes(self):
        ok = seg("un deux trois", 10.0)
        tasse = seg("quatre cinq six", 12.0, dur=0.05)                # 3 mots dans 0,05 s
        absent = seg("sept huit", 14.0)
        absent["words"][1]["s"] = absent["words"][1]["e"] = None
        self.assertEqual(lyrics.bad_lines([ok, tasse, absent]), [1, 2])

    def test_blocs_de_sections(self):
        lines = [("V1", "a"), ("V1", "b"), ("Chorus", "c"), ("V2", "d"), ("Chorus", "c"), (None, "e"), (None, "f")]
        self.assertEqual(lyrics.blocks(lines), [[0, 1], [2], [3], [4], [5], [6]])

    def test_fenetres_par_section(self):
        # couplet chanté vers 30 s, refrain vers 60 s; la transcription a des fautes et du bruit (« générique »)
        lines = [("V1", "J'arrive pus a penser"), ("V1", "dans le cadre"), ("Chorus", "Ayoye ça fait mal")]
        heard = [("Générique", 0.0, 20.0), ("J'arrive", 30.0, 30.5), ("plus", 30.6, 31.0), ("à", 31.0, 31.2),
                 ("penser", 31.3, 32.0), ("dans", 33.0, 33.3), ("le", 33.3, 33.5), ("cadre", 33.6, 34.4),
                 ("Aïe", 60.0, 60.5), ("ça", 60.6, 61.0), ("fait", 61.0, 61.4), ("mal", 61.5, 62.0)]
        (a1, b1), (a2, b2) = lyrics.match_windows(lines, heard, 100.0)
        self.assertTrue(28.0 <= a1 <= 30.0 and 34.4 <= b1 < 60.0)
        self.assertTrue(34.4 < a2 <= 60.0 and 62.0 <= b2 <= 64.0)

    def test_fenetre_bloc_non_entendu(self):
        # refrain absent de la transcription : il prend l'espace entre les mots entendus de ses voisins
        lines = [("V1", "un deux"), ("Chorus", "rien entendu"), ("V2", "trois quatre")]
        heard = [("un", 10.0, 10.5), ("deux", 10.6, 11.0), ("trois", 40.0, 40.5), ("quatre", 40.6, 41.0)]
        w = lyrics.match_windows(lines, heard, 60.0)
        self.assertTrue(11.0 <= w[1][0] < w[1][1] <= 40.0)
        self.assertTrue(w[0][0] <= 10.0 and w[2][1] >= 41.0)

    def test_force_start_pas_d_etirement(self):
        segs = [seg("premier vers ici", 5.0), seg("deuxieme vers", 7.0), seg("refrain", 43.0, section="V2")]
        lyrics.force_start(segs, 20.0)
        self.assertEqual(segs[0]["start"], 20.0)
        self.assertLess(segs[1]["end"], 30.0)


class Montage(unittest.TestCase):
    def test_alternance_solos_ambiance(self):
        f = plan._Filler(["s1.png", "s2.png"], ["a1", "a2", "a3", "a4"], [])
        kinds = [k for k, _ in f.pool]
        self.assertEqual(f.pool[0], ("travel", "s1.png"))            # commence par un solo
        self.assertEqual(kinds.count("travel"), 2)
        self.assertEqual(kinds.count("img"), 4)
        self.assertNotIn(("travel", "travel"), list(zip(kinds, kinds[1:])))

    def test_solos_seuls(self):
        ev = plan._Filler(["s1.png"], [], []).fill(0, 20, "intro")
        self.assertTrue(ev and all(e.get("travel") == "s1.png" for e in ev))

    def test_plan_suit_les_paroles(self):
        segs = [seg("un", 15.0), seg("deux", 18.0)]
        sl = shots.build([("V", "un"), ("V", "deux")])
        tl = plan.build(segs, [], {"solos_list": ["s1.png"]}, 30.0, sl)
        imgs = {e["img"]: e["t"] for e in tl if "img" in e}
        self.assertAlmostEqual(imgs["p1_c1"], 15.0, delta=0.5)
        self.assertEqual(tl[0].get("travel"), "s1.png")              # intro instrumentale


class Prompts(unittest.TestCase):
    def test_prose_sans_etiquettes(self):
        p = prompts.prose("Plan : large ; Sujet : un homme ; Action : il court ; Décor : rue ; Lumière : nuit")
        for lab in ("Plan :", "Sujet", "Action", "Décor", "Lumière"):
            self.assertNotIn(lab, p)
        self.assertIn("il court", p)

    def test_prose_anglais(self):
        p = prompts.prose("Shot: wide ; Subject: a man ; Action: he runs ; Setting: a street ; Lighting: night", "en")
        for lab in ("Shot:", "Subject", "Setting", "Lighting:"):
            self.assertNotIn(lab, p)
        self.assertIn("he runs", p)
        self.assertIn("wide shot", p.lower())

    def test_entete_sans_storyboard(self):
        for lg in ("fr", "en"):
            self.assertNotIn("storyboard", prompts.HEADER[lg].lower())


class Projet(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.p = Path(self.d.name)
        (self.p / "build").mkdir()
        (self.p / "c.mp3").write_bytes(b"x" * 100)
        (self.p / "p.txt").write_text("a\nb\n", encoding="utf-8")
        (self.p / "build" / "beats.npy").write_bytes(b"0")
        (self.p / "build" / "words.json").write_text("{}", encoding="utf-8")
        self.cfg = {"audio": "c.mp3", "paroles": "p.txt", "debut_chant": 0, "bpm_hint": "auto"}
        self.cfg["beats_sig"] = cli._sig(self.p, self.cfg, "beats")
        self.cfg["paroles_sig"] = cli._sig(self.p, self.cfg, "paroles")

    def tearDown(self):
        self.d.cleanup()

    def test_rien_de_perime(self):
        self.assertEqual(cli.perimes(self.p, self.cfg), [])

    def test_mp3_change(self):
        (self.p / "c.mp3").write_bytes(b"y" * 120)
        self.assertEqual(cli.perimes(self.p, self.cfg), ["beats", "paroles"])

    def test_paroles_identiques_recollees(self):
        (self.p / "p.txt").write_bytes(b"\xef\xbb\xbfa \r\nb\r\n\r\n\r\n")    # BOM, espaces, CRLF, lignes vides
        self.assertEqual(cli.perimes(self.p, self.cfg), [])
        (self.p / "p.txt").write_text("a\nc\n", encoding="utf-8")
        self.assertEqual(cli.perimes(self.p, self.cfg), ["paroles"])

    def test_debut_chant(self):
        self.cfg["debut_chant"] = 34
        self.assertEqual(cli.perimes(self.p, self.cfg), ["paroles"])

    def test_historique(self):
        cli._save(self.p, {"look": "a"})
        cli._save(self.p, {"look": "b"})
        h = list((self.p / "build" / "historique").glob("projet_*.json"))
        self.assertEqual(len(h), 1)
        self.assertEqual(json.loads(h[0].read_text(encoding="utf-8"))["look"], "a")
        self.assertEqual(json.loads((self.p / "projet.json").read_text(encoding="utf-8"))["look"], "b")


class Decoupe(unittest.TestCase):
    def test_sans_realesrgan(self):
        # sans GPU Vulkan ni binaire : la découpe continue avec un agrandissement classique
        from PIL import Image
        from clip import panels
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "planches").mkdir()
            im = Image.new("RGB", (1536, 1296), (0, 0, 0))
            for r in range(3):
                for c in range(2):
                    im.paste((90, 90, 90), (c * 768 + 6, r * 432 + 6, c * 768 + 762, r * 432 + 426))
            im.save(d / "planches" / "P1.png")
            old, panels.ESRGAN = panels.ESRGAN, Path("introuvable.exe")
            try:
                panels.cut_all(d, "planches", scale=4, grids={"p1": (2, 3)})
            finally:
                panels.ESRGAN = old
            cases = sorted((d / "cases").glob("p1_c*.png"))
            self.assertEqual(len(cases), 6)
            self.assertGreater(Image.open(cases[0]).width, 2000)


class Ocr(unittest.TestCase):
    def test_bribes_ignorees(self):
        from clip.ocr import _utile
        self.assertFalse(_utile("00"))
        self.assertFalse(_utile("a1"))
        self.assertTrue(_utile("MOTEL"))

    @unittest.skipUnless(__import__("importlib").util.find_spec("rapidocr"), "RapidOCR non installé")
    def test_telemetrie_coupee(self):
        # onnxruntime (Linux) crée un identifiant d'appareil et peut envoyer des données sans cette variable
        import os
        from clip.ocr import _moteur
        _moteur()
        self.assertEqual(os.environ.get("ORT_DISABLE_TELEMETRY"), "1")

    @unittest.skipUnless(__import__("importlib").util.find_spec("rapidocr"), "RapidOCR non installé")
    def test_legende_detectee_et_image_propre(self):
        from PIL import Image, ImageDraw
        from clip.ocr import textes
        from clip.panels import _font
        with tempfile.TemporaryDirectory() as d:
            f, g = Path(d) / "p1_c1.png", Path(d) / "p1_c2.png"
            im = Image.new("RGB", (1280, 720), (40, 40, 60))
            im.save(g)                                               # sans texte
            ImageDraw.Draw(im).text((60, 600), "Photo 1 : plan large", font=_font(48), fill=(255, 255, 255))
            im.save(f)
            r = textes([f, g])
            self.assertIn("plan large", " ".join(r.get("p1_c1", [])).lower())
            self.assertNotIn("p1_c2", r)


class Instrumental(unittest.TestCase):
    """Mode instrumental : niveaux d'énergie, pics, coupes, répartition des images, montage, prompts, publication."""
    @staticmethod
    def rythme(n=96, calme=32, intense=32):
        # 96 beats à 120 BPM : 32 calmes, 32 modérés, 32 intenses
        e = [0.2] * calme + [0.5] * (n - calme - intense) + [0.9] * intense
        from clip import instrumental as ins
        return [round(i * 0.5, 3) for i in range(n)], {"phase": 0, "energie": e, "niveaux": ins.niveaux(e),
                                                         "pics": [[6.1, 1.0], [10.1, 0.3]], "duree": 48.0}

    def test_niveaux_et_passages(self):
        from clip import instrumental as ins
        beats, r = self.rythme()
        self.assertEqual([x["niveau"] for x in ins.passages(beats, r)], [0, 1, 2])
        self.assertEqual(ins.niveaux([0.5] * 40), [1] * 40)              # énergie uniforme : tout modéré
        lv = ins.niveaux([0.2] * 30 + [0.9] * 3 + [0.2] * 30)           # passage trop court : absorbé
        self.assertEqual(len(set(lv)), 1)
        lv = ins.niveaux([0.2] * 40 + [0.9] * 10 + [0.5] * 40)
        self.assertTrue(all(b - a >= ins.RUN_MIN for a, b, _ in ins._runs(lv)))

    def test_pics(self):
        from clip import instrumental as ins
        env = [0.05] * 2000
        for i in (300, 310, 900, 1500):                                   # 310 : trop près de 300
            env[i] = 1.0 if i != 1500 else 0.5
        p = ins.pics(env, 0.0116)
        self.assertEqual(len(p), 3)
        self.assertTrue(all(b[0] - a[0] >= ins.PIC_MIN for a, b in zip(p, p[1:])))
        self.assertEqual(max(f for _, f in p), 1.0)

    def test_coupes_et_montage(self):
        from clip import instrumental as ins
        beats, r = self.rythme()
        c = ins.coupes(beats, r, densite=2)
        t = lambda a, b: [x for x, _ in c if a <= x < b]
        self.assertEqual(t(0, 12), [0.0, 4.0, 6.0, 8.0])   # calme : toutes les 8 beats (4 s) + pic fort à 6,1 s
        self.assertEqual(len(t(18, 30)), 6)             # modéré : toutes les 4 beats (2 s)
        self.assertEqual(len(t(36, 46)), 10)            # intense : tous les 2 beats (1 s)
        self.assertNotIn(10.0, t(9, 11))                # pic faible : pas de coupe imposée
        self.assertEqual(c[0][0], 0.0)
        cfg = {"images_instrumental": 12, "langue": "fr"}
        sl = ins.shotlist(cfg, beats, r)
        self.assertEqual(len(sl["shots"]), 12)
        self.assertEqual({s["niveau"] for s in sl["shots"]}, {0, 1, 2})
        ev = ins.plan(beats, r, sl["shots"], cfg)
        self.assertEqual(len(ev), len(c))
        self.assertTrue(all(a["img"] != b["img"] for a, b in zip(ev, ev[1:])))
        niv = {s["id"]: s["niveau"] for s in sl["shots"]}
        self.assertTrue(all(niv[e["img"]] == n for e, (_, n) in zip(ev, c)))      # image du bon niveau
        self.assertTrue(any(e.get("variante") for e in ev))                         # images qui reviennent
        self.assertEqual(ins.nombre_images({"images_instrumental": 500}), ins.IMAGES[1])

    def test_effets_au_beat_selon_l_energie(self):
        from clip import instrumental as ins, render
        beats, r = self.rythme()
        w = ins.poids(r)
        self.assertEqual(len(w), len(beats))
        self.assertAlmostEqual(w[0], ins.POIDS[0])                       # passage calme : effets adoucis
        self.assertAlmostEqual(w[-1], ins.POIDS[1])                      # passage intense : renforcés
        render.S.clear()
        self.assertEqual(render._force(10.0), (1.0, 0.0))                # option désactivée : inchangé
        render.S.update(poids_t=beats, poids_v=w, pics_t=[6.1], pics_f=[1.0])
        self.assertEqual(render._force(1.0), (ins.POIDS[0], 0.0))
        self.assertGreater(render._force(6.15)[1], 0.6)                  # coup en plus sur le pic
        render.S.clear()

    def test_egaliseur(self):
        import numpy as np
        from PIL import Image
        from clip import effects
        sr, fps = 22050, 30
        t = np.arange(int(sr * 4)) / sr
        x = np.zeros_like(t)
        for k in range(4):                                               # grosse caisse 60 Hz toutes les 0,5 s (0-2 s)
            m = (t >= k * 0.5) & (t < k * 0.5 + 0.08)
            x[m] += np.sin(2 * np.pi * 60 * t[m])
        hiss = np.random.default_rng(1).normal(0, 0.3, len(t))
        x[t >= 3] += np.diff(np.concatenate([[0], hiss]))[t >= 3]       # cymbale : bruit aigu à partir de 3 s
        eq = effects.bands_frames(x.astype(np.float32), sr, fps, 4 * fps)
        self.assertEqual(eq.shape, (4 * fps, 3))
        self.assertGreater(eq[int(0.52 * fps), 0], 0.5)                  # coup de grosse caisse : graves
        self.assertLess(eq[int(2.9 * fps), 0], 0.2)                      # silence : retombé
        self.assertGreater(eq[int(3.05 * fps), 2], 0.5)                  # attaque de la cymbale : aigus
        im = Image.new("RGB", (320, 180))
        for style in ("barres", "miroir", "cercle", "onde"):
            out = effects.visualizer(im, np.linspace(0, 1, 40), style, "#FFDC50", 0.2, bandes=True)
            self.assertGreater(np.asarray(out).sum(), 0)
        self.assertGreater(np.asarray(effects.sparkle(im, 1.0, 3)).sum(), 0)
        self.assertIs(effects.sparkle(im, 0.0, 3), im)

    def test_variantes_du_rendu(self):
        from PIL import Image
        from clip import render
        im = Image.new("RGB", (4, 2), (200, 30, 30))
        im.putpixel((0, 0), (0, 0, 255))
        self.assertEqual(render.variante(im, 1).getpixel((3, 0)), (0, 0, 255))      # miroir
        self.assertEqual(render.variante(im, 2).getpixel((3, 1)), (0, 0, 255))      # rotation 180°
        self.assertEqual(render.variante(im, 3).getpixel((0, 1)), (0, 0, 255))      # retournement vertical
        self.assertNotEqual(render.variante(im, 4).getpixel((1, 1)), (200, 30, 30))  # teinte décalée

    def test_prompts_et_publication(self):
        from clip import instrumental as ins, publish
        beats, r = self.rythme()
        cfg = {"langue": "fr", "instrumental": True, "style": "", "images_instrumental": 12,
               "personnages": {"X": "ne doit pas apparaître"}}
        sl, md = prompts.skeleton(cfg, ins.shotlist(cfg, beats, r), {})
        self.assertIn("images abstraites distinctes", md)
        self.assertNotIn("ne doit pas apparaître", md)
        self.assertIn("abstraite, énergie", md)
        self.assertIn("énergie calme", ins.label(cfg, sl["shots"][0], beats, r))
        cfg.update(titre="T", artiste="A", origine="images")
        d = publish.description(cfg, {"accroche": "x"}, [], "(instrumental)")
        self.assertNotIn("(instrumental)", d)
        self.assertIn(publish.MOTS["fr"]["droits_instru"], d)
        chaps = publish.chapitres(ins.segments_chapitres(beats, r), 48.0)
        self.assertEqual([c.split(" ", 1)[1] for c in chaps], ["Calme", "Modéré", "Intense"])

    def test_paroles_facultatives(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "son.mp3").write_bytes(b"x")
            cli._need(p, {"instrumental": True, "audio": "son.mp3", "paroles": None}, "audio", "paroles")
            with self.assertRaises(cli.Stop):
                cli._need(p, {"audio": "son.mp3", "paroles": None}, "audio", "paroles")


class Import(unittest.TestCase):
    def test_modules(self):
        # tous les modules s'importent (erreur de syntaxe dans un module non testé ailleurs)
        import importlib
        for m in ("render", "effects", "depth", "web", "ai", "publish", "evaluate", "audio", "demandes"):
            importlib.import_module(f"clip.{m}")


class Whisper(unittest.TestCase):
    def test_modele_dans_l_empreinte(self):
        # medium : empreinte inchangée (pas de recalage des anciens projets) ; small : paroles à recaler
        import argparse
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "a.mp3").write_bytes(b"x")
            (p / "a.txt").write_text("un vers", encoding="utf-8")
            cfg = {"audio": "a.mp3", "paroles": "a.txt", "debut_chant": 12}
            ancien = cli._sig(p, cfg, "paroles")
            self.assertEqual(ancien, cli._sig(p, {**cfg, "whisper": "medium"}, "paroles"))
            small = cli._sig(p, {**cfg, "whisper": "small"}, "paroles")
            self.assertNotEqual(ancien, small)
            # recalage rapide (début du chant) : seule la dernière partie de l'empreinte doit différer
            self.assertTrue(small.endswith("|12.0"))
        self.assertEqual(cli._whisper(argparse.Namespace(model=None), {"whisper": "small"}), "small")
        self.assertEqual(cli._whisper(argparse.Namespace(model="small"), {}), "small")
        self.assertEqual(cli._whisper(argparse.Namespace(), {}), "medium")
        with self.assertRaises(cli.Stop):
            cli._whisper(argparse.Namespace(model=None), {"whisper": "large-v3"})


class Langues(unittest.TestCase):
    def tearDown(self):
        from clip import i18n
        i18n.fixer(None)

    def test_langue_des_messages(self):
        import os
        from unittest import mock
        from clip import i18n
        with mock.patch.dict(os.environ, {"CLIP_LANG": "en"}):
            self.assertEqual(i18n.tr("bonjour", "hello"), "hello")
            i18n.fixer("fr")                                   # la requête web l'emporte sur CLIP_LANG
            self.assertEqual(i18n.tr("bonjour", "hello"), "bonjour")
        i18n.fixer(None)
        with mock.patch.dict(os.environ, {"CLIP_LANG": ""}):
            self.assertEqual(i18n.tr("bonjour", "hello"), "bonjour")      # défaut : français

    def test_langue_du_projet(self):
        from clip import i18n, prompts, publish
        self.assertEqual(i18n.langue_projet({}), "fr")                    # anciens projets : français
        self.assertEqual(i18n.tp({"langue": "en"}, "a", "b"), "b")
        pl = {"grid": [2, 3], "ratio": "32:27"}
        en = prompts.render_prompt(pl, [({"text": "x"}, "Shot: wide ; Action: he runs")], {"langue": "en"})
        self.assertIn("EXACTLY 6", en)
        self.assertIn("wide shot", en.lower())
        segs = [seg("a b", t, 2.0, s) for t, s in ((12, "Verse 1"), (16, "Verse 1"), (30, "Chorus"), (34, "Chorus"),
                                                    (50, "Verse 2"))]
        ch = publish.chapitres(segs, 70, langue="en")
        self.assertTrue(any("Verse 1" in c for c in ch) and any("Chorus" in c for c in ch), ch)
        self.assertTrue(any("Couplet 1" in c for c in publish.chapitres(segs, 70)))

    def test_publication_fan_made(self):
        # fan-made : mention, déclaration « aucun droit » et droits laissés à l'artiste, dans les deux langues
        from clip import publish
        for lg, droits in (("fr", "aucun droit"), ("en", "do not own any rights")):
            for o in ("fan", "fan_ia"):
                cfg = {"langue": lg, "titre": "Chanson", "artiste": "Artiste", "origine": o}
                d = publish.description(cfg, {"accroche": "x"}, [], "paroles")
                self.assertIn("Fan-made", d)
                self.assertIn(droits, d)
                self.assertIn(publish.MOTS[lg]["droits_fan"], d)
                self.assertIn("Fan-made", publish.demande(cfg, "paroles"))

    def test_options_de_publication(self):
        from clip import publish
        cfg = {"langue": "fr", "titre": "T", "artiste": "A", "origine": "fan", "publication": {
            "credits": {"paroles": "Moi"}, "clip_studio": True, "liens": "Spotify : s\n\n", "lien_officiel": "https://o",
            "emojis": False, "blocs": {"paroles": False, "hashtags": False}, "ton": "drole", "accroche": "courte",
            "bandeau": "nouveau", "bandeau_couleur": "jaune", "formats": ["vertical", "inconnu"]}}
        r = publish.reglages(cfg)
        self.assertTrue(r["blocs"]["chapitres"])                         # blocs absents : par défaut
        self.assertEqual(r["formats"], ["vertical"])
        d = publish.description(cfg, {"accroche": "Wow", "hashtags": ["#x"]}, ["0:00 Intro"], "la la")
        for attendu in ("Paroles : Moi", publish.CLIP_STUDIO_URL, "Spotify : s", "Chanson officielle : https://o", "Wow"):
            self.assertIn(attendu, d)
        self.assertNotIn("la la", d)                                     # bloc paroles décoché
        self.assertNotIn("#x", d)
        self.assertNotIn("🎬", d)                                        # sans emojis
        q = publish.demande(cfg, "p", reference="Plan : large ; Sujet : Maxime chauve")
        for attendu in ("drôle", "1 phrase", "Aucun emoji", "« NOUVEAU »", "jaune vif", '"vertical"', "Maxime chauve"):
            self.assertIn(attendu, q)
        self.assertNotIn('"carre"', q)
        en = publish.demande({**cfg, "langue": "en"}, "p")
        self.assertIn("funny", en)
        self.assertIn("bright yellow", en)

    def test_miniatures(self):
        from clip import publish
        ia = {"miniatures": [{"idee": "a", "avec_texte": "A", "sans_texte": "a", "carre": "C"}, {"idee": "vide"}] * 3}
        self.assertEqual(len(publish.miniatures(ia)), 3)
        self.assertEqual(publish.miniatures(ia)[0]["carre"], "C")
        self.assertEqual(publish.miniatures({"miniature": "M", "miniature_sans_texte": "m"}),   # ancien format
                         [{"idee": "", "avec_texte": "M", "sans_texte": "m"}])
        md = publish.markdown({"titre": "t", "description": "d\n", "miniatures": publish.miniatures(ia)})
        self.assertIn("Miniature 3 — a (carrée 1:1)", md)

    def test_profils_de_publication(self):
        from clip import web
        with tempfile.TemporaryDirectory() as d:
            old = web.PROJETS, web.PROFILS
            web.PROJETS, web.PROFILS = Path(d), Path(d) / "_profils_publication.json"
            try:
                web.enregistrer_profil("KPR", {"origine": "suno"})
                self.assertEqual(web.profils(), {"KPR": {"origine": "suno"}})
                web.enregistrer_profil("KPR", None)
                self.assertEqual(web.profils(), {})
                with self.assertRaises(ValueError):
                    web.enregistrer_profil(" ", {})
            finally:
                web.PROJETS, web.PROFILS = old

    def test_langue_dans_l_empreinte(self):
        # langue absente de l'empreinte en français (pas de recalage des anciens projets), présente en anglais
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "a.mp3").write_bytes(b"x")
            (p / "a.txt").write_text("un vers", encoding="utf-8")
            cfg = {"audio": "a.mp3", "paroles": "a.txt"}
            self.assertEqual(cli._sig(p, cfg, "paroles"), cli._sig(p, {**cfg, "langue": "fr"}, "paroles"))
            self.assertNotEqual(cli._sig(p, cfg, "paroles"), cli._sig(p, {**cfg, "langue": "en"}, "paroles"))

    def test_erreurs_du_serveur_dans_la_langue_de_la_page(self):
        import http.client
        import json as js
        import threading
        from clip.web import Handler, Server
        srv = Server(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            for lg, attendu in (("en", "Project not found"), ("fr", "Projet introuvable")):
                c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
                c.request("GET", "/api/projet/zz_absent_zz", headers={"X-Lang": lg})
                self.assertIn(attendu, js.loads(c.getresponse().read())["erreur"])
                c.close()
        finally:
            srv.shutdown()
            srv.server_close()

    def test_chemins_et_ouverture_restent_dans_le_projet(self):
        # réglages de chemin : relatifs au projet seulement; « Ouvrir » : dossiers et vidéos seulement
        import http.client
        import json as js
        import threading
        from clip import web
        with tempfile.TemporaryDirectory() as d:
            old = web.PROJETS
            web.PROJETS = Path(d)
            (Path(d) / "essai").mkdir()
            (Path(d) / "essai" / "projet.json").write_text("{}", encoding="utf-8")
            (Path(d) / "essai" / "outil.bat").write_text("echo", encoding="utf-8")
            srv = web.Server(("127.0.0.1", 0), web.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()

            def post(url, body=b""):
                c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
                c.request("POST", url, body=body)
                r = c.getresponse()
                out = r.status, js.loads(r.read() or b"{}")
                c.close()
                return out
            try:
                for v in ("../autre", "C:/Windows", "/etc", "planches/../../x"):
                    self.assertEqual(post("/api/projet/essai/config", js.dumps({"planches": v}).encode())[0], 400, v)
                self.assertEqual(post("/api/projet/essai/config", js.dumps({"solos_list": ["../x.png"]}).encode())[0],
                                 400)
                self.assertEqual(post("/api/projet/essai/config", js.dumps({"planches": "mes_planches"}).encode())[0],
                                 200)
                self.assertEqual(post("/api/projet/essai/ouvrir?chemin=outil.bat")[0], 400)
                self.assertEqual(post("/api/projet/essai/ouvrir?chemin=../..")[0], 400)
                self.assertEqual(post("/api/projet/essai/ouvrir?chemin=build/absente.mp4")[0], 400)
                self.assertEqual(post("/api/projet/essai/reveler?nom=../projet.json")[0], 400)
                self.assertEqual(post("/api/projet/essai/restaurer?f=../../projet.json")[0], 400)
                self.assertEqual(post("/api/projet/ESSAI/config", b"{}")[0], 400)          # nom exact du dossier
                # dépôt : le nom reçu est réduit au nom de fichier, écrit dans le projet
                self.assertEqual(post("/api/projet/essai/upload?type=paroles&nom=..%2F..%2Fpiege.txt", b"la")[0], 200)
                self.assertTrue((Path(d) / "essai" / "piege.txt").exists())
                self.assertFalse((Path(d).parent / "piege.txt").exists())
                self.assertEqual(post("/api/projet/essai/upload?type=planche&id=p1&nom=a.png", b"x")[0], 200)
                self.assertEqual(post("/api/projet/essai/upload?type=planche&id=p1&nom=a.jpg", b"x")[0], 200)
                self.assertEqual(sorted(f.name for f in (Path(d) / "essai" / "mes_planches").iterdir()), ["P1.jpg"])

                def get(url):
                    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
                    c.request("GET", url)
                    r = c.getresponse()
                    out = r.status, r.getheader("Content-Type"), r.read()
                    c.close()
                    return out
                st, ct, body = get("/fichier/essai/piege.txt")
                self.assertEqual((st, ct, body), (200, "text/plain; charset=utf-8", b"la"))
                self.assertEqual(get("/fichier/essai/mes_planches/P1.jpg")[1], "image/jpeg")
                self.assertEqual(get("/fichier/essai/outil.bat")[1], "application/octet-stream")
                self.assertIn(get("/fichier/essai/..%2F..%2Fx")[0], (403, 404))
                self.assertEqual(get("/api/projet/ESSAI")[0], 404)                       # nom exact du dossier
            finally:
                srv.shutdown()
                srv.server_close()
                web.PROJETS = old


class Ecriture(unittest.TestCase):
    def test_ecriture_atomique(self):
        # projet.json & co : une écriture interrompue laisse l'ancienne version intacte
        from unittest import mock
        from clip import ecrire
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "projet.json"
            ecrire(f, '{"v": 1}')
            ecrire(f, '{"v": 2}')
            self.assertEqual(f.read_text(encoding="utf-8"), '{"v": 2}')
            self.assertEqual([x.name for x in Path(d).iterdir()], ["projet.json"])   # pas de .tmp qui traîne
            with mock.patch("os.replace", side_effect=OSError("coupure")):
                with self.assertRaises(OSError):
                    ecrire(f, '{"v": 3}')
            self.assertEqual(f.read_text(encoding="utf-8"), '{"v": 2}')


class Console(unittest.TestCase):
    def test_sortie_redirigee_cp1252(self):
        # sortie redirigée sous Windows (cp1252) : « → » ne doit pas faire planter la commande
        import os
        import subprocess
        import sys
        r = subprocess.run([sys.executable, "-c", "import clip; print('vers → 1.0 s ✨')"], capture_output=True,
                           env={**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
        self.assertEqual(r.returncode, 0, r.stderr)


class Claude(unittest.TestCase):
    def test_appel_allege(self):
        # appel sans outils, connecteurs ni réglages (surcoût de ~34 000 tokens par appel sinon)
        from clip.ai import OPTIONS
        for opt in ("-p", "--tools", "--strict-mcp-config", "--setting-sources", "--system-prompt"):
            self.assertIn(opt, OPTIONS)
        self.assertEqual(OPTIONS[OPTIONS.index("--tools") + 1], "")
        self.assertNotIn("--bare", OPTIONS)        # ignorerait la connexion par abonnement


class Web(unittest.TestCase):
    def test_arguments_filtres(self):
        from clip.web import ARG_VALUES
        self.assertTrue(ARG_VALUES["--ids"].match("p1_c2,solo3"))
        self.assertFalse(ARG_VALUES["--ids"].match("p1_c2;del"))
        self.assertFalse(ARG_VALUES["--out"].match("..\\x.mp4"))
        self.assertTrue(ARG_VALUES["--out"].match("aveuglement_v2.mp4"))

    def test_requetes_etrangeres_refusees(self):
        # une page web d'un autre site ne doit pas piloter le serveur local (Origin, rebinding DNS)
        import http.client
        import threading
        from clip.web import Handler, Server
        srv = Server(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]

        def statut(methode, entetes):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request(methode, "/api/version", body=b"{}" if methode == "POST" else None, headers=entetes)
            code = c.getresponse().status
            c.close()
            return code
        try:
            self.assertEqual(statut("GET", {}), 200)
            self.assertEqual(statut("GET", {"Host": f"localhost:{port}"}), 200)
            self.assertEqual(statut("GET", {"Host": f"pirate.example:{port}"}), 403)
            self.assertEqual(statut("POST", {"Origin": "https://pirate.example"}), 403)
            self.assertNotEqual(statut("POST", {"Origin": f"http://127.0.0.1:{port}"}), 403)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
