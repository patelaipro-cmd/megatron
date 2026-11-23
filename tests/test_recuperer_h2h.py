import unittest
from scripts.recuperer_h2h import equivalent, retrieve

class H2HTests(unittest.TestCase):
    def test_both_venues_and_date_cutoff(self):
        rows = [
            {"date": "2026-01-01", "home": "Everton", "away": "Brentford", "score": "1-2"},
            {"date": "2025-01-01", "home": "Brentford", "away": "Everton", "score": "0-0"},
            {"date": "2027-01-01", "home": "Everton", "away": "Brentford", "score": "3-1"},
        ]
        result = retrieve("Brentford", "Everton", "2026-11-23", rows, {})
        self.assertEqual([r["score"] for r in result], ["1-2", "0-0"])

    def test_gender_separation(self):
        self.assertFalse(equivalent("Bayern Munich Women", "Bayern Munich", {}))
        self.assertFalse(equivalent("Hoffenheim Women", "Hoffenheim", {}))

    def test_alias(self):
        group = {"manutd", "manunited", "manchesterunited"}
        aliases = {name: group for name in group}
        self.assertTrue(equivalent("Man United", "Manchester United", aliases))

if __name__ == "__main__":
    unittest.main()
