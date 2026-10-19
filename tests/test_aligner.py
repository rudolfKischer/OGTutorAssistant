import json
import unittest
from pathlib import Path

from scripts.aligner.model import Model, SETTINGS
from scripts.aligner.viterbi import align

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {
    ("p", ("P",)): 900, ("r", ("R",)): 900, ("o", ("AA",)): 300, ("b", ("B",)): 800, ("a", ("AH",)): 500,
    ("l", ("L",)): 900, ("y", ("IY",)): 400, ("ob", ("AA",)): 2, ("a", ("B", "AH")): 1, ("e", ()): 900,
    ("d", ("D",)): 800, ("d", ()): 30, ("ee", ("IY",)): 200, ("e", ("IY",)): 100,
}


def text(aligned) -> str:
    return " ".join(f"{letters}>{'+'.join(phones) or '-'}" for letters, phones in aligned.units)


class ViterbiTests(unittest.TestCase):
    def setUp(self):
        self.model = Model(COUNTS)

    def test_a_phone_goes_to_the_letter_that_usually_carries_it(self):
        aligned = align("probably", ["P", "R", "AA1", "B", "AH0", "B", "L", "IY2"], self.model)
        self.assertEqual(text(aligned), "p>P r>R o>AA b>B a>AH b>B l>L y>IY")

    def test_a_silent_letter_is_placed_after_the_sounding_one(self):
        aligned = align("dd", ["D"], self.model)
        self.assertEqual(text(aligned), "d>D d>-")

    def test_unseen_letters_still_align_with_a_fallback_unit(self):
        aligned = align("q", ["K"], self.model)
        self.assertEqual(aligned.backoff_units, 1)
        self.assertEqual(aligned.weak_units, ["q"])

    def test_a_letter_can_carry_several_phones_when_nothing_else_fits(self):
        aligned = align("w", ["D", "AH", "B", "AH", "L", "Y", "UW"], self.model)
        self.assertEqual(len(aligned.units), 1)
        self.assertEqual(len(aligned.units[0][1]), 7)

    def test_rare_units_are_reported_as_weak(self):
        aligned = align("ob", ["AA"], self.model)
        self.assertIn("ob", aligned.weak_units)

    def test_every_alignment_rebuilds_the_spelling_and_the_phones(self):
        aligned = align("bleed", ["B", "L", "IY1", "D"], self.model)
        self.assertEqual("".join(letters for letters, _ in aligned.units), "bleed")
        self.assertEqual([phone for _, phones in aligned.units for phone in phones], ["B", "L", "IY", "D"])


@unittest.skipUnless((ROOT / SETTINGS["model_path"]).exists(), "alignment model not built")
class TrainedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Model.load(ROOT / SETTINGS["model_path"])

    def check(self, word: str, phones: list[str], expected: str):
        self.assertEqual(text(align(word, phones, self.model)), expected)

    def test_shifted_phones_found_in_the_source_alignment_are_corrected(self):
        self.check("probably", ["P", "R", "AA1", "B", "AH0", "B", "L", "IY2"], "p>P r>R o>AA b>B a>AH b>B l>L y>IY")
        self.check("are", ["AA1", "R"], "a>AA r>R e>-")
        self.check("coombe", ["K", "UW1", "M", "B"], "c>K oo>UW m>M b>B e>-")
        self.check("cannes", ["K", "AE1", "N", "Z"], "c>K a>AE nn>N e>- s>Z")

    def test_an_r_vowel_stays_with_its_letters(self):
        self.check("whorl", ["W", "ER1", "L"], "w>W h>- or>ER l>L")

    def test_a_dropped_consonant_leaves_the_letter_silent_without_moving_sounds(self):
        self.check("fifth", ["F", "IH1", "TH"], "f>F i>IH f>- th>TH")


if __name__ == "__main__":
    unittest.main()


class HyphenTests(unittest.TestCase):
    def test_a_hyphen_always_separates_words_and_carries_no_sound(self):
        from scripts.aligner.words import align_word
        aligned = align_word("t-shirt", ["T", "IY1", "SH", "ER1", "T"], Model.load(ROOT / SETTINGS["model_path"]))
        dashes = [units for letters, units in aligned.units if letters == "-"]
        self.assertEqual(dashes, [()])
        self.assertNotIn("-", [letters for letters, _ in aligned.units if letters != "-" and "-" in letters])

    def test_each_word_is_aligned_with_its_own_sounds(self):
        from scripts.aligner.words import align_word
        aligned = align_word("to-do", ["T", "UW1", "D", "UW1"], Model.load(ROOT / SETTINGS["model_path"]))
        self.assertEqual([letters for letters, _ in aligned.units], ["t", "o", "-", "d", "o"])
