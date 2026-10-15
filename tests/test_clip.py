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
