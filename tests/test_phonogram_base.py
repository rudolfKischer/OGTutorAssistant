import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.phonogram_base.analysis import analyze
from scripts.phonogram_base.inputs import definitions
from scripts.phonogram_base.models import AnalysisStatus, Reason
from scripts.phonogram_base.registry import Registry
from scripts.phonogram_base.storage import BaseWriter, read_query


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/fixtures/phonogram-base-cases.json").read_text())
SETTINGS = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
PHONES = set(json.loads((ROOT / "data/mappings/arpabet_to_og.json").read_text())["arpabet_to_og"])


def analysis(case: dict):
    registry = Registry(definitions(ROOT), {})
    return analyze(case["word"], case["pronunciation"], case["alignment"], 1, 1.0, registry, SETTINGS, PHONES)


class PhonogramBaseTests(unittest.TestCase):
    def test_regressions_use_positioned_spelling_and_sound_pairs(self):
        for case in CASES:
            with self.subTest(word=case["word"]):
                result = analysis(case)
                self.assertEqual(result.status, AnalysisStatus.Consistent)
                pairs = [(item.pattern.spelling, item.pattern.sounds) for item in result.occurrences]
                for expected in case["expected"]:
                    self.assertIn((expected["spelling"], expected["sounds"]), pairs)

    def test_split_vowel_has_disjoint_letter_positions(self):
        result = analysis(next(case for case in CASES if case["word"] == "make"))
        pair = next(item for item in result.occurrences if item.pattern.spelling == "a_e")
        self.assertEqual([(span.start, span.end) for span in pair.spans], [(1, 2), (3, 4)])
        self.assertEqual(pair.phones, ["EY1"])

    def test_blend_is_an_overlay_and_components_stay_present(self):
        for word, spelling in [("spot", "sp"), ("split", "spl")]:
            result = analysis(next(case for case in CASES if case["word"] == word))
            overlays = [item for item in result.occurrences if item.layer == SETTINGS["layers"]["overlay"]]
            self.assertTrue(any(item.pattern.spelling == spelling for item in overlays))
            base = [item for item in result.occurrences if item.layer == SETTINGS["layers"]["base"]]
            positions = [i for item in base for span in item.spans for i in range(span.start, span.end)]
            self.assertEqual(sorted(positions), list(range(len(word))))

    def test_bad_pronunciation_and_missing_alignment_are_excluded(self):
        case = next(case for case in CASES if case["word"] == "head")
        bad = analysis({**case, "pronunciation": ["P", "AO1", "R", "T", "S"]})
        self.assertEqual(bad.status, AnalysisStatus.Excluded)
        self.assertIn(Reason.Pronunciation, bad.reasons)
        missing = analysis({**case, "alignment": []})
        self.assertIn(Reason.Missing, missing.reasons)
        self.assertFalse(missing.occurrences)

    def test_unsupported_phone_does_not_become_a_phonogram(self):
        case = next(case for case in CASES if case["word"] == "head")
        bad = analysis({**case, "alignment": [["head", "#"]]})
        self.assertIn(Reason.Unknown, bad.reasons)
        self.assertFalse(bad.occurrences)

    def test_word_counts_are_distinct_from_occurrence_counts(self):
        case = next(case for case in CASES if case["word"] == "bob")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "base.sqlite"
            writer = BaseWriter(path)
            try:
                writer.add(analysis(case))
                summary = writer.summarize("test", {}, SETTINGS)
                writer.finish(summary)
            finally:
                writer.close()
            pair = next(row for row in summary.patterns if row.pattern.spelling == "b")
            self.assertEqual(pair.word_count, 1)
            self.assertEqual(pair.occurrence_count, 2)
            self.assertIn("rare", pair.flags)
            words = read_query(path, "pattern-words.sql", (AnalysisStatus.Consistent, pair.pattern.id, 30, 0))
            self.assertEqual([row[0] for row in words], ["bob"])


if __name__ == "__main__":
    unittest.main()
