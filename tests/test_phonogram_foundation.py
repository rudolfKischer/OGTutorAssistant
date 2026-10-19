import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.phonogram_audit.database import connect_readonly
from scripts.phonogram_audit.golden import check_golden
from scripts.phonogram_audit.mappings import audit_mappings
from scripts.phonogram_audit.models import Mapping, Target


ROOT = Path(__file__).resolve().parents[1]


class PhonogramFoundationTests(unittest.TestCase):
    def test_detector_matches_frozen_word_inputs(self):
        fixture = ROOT / "data/fixtures/detector-golden.json"
        self.assertTrue(json.loads(fixture.read_text()))
        self.assertEqual(check_golden(fixture), [])

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                connect_readonly(path)
            self.assertFalse(path.exists())

    def test_readonly_connection_refuses_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.db"
            with sqlite3.connect(path) as connection:
                connection.executescript((ROOT / "tests/sql/readonly-fixture.sql").read_text())
            before = path.read_bytes()
            with connect_readonly(path) as connection:
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute((ROOT / "tests/sql/readonly-mutation.sql").read_text())
            self.assertEqual(path.read_bytes(), before)

    def test_source_namespace_preserves_the_i_collision(self):
        sight = Target("i", "i", "sight_word", "", [], "modeled", [])
        short_i = Target("phonogram_i_short_i", "i -> short i", "phonogram", "i", ["short_i"], "modeled", [])
        targets = {target.id: target for target in [sight, short_i]}
        records = [Mapping(namespace, "i", "i", "fixture", [target], "retain", "copy_each_direction",
                           "copy_each_direction", "fixture", [])
                   for namespace, target in [("deployed_catalog_v1", sight), ("og_classic_fixture_v1", short_i)]]
        self.assertEqual(audit_mappings(records, targets).errors, [])
        self.assertNotEqual(records[0].targets[0].id, records[1].targets[0].id)

    def test_duplicate_source_cannot_silently_override_a_mapping(self):
        target = Target("i", "i", "sight_word", "", [], "modeled", [])
        mapping = Mapping("fixture", "i", "i", "fixture", [target], "retain", "copy_each_direction",
                          "copy_each_direction", "fixture", [])
        self.assertTrue(audit_mappings([mapping, mapping], {target.id: target}).errors)

    def test_empty_phonogram_and_missing_bundle_members_fail_validation(self):
        invalid = Target("invalid", "invalid", "phonogram", "", [], "modeled", ["missing"])
        result = audit_mappings([], {invalid.id: invalid})
        self.assertEqual(len(result.errors), 2)


if __name__ == "__main__":
    unittest.main()
