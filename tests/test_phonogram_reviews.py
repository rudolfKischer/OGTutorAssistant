import json
import unittest
from pathlib import Path

from db_builder.phoneme_converter import convert_phoneme_sequence
from scripts.phonogram_review_audit.assess import assessment_for
from scripts.phonogram_review_audit.benchmarks import pronunciation_check
from scripts.phonogram_review_audit.groups import group_for


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = json.loads((ROOT / "static/phonogram-review/settings.json").read_text())
ASSESSMENTS = json.loads((ROOT / "data/mappings/phonogram-review-assessments.json").read_text())


def record(section="review", count=0, excluded=0, defined=False, spelling="x", sounds=None):
    return {"section": section, "word_count": count, "excluded_words": excluded,
            "flags": ["rare"] if count < 10 else [], "pattern": {
                "id": "test", "spelling": spelling, "sounds": sounds or [],
                "kind": "silent" if section == "silent" else "phonogram",
                "definition_ids": ["test"] if defined else [],
            }}


class PhonogramReviewTests(unittest.TestCase):
    def test_each_primary_reason_has_a_distinct_group(self):
        cases = [
            (record(count=10), "unmapped_common"), (record(count=1), "unmapped_rare"),
            (record(excluded=3), "excluded_only"), (record(defined=True, count=1), "defined_rare"),
            (record(defined=True), "defined_unobserved"),
            (record(section="silent", spelling="'", excluded=3), "silent_punctuation"),
            (record(section="silent", count=1), "silent_consistent"),
            (record(section="silent", excluded=3), "silent_excluded"),
        ]
        for case, expected in cases:
            self.assertEqual(group_for(case, SETTINGS["base"]["reviewGroups"]), expected)

    def test_defined_pattern_with_only_excluded_matches_is_not_unobserved(self):
        case = record(defined=True, excluded=4)
        self.assertEqual(group_for(case, SETTINGS["base"]["reviewGroups"]), "excluded_only")

    def test_zero_count_long_u_definitions_have_a_verified_representation_issue(self):
        converted = [sound for _, sound in convert_phoneme_sequence(["Y", "UW1"])]
        self.assertEqual(converted, ["long_u"])
        case = record(defined=True, spelling="u", sounds=["y", "long_oo"])
        assessment = assessment_for(case, "defined_unobserved", ASSESSMENTS)
        self.assertEqual(assessment.category, "canonical_alias")
        self.assertEqual(assessment.status, "Verified")
        self.assertIn("FIX-01", assessment.fix_ids)

    def test_linguistic_hypotheses_are_not_marked_verified(self):
        case = record(count=1, spelling="f", sounds=["v"])
        assessment = assessment_for(case, "unmapped_rare", ASSESSMENTS)
        self.assertEqual(assessment.category, "exception")
        self.assertEqual(assessment.status, "Unverified")

    def test_source_comparison_distinguishes_variants_from_missing_data(self):
        variants = {"read": [["R", "EH1", "D"], ["R", "IY1", "D"]]}
        alignment = [["r", "R"], ["ea", "IY"], ["d", "D"]]
        self.assertEqual(pronunciation_check("read", ["R", "EH1", "D"], alignment, variants),
                         "matches_other_cmu_variant")
        self.assertEqual(pronunciation_check("read", ["R", "IY1", "D"], alignment, variants), "matches_selected")
        self.assertEqual(pronunciation_check("read", ["R", "IY1", "D"], [], variants), "missing_alignment")

    def test_every_flagged_pattern_has_an_individual_audit_record(self):
        audit = json.loads((ROOT / "static/phonogram-review/review-audit.json").read_text())
        self.assertEqual(audit["reviewed_patterns"], len(audit["findings"]))
        self.assertEqual(sum(audit["group_counts"].values()), audit["reviewed_patterns"])
        self.assertEqual(len({row["pattern_id"] for row in audit["findings"]}), audit["reviewed_patterns"])
        self.assertTrue(all(row["assessment"]["note"] and row["assessment"]["fix_ids"] for row in audit["findings"]))


if __name__ == "__main__":
    unittest.main()
