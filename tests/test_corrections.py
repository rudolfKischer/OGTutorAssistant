import json
import unittest
from pathlib import Path

from scripts.phonogram_base.corrections import Corrections
from scripts.pronunciation_corrections import build as generator

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
INDICA = ["IH1", "D", "AH0", "K", "AH0"]
FIXED = ["IH1", "N", "D", "AH0", "K", "AH0"]
ENTRIES = [
    {"word": "indica", "action": "prefer", "pronunciation": FIXED},
    {"word": "hurricane", "action": "drop", "pronunciation": ["HH", "AH1", "R", "AH0", "K", "EY2", "N", "Z"]},
]


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.corrections = Corrections(ENTRIES, SETTINGS)

    def test_a_preferred_pronunciation_becomes_main_and_the_original_is_kept(self):
        main, others = self.corrections.apply("indica", INDICA, [])
        self.assertEqual(main, FIXED)
        self.assertEqual(others, [INDICA])

    def test_a_dropped_variant_disappears(self):
        first, second = ["HH", "ER1", "AH0", "K", "EY2", "N"], ["HH", "AH1", "R", "AH0", "K", "EY2", "N", "Z"]
        main, others = self.corrections.apply("hurricane", first, [second])
        self.assertEqual((main, others), (first, []))

    def test_other_words_are_untouched(self):
        self.assertEqual(self.corrections.apply("cat", ["K", "AE1", "T"], []), (["K", "AE1", "T"], []))

    def test_the_in_prefix_rule_inserts_the_missing_n(self):
        entries = generator.in_prefix_entries({"indica": INDICA, "index": ["IH1", "N", "D", "EH2", "K", "S"], "inn": ["IH1", "N"]})
        self.assertEqual([(entry["word"], entry["pronunciation"]) for entry in entries], [("indica", FIXED)])

    def test_the_final_z_rule_skips_real_plurals_and_pairs(self):
        entries = generator.extra_z_entries({"citron": [["S", "IH1", "T", "R", "AH0", "N"], ["S", "IH1", "T", "R", "AH0", "N", "Z"]],
                                             "eaux": [["OW1"], ["OW1", "Z"]]})
        self.assertEqual([entry["word"] for entry in entries], ["citron"])


if __name__ == "__main__":
    unittest.main()


class PreferAndDropTests(unittest.TestCase):
    def test_a_wrong_dictionary_entry_is_replaced_and_not_kept_as_an_alternate(self):
        settings = {"pronunciation": {"correction_actions": {"prefer": "prefer", "drop": "drop"}}}
        entries = [{"word": "w", "action": "prefer", "pronunciation": ["A", "B"]}, {"word": "w", "action": "drop", "pronunciation": ["A", "C"]}]
        selected, alternates = Corrections(entries, settings).apply("w", ["A", "C"], [])
        self.assertEqual((selected, alternates), (["A", "B"], []))
