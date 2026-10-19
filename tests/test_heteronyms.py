import json
import tempfile
import unittest
from pathlib import Path

from scripts.heteronyms import homograph_data, wiktionary_category
from scripts.heteronyms.ipa import to_arpabet
from scripts.heteronyms.wikipedia_table import SOURCE, read as read_table
from scripts.phonogram_base.pronunciations import collect, options_for

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
TABLE = """{| class="wikitable"
|-
! Spelling !! Pronunciation !! Part of speech !! Meaning
|-
|rowspan="2"| lead
| {{IPAc-en|ˈ|l|iː|d}}
|verb
|to guide
|-
| {{IPAc-en|ˈ|l|ɛ|d}}
|noun
|a metal
|}
"""
LEAD = {"spelling": "lead", "senses": [
    {"source": "wikipedia_table", "ipa": "ˈliːd", "part_of_speech": "verb", "meaning": "to guide"},
    {"source": "wikipedia_table", "ipa": "ˈlɛd", "part_of_speech": "noun", "meaning": "a metal"}]}


class IpaTests(unittest.TestCase):
    def test_stress_goes_on_the_following_vowel(self):
        self.assertEqual(to_arpabet("ˈlɛd"), ["L", "EH1", "D"])
        self.assertEqual(to_arpabet("rɪˈkɔːrd"), ["R", "IH0", "K", "AO1", "R", "D"])

    def test_unknown_symbols_are_refused_not_guessed(self):
        self.assertIsNone(to_arpabet("ˈlɸd"))


class SourceParsingTests(unittest.TestCase):
    def test_rowspan_spelling_is_carried_to_every_sense(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / SOURCE["raw_path"]
            path.parent.mkdir(parents=True)
            path.write_text(TABLE)
            senses = read_table(root)["lead"]
        self.assertEqual([(sense.ipa, sense.part_of_speech) for sense in senses], [("ˈliːd", "verb"), ("ˈlɛd", "noun")])

    def test_wiktionary_members_keep_only_plain_lowercase_words(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / wiktionary_category.SOURCE["raw_path"]
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"members": ["lead", "Des Moines", "ha-ha", "101"]}))
            self.assertEqual(wiktionary_category.read(root), ["lead"])

    def test_homograph_data_labels_become_senses(self):
        senses = homograph_data.read(ROOT)["lead"]
        self.assertTrue(any(sense.ipa == "ˈlɛd" and sense.meaning == "material" for sense in senses))


class PronunciationOptionTests(unittest.TestCase):
    def test_unstressed_vowel_quality_is_a_different_pronunciation(self):
        options = collect(["P", "R", "AA1", "JH", "EH0", "K", "T"], [["P", "R", "AA1", "JH", "IH0", "K", "T"]], SETTINGS)
        self.assertEqual(len(options), 2)

    def test_stressed_vowel_difference_is_a_new_pronunciation(self):
        options = collect(["L", "EH1", "D"], [["L", "IY1", "D"]], SETTINGS)
        self.assertEqual([option.source for option in options], ["selected", "cmu"])

    def test_senses_attach_to_the_matching_pronunciation(self):
        options = options_for("lead", ["L", "EH1", "D"], [["L", "IY1", "D"]], LEAD, SETTINGS)
        meanings = {option.ordinal: [sense["meaning"] for sense in option.senses] for option in options}
        self.assertEqual(meanings, {0: ["a metal"], 1: ["to guide"]})

    def test_a_sense_without_a_dictionary_match_adds_an_ipa_pronunciation(self):
        entry = {"spelling": "x", "senses": [{"source": "s", "ipa": "ˈlaɪv", "part_of_speech": "adjective", "meaning": "alive"}]}
        options = options_for("x", ["L", "IH1", "V"], [], entry, SETTINGS)
        self.assertEqual([option.source for option in options], ["selected", "ipa"])


if __name__ == "__main__":
    unittest.main()


class SamePronunciationTests(unittest.TestCase):
    def test_stress_only_difference_is_one_pronunciation(self):
        options = collect(["P", "R", "AA1", "JH", "EH0", "K", "T"], [["P", "R", "AA2", "JH", "EH0", "K", "T"]], SETTINGS)
        self.assertEqual(len(options), 1)

    def test_phones_that_map_to_the_same_sounds_are_one_pronunciation(self):
        options = collect(["T", "IH1", "R"], [["T", "IY1", "R"]], SETTINGS)
        self.assertEqual(len(options), 1)

    def test_regional_differences_are_kept_as_separate_pronunciations(self):
        pairs = [(["W", "AO1", "R", "L"], ["HH", "W", "AO1", "R", "L"]), (["N", "UW1"], ["N", "Y", "UW1"]),
                 (["P", "AO1", "T"], ["P", "AA1", "T"]), (["P", "R", "AA1", "JH", "EH0", "K", "T"], ["P", "R", "AA1", "JH", "IH0", "K", "T"])]
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                self.assertEqual(len(collect(first, [second], SETTINGS)), 2)

    def test_a_sense_ipa_still_attaches_to_a_regional_variant_instead_of_adding_a_new_one(self):
        entry = {"spelling": "x", "senses": [{"source": "s", "ipa": "ˈprɒdʒɪkt", "part_of_speech": "noun", "meaning": "m"}]}
        options = options_for("x", ["P", "R", "AA1", "JH", "EH0", "K", "T"], [], entry, SETTINGS)
        self.assertEqual(len(options), 1)
