import json
from pathlib import Path
import sys
import unittest

from rmf_load_lab import audit, validate_scenarios


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class LoadLabTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = json.loads((FIXTURES / "scenarios.json").read_text())
        self.command = [sys.executable, str(FIXTURES / "fake_bidder.py"), "{scenario}"]

    def test_example_three_languages(self):
        for locale in ("fr", "en", "es"):
            report = audit(self.scenarios[:1], self.command, locale)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(len(report["scenarios"][0]["runs"]), 3)
            self.assertGreater(report["scenarios"][0]["peak_rss_mb"], 0)

    def test_rejection_fails(self):
        command = [sys.executable, "-c", "import json; print(json.dumps({'accepted': False}))", "{scenario}"]
        report = audit(self.scenarios[:1], command)
        self.assertEqual(report["status"], "fail")
        self.assertIn("rejected", {item["code"] for item in report["findings"]})

    def test_duplicate_name_invalid(self):
        with self.assertRaises(ValueError):
            validate_scenarios([self.scenarios[0], self.scenarios[0]])


if __name__ == "__main__":
    unittest.main()
