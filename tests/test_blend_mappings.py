import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from db_builder.phonograms.models import Direction, PairDefinition, validate_blends
from db_builder.phonograms.store import BlendStore
from scripts.phonogram_blend_routes import load_store
from scripts.phonogram_review import create_app


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT.parent / "notes/issue-10-phonograms/phase-0"


class BlendMappingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "blends.sqlite"
        self.store, self.version = load_store(ROOT, self.database)
        self.blends = {blend.id: blend for blend in self.store.definitions()}

    def test_all_existing_blends_have_valid_ordered_components(self):
        self.assertEqual(len(self.blends), 40)
        initial = self.blends["blend_initial_st"]
        final = self.blends["blend_final_st"]
        self.assertEqual(initial.spelling, "st")
        self.assertEqual(initial.sounds, ["s", "t"])
        self.assertEqual(final.sounds, initial.sounds)
        self.assertNotEqual(initial.id, final.id)
        self.assertEqual([(unit.start, unit.end) for unit in initial.components], [(0, 1), (1, 2)])

    def test_letters_can_have_different_or_multiple_sounds(self):
        self.assertEqual(self.blends["blend_initial_sc"].sounds, ["s", "k"])
        self.assertEqual(self.blends["blend_final_xt"].sounds, ["k", "s", "t"])
        self.assertEqual(len(self.blends["blend_final_xt"].components), 2)

    def test_selection_roundtrips_the_existing_id_and_independent_direction(self):
        self.store.save_selection(Direction.Reading, "blend_initial_st")
        self.assertEqual(len(self.store.selections()), 1)
        self.store.save_selection(Direction.Spelling, "blend_final_st")
        reopened = BlendStore(self.database)
        saved = {row.direction: row for row in reopened.selections()}
        self.assertEqual(saved[Direction.Reading].concept_id, "blend_initial_st")
        self.assertEqual(saved[Direction.Spelling].concept_id, "blend_final_st")
        self.assertTrue(all(row.bundle_version == self.version for row in saved.values()))

    def test_unknown_or_component_ids_cannot_be_saved_as_blends(self):
        for concept in ["unknown", "phonogram_s_s"]:
            with self.assertRaises(ValueError):
                self.store.save_selection(Direction.Reading, concept)
        self.assertEqual(self.store.selections(), [])

    def test_reseeding_preserves_saved_selection(self):
        self.store.save_selection(Direction.Reading, "blend_initial_st")
        reopened, _ = load_store(ROOT, self.database)
        self.assertEqual(reopened.selections()[0].concept_id, "blend_initial_st")

    def test_invalid_sequences_and_positions_are_rejected(self):
        blend = self.blends["blend_initial_st"]
        inventory = json.loads((ROOT / "static/phonogram-review/inventories.json").read_text())
        pairs = [PairDefinition(row["id"], row["spelling"], row["sounds"]) for row in inventory["phonograms"]]
        invalids = [replace(blend, sounds=["sh"]), replace(blend, spelling="ts"),
                    replace(blend, components=blend.components[:1])]
        for invalid in invalids:
            with self.assertRaises(ValueError):
                validate_blends([invalid], pairs)

    def test_readonly_authoring_database_is_never_used_for_preview(self):
        source = ROOT / "data/words.db"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            load_store(ROOT, source)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    def test_api_saves_and_reloads_from_database(self):
        client = create_app(REPORT, blend_database=self.database).test_client()
        response = client.post("/api/blends/selection", json={
            "direction": "reading", "concept_id": "blend_initial_st",
        })
        self.assertEqual(response.status_code, 200)
        data = client.get("/api/blends").get_json()
        self.assertEqual(len(data["definitions"]), 40)
        self.assertEqual(data["selections"], [response.get_json()])
        self.assertEqual(BlendStore(self.database).selections()[0].concept_id, "blend_initial_st")

    def test_api_rejects_unknown_ids_and_invalid_directions(self):
        client = create_app(REPORT, blend_database=self.database).test_client()
        for payload in [{}, {"direction": "reading", "concept_id": "missing"},
                        {"direction": "both", "concept_id": "blend_initial_st"},
                        {"direction": [], "concept_id": "blend_initial_st"}]:
            self.assertEqual(client.post("/api/blends/selection", json=payload).status_code, 400)
        self.assertEqual(self.store.selections(), [])


if __name__ == "__main__":
    unittest.main()
