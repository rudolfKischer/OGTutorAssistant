import json
import tempfile
import unittest
from pathlib import Path

from scripts.word_origins.definitions import ABBREVIATION_START, ACRONYM_WORDS, name_kinds, name_origins, profile
from scripts.word_origins.forms import base_forms
from scripts.word_origins.merge import add_kaikki, demote, drop_short_word_flags, origin_name, add_proper_nouns, add_wiktionary

LISTS = {"surname": ["baker", "dembowski", "hauls"], "first_name": ["aaron"], "place": ["paris"], "wordnet_proper": ["paris"],
         "wordnet_acronym": ["nato", "all"], "wordnet_common": ["baker", "haul", "all"]}
CATEGORIES = {"loan:French": {"members": ["ballet"]}, "acronym": {"members": ["nasa", "all"]}}


def repository() -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "data/sources").mkdir(parents=True)
    (root / "data/sources/name-lists.json").write_text(json.dumps({"lists": LISTS}))
    (root / "data/sources/wiktionary-origin-categories.json").write_text(json.dumps({"categories": CATEGORIES}))
    return root


class FormTests(unittest.TestCase):
    def test_inflections_reduce_to_stems(self):
        self.assertTrue({"haul", "hauls"} <= base_forms("hauls"))
        self.assertIn("carry", base_forms("carries"))

    def test_short_words_are_not_stripped_to_nothing(self):
        self.assertEqual(base_forms("is"), {"is"})


class ProperNounTests(unittest.TestCase):
    def setUp(self):
        self.words: dict = {}
        add_proper_nouns(self.words, repository(), ["baker", "dembowski", "hauls", "aaron", "paris", "cat"])

    def test_name_only_words_are_flagged_with_their_kinds(self):
        self.assertEqual(self.words["dembowski"]["proper_noun"], ["surname"])
        self.assertEqual(self.words["paris"]["proper_noun"], ["place", "wordnet_proper"])

    def test_words_that_are_also_ordinary_english_are_not(self):
        self.assertNotIn("baker", self.words)
        self.assertNotIn("hauls", self.words)
        self.assertNotIn("cat", self.words)

    def test_acronyms_from_wordnet_skip_common_words(self):
        self.assertEqual(self.words["nato"]["acronym"], ["wordnet"])
        self.assertNotIn("all", self.words)


class WiktionaryTests(unittest.TestCase):
    def test_loans_and_initialisms_are_flagged_except_common_words(self):
        words: dict = {}
        add_wiktionary(words, repository())
        self.assertEqual(words["ballet"]["loan"], ["French"])
        self.assertEqual(words["nasa"]["acronym"], ["acronym"])
        self.assertNotIn("all", words)


class KaikkiTests(unittest.TestCase):
    def setUp(self):
        self.root = repository()
        found = {"words": {"ftp": {"lower": False, "name": True, "acronym": ["initialism"], "loan": []},
                           "hauls": {"lower": True, "name": False, "acronym": [], "loan": []},
                           "ballet": {"lower": True, "name": False, "acronym": [], "loan": ["fr", "la"]}}}
        (self.root / "data/sources/kaikki-flags.json").write_text(json.dumps(found))

    def test_dictionary_evidence_flags_names_and_acronyms_and_languages(self):
        words: dict = {"hauls": {"proper_noun": ["surname"]}}
        add_kaikki(words, self.root)
        self.assertEqual(words["ftp"], {"proper_noun": ["wiktionary"], "acronym": ["initialism"]})
        self.assertEqual(words["ballet"]["loan"], ["French"])
        self.assertNotIn("proper_noun", words["hauls"])


class DefinitionNameTests(unittest.TestCase):
    def test_a_first_sense_that_is_a_surname_flags_the_word(self):
        self.assertEqual(name_kinds(["A surname from Scottish Gaelic.", "An unincorporated community in Atascosa County, Texas, United States."]),
                         ["place", "surname"])

    def test_one_ordinary_sense_means_the_word_is_not_name_only(self):
        self.assertEqual(name_kinds(["A surname.", "A person who bakes."]), [])
        self.assertEqual(profile(["A surname.", "A person who bakes."]), (["surname"], True))

    def test_places_need_a_capitalised_location(self):
        self.assertEqual(name_kinds(["The state induced by hypnotic methods of Mesmer."]), [])
        self.assertEqual(name_kinds(["The capital and largest city of France."]), ["place"])

    def test_given_names_are_recognised(self):
        self.assertEqual(name_kinds(["A female given name from English."]), ["given_name"])


class MixedNameTests(unittest.TestCase):
    def test_words_with_an_ordinary_sense_move_to_the_mixed_flag(self):
        words = {"hauls": {"proper_noun": ["surname", "wiktionary"]}}
        demote(words, "hauls", [])
        self.assertEqual(words["hauls"], {"name_sense": ["surname"]})


class AbbreviationDefinitionTests(unittest.TestCase):
    def test_abbreviation_and_acronym_wording_is_detected(self):
        self.assertTrue(ABBREVIATION_START.search("Abbreviation of August."))
        self.assertTrue(ACRONYM_WORDS.search("Initialism of driving while impaired."))
        self.assertFalse(ACRONYM_WORDS.search("A person who bakes."))


class ShortWordTests(unittest.TestCase):
    def test_letters_and_two_letter_words_carry_no_loan_flag(self):
        words = {"o": {"loan": ["Hokkien"]}, "de": {"loan": ["French"]}, "ballet": {"loan": ["French"]}, "y": {"unusual_spelling": "y > W+AY"}}
        drop_short_word_flags(words)
        self.assertNotIn("loan", words["o"])
        self.assertNotIn("loan", words["de"])
        self.assertIn("loan", words["ballet"])
        self.assertNotIn("unusual_spelling", words["y"])

    def test_language_codes_map_to_names_or_are_dropped(self):
        self.assertEqual(origin_name("es-MX"), "Spanish")
        self.assertEqual(origin_name("nan-hbl"), "Hokkien")
        self.assertIsNone(origin_name("egy"))
        self.assertIsNone(origin_name("zzz"))


class NameOriginTests(unittest.TestCase):
    def test_a_surname_origin_language_is_read_from_the_definition(self):
        self.assertEqual(name_origins(["A Vietnamese surname."]), ["Vietnamese"])
        self.assertEqual(name_origins(["A surname from Scottish Gaelic."]), ["Scottish Gaelic"])

    def test_english_origins_and_non_name_senses_are_ignored(self):
        self.assertEqual(name_origins(["An English surname."]), [])
        self.assertEqual(name_origins(["A word from German meaning a thing."]), [])
