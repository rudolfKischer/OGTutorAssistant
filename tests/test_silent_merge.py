import json
import unittest
from pathlib import Path

from scripts.phonogram_base.inputs import definitions, silent_rules
from scripts.phonogram_base.models import Unit
from scripts.phonogram_base.normalize import normalize, split_vowels
from scripts.phonogram_base.registry import Registry
from scripts.phonogram_base.silent_merge import merge_silent

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
MERGES, SPLITS, SUFFIXES = silent_rules(ROOT, SETTINGS)


def unit(spelling: str, start: int, phone: str | None, position: int) -> Unit:
    phones = [phone] if phone else []
    return Unit(spelling, phones, start, start + len(spelling), position, position + len(phones))


def build(spellings: list[tuple[str, str | None]]) -> list[Unit]:
    items, start, position = [], 0, 0
    for spelling, phone in spellings:
        items.append(unit(spelling, start, phone, position))
        start += len(spelling)
        position += 1 if phone else 0
    return items


class SilentMergeTests(unittest.TestCase):
    def test_a_doubled_consonant_becomes_one_unit_and_keeps_its_phone(self):
        merged, _ = merge_silent(build([("s", "S"), ("o", "AA"), ("r", "R"), ("r", None), ("y", "IY")]), MERGES, set(), SUFFIXES)
        self.assertEqual([(item.spelling, item.phones) for item in merged], [("s", ["S"]), ("o", ["AA"]), ("rr", ["R"]), ("y", ["IY"])])
        self.assertEqual((merged[2].start, merged[2].end), (2, 4))

    def test_a_silent_letter_can_merge_into_the_next_unit(self):
        merged, _ = merge_silent(build([("c", "K"), ("a", "AO"), ("ll", "L"), ("e", None), ("d", "D")]), MERGES, set(), SUFFIXES)
        self.assertEqual([item.spelling for item in merged], ["c", "a", "ll", "ed"])
        self.assertEqual(merged[3].phones, ["D"])

    def test_an_ed_ending_wins_over_an_r_controlled_ending(self):
        items = build([("s", "S"), ("o", "AO"), ("a", None), ("r", "R"), ("e", None), ("d", "D")])
        merged, _ = merge_silent(items, MERGES, set(), SUFFIXES)
        self.assertEqual([item.spelling for item in merged][-2:], ["ar", "ed"])

    def test_two_silent_letters_can_join_the_next_sounding_unit(self):
        merged, _ = merge_silent(build([("b", "B"), ("e", None), ("a", None), ("u", "Y")]), MERGES, set(), SUFFIXES)
        self.assertEqual([item.spelling for item in merged], ["b", "eau"])

    def test_an_r_controlled_ending_is_formed_from_three_units(self):
        merged, _ = merge_silent(build([("a", "AA"), ("r", "R"), ("e", None)]), MERGES, set(), SUFFIXES)
        self.assertEqual([(item.spelling, item.phones) for item in merged], [("are", ["AA", "R"])])

    def test_unlisted_combinations_stay_silent(self):
        merged, _ = merge_silent(build([("h", "HH"), ("a", "AE"), ("q", None)]), MERGES, set())
        self.assertEqual(len(merged), 3)

    def test_protected_units_are_never_merged(self):
        items = build([("m", "M"), ("a", "EY"), ("k", "K"), ("e", None)])
        merged, locked = merge_silent(items, MERGES, {1, 3})
        self.assertEqual([item.spelling for item in merged], ["m", "a", "k", "e"])
        self.assertEqual(locked, {1, 3})


class SplitVowelTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(definitions(ROOT), {}, MERGES, SPLITS, SUFFIXES)

    def test_a_silent_e_inside_a_word_forms_a_split_spelling(self):
        items = build([("s", "S"), ("a", "EY"), ("f", "F"), ("e", None), ("l", "L"), ("y", "IY")])
        occurrences, consumed = split_vowels(items, self.registry, "base")
        self.assertEqual([item.pattern.spelling for item in occurrences], ["a_e"])
        self.assertEqual(consumed, {1, 3})

    def test_an_undefined_split_spelling_is_still_recognised(self):
        items = build([("h", "HH"), ("a", "AE"), ("v", "V"), ("e", None)])
        occurrences, _ = split_vowels(items, self.registry, "base")
        self.assertEqual([item.pattern.spelling for item in occurrences], ["a_e"])

    def test_a_vowel_letter_between_is_not_a_split_spelling(self):
        items = build([("y", "Y"), ("i", "IY"), ("e", None), ("l", "L"), ("d", "D")])
        occurrences, _ = split_vowels(items, self.registry, "base")
        self.assertEqual(occurrences, [])

    def test_every_letter_is_covered_once_after_grouping(self):
        items = build([("s", "S"), ("o", "AH"), ("m", "M"), ("e", None)])
        occurrences = normalize(items, self.registry, "base")
        covered = sorted(i for item in occurrences for span in item.spans for i in range(span.start, span.end))
        self.assertEqual(covered, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
