import importlib.util
import io
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "capturer_sources_live.py"
spec = importlib.util.spec_from_file_location("capturer_sources_live", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Reponse:
    status = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def __init__(self, url):
        self.url = url
        self.fp = io.BytesIO(b"<html>fiction</html>")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fp.close()

    def geturl(self):
        return self.url

    def read(self, n):
        return self.fp.read(n)


class CapturerSourcesTests(unittest.TestCase):
    def test_source_publique_capturee_sans_extraction(self):
        doc = {"match_id": "fictif", "checkpoint": "SONDE_RESEAU", "urls": [
            {"source": "sportsmole", "url": "https://www.sportsmole.co.uk/football/test"},
            {"source": "xpertstats", "url": "https://xpertstats.com/test"}]}
        def fake_open(req, timeout):
            self.assertEqual(timeout, module.TIMEOUT)
            return Reponse(req.full_url)
        out = module.capturer(doc, ouvrir=fake_open, au=datetime(2026, 11, 16, tzinfo=timezone.utc))
        self.assertEqual([r["statut"] for r in out], ["HTTP_OK", "HTTP_OK"])
        self.assertEqual(out[0]["extraction_sportive"], "NON_EFFECTUEE")
        self.assertEqual(out[0]["capture_le"], "2026-11-16T00:00:00+00:00")
        self.assertTrue(out[0]["sha256"])

    def test_mauvaise_source_ou_secret_refuse_avant_http(self):
        for url in ("http://sportsmole.co.uk/", "https://evil.example.com/test",
                    "https://www.sportsmole.co.uk/?token=secret",
                    "https://www.sportsmole.co.uk/?sessionid=secret",
                    "https://www.sportsmole.co.uk/?id=123#secret"):
            with self.subTest(url=url):
                doc = {"match_id": "fictif", "checkpoint": "SONDE_RESEAU", "urls": [
                    {"source": "sportsmole", "url": url}]}
                with mock.patch.object(module.urllib.request, "urlopen") as req, self.assertRaises(ValueError):
                    module.capturer(doc)
                req.assert_not_called()

    def test_http_erreur_preservee_sans_fausse_reussite(self):
        doc = {"match_id": "fictif", "checkpoint": "SONDE_RESEAU", "urls": [
            {"source": "180score", "url": "https://180score.com/test"}]}
        def fail(*_args, **_kwargs):
            raise TimeoutError("timeout")
        result = module.capturer(doc, ouvrir=fail)
        self.assertEqual(result[0]["statut"], "ERREUR")
        self.assertEqual(result[0]["code_http"], 0)
        self.assertIsNone(result[0]["sha256"])

    def test_controle_exige_match_et_fenetre_reelle(self):
        d = {"match_id": "fictif", "checkpoint": "T+15", "urls": [
            {"source": "180score", "url": "https://180score.com/test"}]}
        with self.assertRaisesRegex(ValueError, "kickoff"):
            module.capturer(d)
        d["kickoff"] = "2026-11-15T20:00:00+01:00"
        with self.assertRaisesRegex(ValueError, "hors fenêtre"):
            module.capturer(d, au=datetime(2026, 11, 16, 12, tzinfo=timezone.utc))
        with mock.patch.object(module, "_ouvrir_public", return_value=Reponse("https://180score.com/test")):
            r = module.capturer(d, au=datetime(2026, 11, 15, 19, 15, tzinfo=timezone.utc))
        self.assertEqual(r[0]["checkpoint"], "T+15")


if __name__ == "__main__":
    unittest.main()
