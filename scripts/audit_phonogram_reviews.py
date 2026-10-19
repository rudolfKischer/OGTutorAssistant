import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from contextlib import closing
from dataclasses import asdict
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.phonogram_base.storage import sql
from scripts.phonogram_review_audit.assess import assessment_for
from scripts.phonogram_review_audit.groups import group_for
from scripts.phonogram_review_audit.models import PatternReview, ReviewReport, WordEvidence


AUDIT_DIRECTORY = REPOSITORY / "scripts/phonogram_review_audit"


def review_record(record: dict, connection, groups: list[dict], settings: dict) -> tuple[PatternReview, set[str]]:
    pattern = record["pattern"]
    group = group_for(record, groups)
    query = (AUDIT_DIRECTORY / "sql/evidence.sql").read_text()
    evidence = [WordEvidence(*row) for row in connection.execute(query, (pattern["id"],))]
    limit = settings["sample_limit"]
    consistent = [row.word for row in evidence if row.status == "consistent"][:limit]
    excluded = [row.word for row in evidence if row.status == "excluded"][:limit]
    result = PatternReview(pattern["id"], pattern["spelling"], pattern["sounds"], record["section"], group,
                           record["word_count"], record["excluded_words"], sum(row.weight for row in evidence),
                           consistent, excluded, assessment_for(record, group, settings))
    return result, {row.word for row in evidence}


def audit(database: Path, groups: list[dict], settings: dict) -> ReviewReport:
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        connection.execute(sql("readonly.sql"))
        summary = json.loads(connection.execute(sql("summary.sql")).fetchone()[0])
        records = [row for row in summary["patterns"] if row["section"] != "teaching"]
        findings, affected = [], set()
        for record in records:
            finding, words = review_record(record, connection, groups, settings)
            findings.append(finding)
            affected.update(words)
    code = {str(path.relative_to(REPOSITORY)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [Path(__file__), *AUDIT_DIRECTORY.rglob("*.py"), *AUDIT_DIRECTORY.rglob("*.sql")]}
    payload = json.dumps([summary["bundle_version"], groups, settings, code], sort_keys=True)
    version = hashlib.sha256(payload.encode()).hexdigest()
    return ReviewReport(summary["bundle_version"], version, len(findings), dict(Counter(row.group for row in findings)),
                        dict(Counter(row.assessment.category for row in findings)), len(affected), findings)


def write_outputs(report: ReviewReport, directory: Path, publish: bool = True) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    document = json.dumps(asdict(report), indent=2) + "\n"
    (directory / "phonogram-review-audit.json").write_text(document)
    if publish:
        (REPOSITORY / "static/phonogram-review/review-audit.json").write_text(document)
    fields = ["pattern_id", "spelling", "sounds", "section", "group", "word_count", "excluded_words",
              "consistent_examples", "excluded_examples", "assessment", "claim_status", "fix_ids", "note"]
    with (directory / "phonogram-review-audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for finding in report.findings:
            row = asdict(finding)
            assessment = row.pop("assessment")
            row.pop("affected_frequency_weight")
            row.update(assessment=assessment["category"], claim_status=assessment["status"],
                       fix_ids=assessment["fix_ids"], note=assessment["note"])
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--no-publish", action="store_true")
    arguments = parser.parse_args()
    base = json.loads((REPOSITORY / "scripts/phonogram_base/settings.json").read_text())
    review = json.loads((REPOSITORY / "static/phonogram-review/settings.json").read_text())
    settings = json.loads((REPOSITORY / "data/mappings/phonogram-review-assessments.json").read_text())
    report = audit(arguments.database or Path(base["database"]), review["base"]["reviewGroups"], settings)
    write_outputs(report, arguments.output, not arguments.no_publish)
    print(json.dumps(dict(patterns=report.reviewed_patterns, groups=report.group_counts, assessments=report.assessments)))


if __name__ == "__main__":
    main()
