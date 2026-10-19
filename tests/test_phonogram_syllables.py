import json
import tempfile
import unittest
from pathlib import Path

from scripts.phonogram_base import syllables
from scripts.phonogram_base.analysis import analyze
from scripts.phonogram_base.inputs import definitions
from scripts.phonogram_base.models import AnalysisStatus, Reason
from scripts.phonogram_base.registry import Registry

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
PHONES = set(json.loads((ROOT / "data/mappings/arpabet_to_og.json").read_text())["arpabet_to_og"])
HAPPY = ("happy", ["HH", "AE1", "P", "IY0"], [["h", "HH"], ["a", "AE"], ["pp", "P"], ["y", "IY"]])
BEING = ("being", ["B", "IY1", "IH0", "NG"], [["b", "B"], ["e", "IY"], ["i", "IH"], ["ng", "NG"]])
APPLE = ("apple", ["AE1", "P", "AH0", "L"], [["a", "AE"], ["pp", "P"], ["l", "AH|L"], ["e", None]])


def run(case: tuple, table: dict | None = None):
    word, pronunciation, alignment = case
    registry = Registry(definitions(ROOT), {})
    return analyze(word, pronunciation, alignment, 1, 1.0, registry, SETTINGS, PHONES, table)


def base_syllables(result) -> list[int]:
    return [item.syllable for item in result.occurrences if item.layer == SETTINGS["layers"]["base"]]


class PhoneticTableTests(unittest.TestCase):
    def test_table_lines_become_syllables_and_variants_are_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.rep"
            path.write_text("## comment\nHAPPY  HH AE1 - P IY0\nREALLY  R IH1 - L IY0\nREALLY(2)  R IY1 - L IY0\n")
            table = syllables.load_table(path, SETTINGS)
        self.assertEqual(table["happy"], [[["HH", "AE1"], ["P", "IY0"]]])
        self.assertEqual(len(table["really"]), 2)

    def test_table_must_match_the_pronunciation_being_analysed(self):
        table = {"happy": [[["HH", "AE1"], ["P", "IY0"]]]}
        self.assertIsNotNone(syllables.from_table(HAPPY[1], table["happy"], SETTINGS))
        self.assertIsNone(syllables.from_table(["HH", "EH1", "P", "IY0"], table["happy"], SETTINGS))

    def test_rule_fallback_gives_the_last_consonant_to_the_next_syllable(self):
        result = syllables.by_nuclei(["S", "AH1", "M", "TH", "IH0", "NG"], SETTINGS)
        self.assertEqual([(item.phone_start, item.phone_end) for item in result], [(0, 3), (3, 6)])


class SyllableBehaviourTests(unittest.TestCase):
    def test_a_phonogram_crossing_the_written_break_no_longer_excludes_the_word(self):
        result = run(HAPPY)
        self.assertEqual(result.status, AnalysisStatus.Consistent)
        self.assertEqual(result.warnings, [Reason.Boundary])
        self.assertEqual(base_syllables(result), [0, 0, 1, 1])

    def test_written_syllable_count_disagreement_is_a_warning(self):
        result = run(BEING)
        self.assertEqual(result.status, AnalysisStatus.Consistent)
        self.assertIn(Reason.Count, result.warnings)
        self.assertEqual(base_syllables(result), [0, 0, 1, 1])

    def test_syllables_come_from_the_table_when_it_matches(self):
        table = {"happy": [[["HH", "AE1", "P"], ["IY0"]]]}
        result = run(HAPPY, table)
        self.assertEqual(base_syllables(result), [0, 0, 0, 1])
        self.assertEqual({item.source for item in result.phonetic_syllables}, {SETTINGS["syllables"]["source_table"]})

    def test_silent_letter_joins_the_previous_syllable(self):
        result = run(APPLE)
        self.assertEqual(result.occurrences[-1].phones, [])
        self.assertEqual(base_syllables(result)[-1], base_syllables(result)[-2])

    def test_phones_are_still_covered_exactly_once_by_the_syllables(self):
        result = run(HAPPY)
        covered = [phone for item in result.phonetic_syllables for phone in range(item.phone_start, item.phone_end)]
        self.assertEqual(covered, list(range(len(HAPPY[1]))))

    def test_syllable_problems_never_appear_as_blocking_reasons(self):
        for case in (HAPPY, BEING, APPLE):
            self.assertTrue({Reason.Boundary, Reason.Count, Reason.Syllables}.isdisjoint(run(case).reasons))

    def test_a_real_pronunciation_conflict_still_excludes(self):
        word, _, alignment = HAPPY
        result = run((word, ["P", "AO1", "R", "T", "S", "IY0"], alignment))
        self.assertEqual(result.status, AnalysisStatus.Excluded)
        self.assertIn(Reason.Pronunciation, result.reasons)


if __name__ == "__main__":
    unittest.main()
