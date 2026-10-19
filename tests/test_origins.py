import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.aligner.model import Model, SETTINGS as ALIGNER
from scripts.phonogram_base.analysis import origin_reasons
from scripts.phonogram_base.models import Reason
from scripts.word_origins.build import computed_flags, spelled_with_letter_names

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
MODEL = Model.load(ROOT / ALIGNER["model_path"])


class LetterNameTests(unittest.TestCase):
    def test_a_word_said_letter_by_letter_is_detected(self):
        self.assertTrue(spelled_with_letter_names("kgb", ["K", "EY2", "JH", "IY2", "B", "IY1"]))

    def test_an_ordinary_word_is_not(self):
        self.assertFalse(spelled_with_letter_names("us", ["AH1", "S"]))


class OriginExclusionTests(unittest.TestCase):
    def test_letter_name_words_are_excluded(self):
        self.assertEqual(origin_reasons("gps", {"letter_names": True}, SETTINGS), [Reason.Abbreviation])

    def test_a_computed_abbreviation_is_excluded(self):
        self.assertEqual(origin_reasons("etc", {"abbreviation": True}, SETTINGS), [Reason.Abbreviation])

    def test_loanwords_and_unusual_spellings_are_flagged_but_not_excluded(self):
        flags = {"loan": ["Italian"], "unusual_spelling": "cc > CH"}
        self.assertEqual(origin_reasons("gucci", flags, SETTINGS), [])

    def test_unflagged_words_are_kept(self):
        self.assertEqual(origin_reasons("cat", {}, SETTINGS), [])


class ComputedFlagTests(unittest.TestCase):
    def test_a_short_word_that_needs_an_unseen_unit_is_an_abbreviation(self):
        flags = computed_flags("xml", ["EH1", "K", "S", "EH1", "M", "EH1", "L"], MODEL)
        self.assertTrue(flags.get("abbreviation") or flags.get("letter_names"))

    def test_a_regular_word_has_no_flags(self):
        self.assertEqual(computed_flags("cat", ["K", "AE1", "T"], MODEL), {})

    def test_a_rare_unit_is_reported_as_unusual_spelling(self):
        flags = computed_flags("czar", ["Z", "AA1", "R"], MODEL)
        self.assertIn("cz", flags.get("unusual_spelling", ""))


if __name__ == "__main__":
    unittest.main()


class LetterNamePluralTests(unittest.TestCase):
    def test_plural_initialisms_are_detected(self):
        self.assertTrue(spelled_with_letter_names("cds", ["S", "IY2", "D", "IY1", "Z"]))

    def test_alternate_letter_names_are_accepted(self):
        self.assertTrue(spelled_with_letter_names("cgi", ["S", "IY2", "G", "IY2", "AY1"]))

    def test_a_plain_s_word_is_not_a_letter_word(self):
        self.assertFalse(spelled_with_letter_names("ads", ["AE1", "D", "Z"]))


class SilentContextTests(unittest.TestCase):
    def test_a_silent_letter_in_an_unseen_context_is_flagged(self):
        flags = computed_flags("nguyen", ["N", "UW0", "Y", "EH1", "N"], MODEL, None, Counter({("g", "n"): 40}))
        self.assertIn("g silent after n", flags["unusual_spelling"])

    def test_a_familiar_silent_context_is_not(self):
        flags = computed_flags("sign", ["S", "AY1", "N"], MODEL, None, Counter({("g", "n"): 40, ("i", "g"): 40}))
        self.assertNotIn("silent", flags.get("unusual_spelling", ""))
