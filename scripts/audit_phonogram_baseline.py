import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from phonogram_audit.alignment import audit_alignment
from phonogram_audit.database import load_inputs
from phonogram_audit.golden import sample_records
from phonogram_audit.mappings import audit_mappings, load_mappings, load_targets
from phonogram_audit.lock import validate_lock
from phonogram_audit.models import AuditPaths, BaselineReport
from phonogram_audit.snapshot import file_snapshot, repository_snapshot
from phonogram_audit.tags import audit_tags, current_tags, invert


def arguments() -> AuditPaths:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=REPOSITORY.parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    data = workspace / "StructuredLearningSoftwareMain" / "infra" / "data"
    notes = workspace / "notes" / "issue-10-phonograms"
    return AuditPaths(
        workspace, REPOSITORY / "data" / "words.db", data / "production_cache.json",
        data / "production_cache_keys.csv", notes / "MASTER-PLAN-ID-MAP.csv",
        notes / "MASTER-PLAN-CATALOG.csv", args.output.resolve(),
    )


def build_report(paths: AuditPaths, settings: dict) -> BaselineReport:
    files = [paths.database, paths.cache, paths.catalog, paths.mapping, paths.target_catalog]
    files += [REPOSITORY / "data" / name for name in ["words.json", "g2p_aligned.json"]]
    snapshots = [file_snapshot(path, paths.workspace, settings["hash_chunk_bytes"]) for path in files]
    inputs = load_inputs(paths.database)
    cache = json.loads(paths.cache.read_text())
    tags = current_tags(inputs)
    targets = load_targets(paths.target_catalog)
    mappings = load_mappings(paths.mapping, targets, cache["concept_to_words"],
                             cache["word_frequency_rank"], settings["example_limit"])
    pronunciations = {row[0]: row[1] for row in json.loads(files[-2].read_text())}
    alignments = json.loads(files[-1].read_text())
    report = BaselineReport(
        settings["schema_version"], settings["phase"], datetime.now(timezone.utc).isoformat(),
        [repository_snapshot(paths.workspace, name) for name in settings["repositories"]],
        snapshots, audit_tags(tags, invert(cache["concept_to_words"])),
        audit_alignment(inputs, pronunciations, alignments, settings["alignment_example_limit"]),
        audit_mappings(mappings, targets),
    )
    after = file_snapshot(paths.database, paths.workspace, settings["hash_chunk_bytes"])
    if after.sha256 != snapshots[0].sha256:
        raise ValueError("Source database changed during read-only audit")
    samples = sample_records(inputs, tags, settings["sample_words"])
    paths.output.mkdir(parents=True, exist_ok=True)
    (paths.output / "detector-golden.json").write_text(json.dumps(samples, indent=2) + "\n")
    return report


def main() -> None:
    settings = json.loads((REPOSITORY / "scripts/phonogram_audit/settings.json").read_text())
    paths = arguments()
    report = build_report(paths, settings)
    validate_lock(report, REPOSITORY / "data/fixtures/phonogram-baseline.lock.json")
    (paths.output / settings["report_filename"]).write_text(json.dumps(asdict(report), indent=2) + "\n")
    print(json.dumps(dict(shared_words=report.tags.shared_words, identical_words=report.tags.identical_words,
                          mapping_rows=report.mapping.source_rows, mapping_errors=report.mapping.errors)))
    if report.tags.mismatches or report.mapping.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
