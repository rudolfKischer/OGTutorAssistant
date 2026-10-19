import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.explorer_concepts import builder
from scripts.explorer_concepts.catalog import SETTINGS as EXPLORER, SoundNames, concept_row
from scripts.phonogram_base.analysis import analyze
from scripts.phonogram_base.inputs import definitions
from scripts.phonogram_base.registry import Registry
from scripts.phonogram_base.storage import BaseWriter
from scripts.phonogram_cache.exporter import SETTINGS as CACHE, build as build_cache

ROOT = Path(__file__).resolve().parents[1]
CASES = {case["word"]: case for case in json.loads((ROOT / "data/fixtures/phonogram-base-cases.json").read_text())}
BASE = json.loads((ROOT / "scripts/phonogram_base/settings.json").read_text())
PHONES = set(json.loads((ROOT / "data/mappings/arpabet_to_og.json").read_text())["arpabet_to_og"])
REPLACED = ["vowel_team_ea", "phoneme_short_e"]
KEPT = "closed_syllable"
WORD_IDS = {"head": 1, "steak": 2, "read": 3, "absent": 4}


def analyses():
    registry = Registry(definitions(ROOT), {})
    result = [analyze(word, CASES[word]["pronunciation"], CASES[word]["alignment"], index, 1.0, registry, BASE, PHONES)
              for index, word in enumerate(["head", "steak"])]
    broken = CASES["head"]["alignment"][:-1]
    result.append(analyze("read", CASES["head"]["pronunciation"], broken, 3, 1.0, registry, BASE, PHONES))
    return result


def workspace(root: Path) -> Path:
    mapping = root / CACHE["id_map"]
    mapping.parent.mkdir(parents=True)
    with mapping.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["namespace", "source_id", "action"])
        for source in REPLACED:
            writer.writerow([CACHE["id_map_namespace"], source, CACHE["replaced_action"]])
    cache = root / CACHE["deployed_cache"]
    cache.parent.mkdir(parents=True)
    legacy = {tag: ["head", "steak", "read", "absent"] for tag in REPLACED + [KEPT]}
    cache.write_text(json.dumps({"concept_to_words": legacy, "sight_words": [], "word_frequency_rank": {}}))
    notation = root / EXPLORER["notation_source"]
    notation.parent.mkdir(parents=True)
    entry = {"b": "short e", "h": "/ĕ/", "l": "/ɛ/", "n": "as in bed"}
    notation.write_text(json.dumps({"phonemes": {EXPLORER["notation_prefix"] + "short_e": entry}}))
    return root


def observations(path: Path) -> None:
    writer = BaseWriter(path)
    for item in analyses():
        writer.add(item)
    writer.connection.commit()
    writer.close()


class ExplorerConceptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = workspace(Path(self.directory.name) / "workspace")
        self.database = Path(self.directory.name) / "observations.sqlite"
        observations(self.database)
        self.cache = build_cache(self.root, self.database)

    def tearDown(self):
        self.directory.cleanup()

    def tags(self, word: str) -> set[str]:
        return {tag for tag, words in self.cache["concept_to_words"].items() if word in words}

    def test_sound_wide_tags_are_replaced_by_exact_phonograms(self):
        tags = self.tags("head")
        self.assertIn("phonogram_ea_short_e", tags)
        self.assertTrue(tags.isdisjoint(REPLACED))
        self.assertIn(KEPT, tags)

    def test_other_pronunciation_of_the_same_spelling_is_a_different_tag(self):
        self.assertIn("phonogram_ea_long_a", self.tags("steak"))
        self.assertNotIn("phonogram_ea_short_e", self.tags("steak"))

    def test_excluded_and_unanalysed_words_carry_the_unlearnable_tag(self):
        for word in ["read", "absent"]:
            self.assertIn(CACHE["unresolved_tag"], self.tags(word))
        self.assertNotIn(CACHE["unresolved_tag"], self.tags("head"))

    def test_undefined_patterns_join_their_sound_family_as_rarer_spellings(self):
        names = SoundNames(ROOT)
        tag = CACHE["tag_separator"].join([CACHE["unmodeled_prefix"], "ie", "long_e"])
        row = concept_row(tag, {}, names)
        self.assertEqual(row.kind, EXPLORER["kinds"]["unmodeled"])
        self.assertEqual(row.family, "long_vowels_teams")

    def test_overlay_records_catalog_words_and_positioned_phonograms(self):
        output = Path(self.directory.name) / "overlay.sqlite"
        with mock.patch.object(builder, "word_ids", return_value=WORD_IDS):
            builder.build(ROOT, self.database, output, self.root)
        with sqlite3.connect(output) as connection:
            label = connection.execute("SELECT label FROM concepts WHERE concept = 'phonogram_ea_short_e'").fetchone()
            kinds = dict(connection.execute("SELECT concept, kind FROM concepts WHERE kind = ?", (EXPLORER["kinds"]["unresolved"],)))
            status = connection.execute("SELECT status FROM word_analysis WHERE word_id = 3").fetchone()
            spans = connection.execute("SELECT spans FROM word_phonograms WHERE word_id = 1 AND spelling = 'ea'").fetchone()
            ipa = connection.execute("SELECT ipa FROM sounds WHERE sound = 'short_e'").fetchone()
            syllables = connection.execute("SELECT syllables FROM word_analysis WHERE word_id = 1").fetchone()
            written = connection.execute("SELECT written FROM word_analysis WHERE word_id = 1").fetchone()
            absent = connection.execute("SELECT COUNT(*) FROM word_concepts WHERE word_id = 4").fetchone()
        self.assertEqual(label, ("short e | ea",))
        self.assertIn(CACHE["unresolved_tag"], kinds)
        self.assertEqual(ipa, ("/ɛ/",))
        self.assertEqual(json.loads(syllables[0]), [[0, 3]])
        self.assertEqual(json.loads(written[0]), [[0, 4]])
        self.assertEqual(status, ("excluded",))
        self.assertEqual(json.loads(spans[0]), [[1, 3]])
        self.assertGreater(absent[0], 0)


if __name__ == "__main__":
    unittest.main()
