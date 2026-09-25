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

    def test_entete_sans_storyboard(self):
        self.assertNotIn("storyboard", prompts.HEADER.lower())


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


class Import(unittest.TestCase):
    def test_modules(self):
        # tous les modules s'importent (erreur de syntaxe dans un module non testé ailleurs)
        import importlib
        for m in ("render", "effects", "depth", "web", "ai", "publish", "evaluate", "audio", "demandes"):
            importlib.import_module(f"clip.{m}")


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


if __name__ == "__main__":
    unittest.main()
