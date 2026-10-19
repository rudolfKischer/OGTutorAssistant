import json
import unittest
from pathlib import Path

from db_builder.phoneme_converter import convert_phoneme_sequence
from scripts.phonogram_base.inputs import definitions
from scripts.phonogram_base.models import PatternKind
from scripts.phonogram_base.normalize import normalize, sounds, units
from scripts.phonogram_base.registry import Registry
from scripts.phonogram_base.sound_ids import canonical_sounds


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "data/fixtures/phonogram-long-u-cases.json").read_text())


class SoundIdentityTests(unittest.TestCase):
    def test_atomic_identity_preserves_legacy_converter(self):
        self.assertEqual(convert_phoneme_sequence(["Y", "UW1"])[0][1], "long_u")
        self.assertEqual(sounds(["Y", "UW1"]), ["y", "long_oo"])
        self.assertEqual(sounds(["UW1"]), ["long_oo"])
        expanded = canonical_sounds(["long_u"])
        self.assertEqual(canonical_sounds(expanded), expanded)

    def test_aliases_share_identity_and_keep_definition_ids(self):
        registry = Registry(definitions(ROOT), {})
        for spelling in {case["spelling"] for case in CASES}:
            fused = registry.pattern(spelling, ["long_u"])
            expanded = registry.pattern(spelling, ["y", "long_oo"])
            self.assertIs(fused, expanded)
            expected = [item.id for item in definitions(ROOT) if item.spelling == spelling
                        and item.sounds == ["y", "long_oo"] and item.kind == PatternKind.Phonogram]
            self.assertTrue(expected)
            self.assertEqual(fused.definition_ids, expected)

    def test_real_alignments_preserve_letter_and_phone_spans(self):
        for case in CASES:
            with self.subTest(word=case["word"]):
                registry = Registry(definitions(ROOT), {})
                items = units(case["alignment"], case["pronunciation"], True)
                occurrences = normalize(items, registry, "base")
                pair = next(item for item in occurrences if item.pattern.spelling == case["spelling"])
                self.assertEqual(pair.pattern.sounds, ["y", "long_oo"])
                self.assertEqual(pair.phones, ["Y", next(p for p in case["pronunciation"] if p.startswith("UW"))])
                self.assertEqual(pair.phone_end - pair.phone_start, 2)
                positions = [i for item in occurrences for span in item.spans for i in range(span.start, span.end)]
                self.assertEqual(sorted(positions), list(range(len(case["word"]))))
                ordered = sorted(occurrences, key=lambda item: item.phone_start)
                self.assertEqual([p for item in ordered for p in item.phones], case["pronunciation"])
                if case["word"] == "cute":
                    self.assertEqual([(span.start, span.end) for span in pair.spans], [(1, 2), (3, 4)])


if __name__ == "__main__":
    unittest.main()
