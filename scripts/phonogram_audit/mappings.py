import csv
import json
from collections import Counter
from pathlib import Path

from .models import Mapping, MappingAudit, Target, TargetKind, TargetStatus


def load_targets(path: Path) -> dict[str, Target]:
    with path.open(newline="") as stream:
        records = [Target(
            row["concept_id"], row["concept_name"], TargetKind(row["kind"]), row["spelling"],
            json.loads(row["phonemes"]), TargetStatus(row["model_status"]), json.loads(row["member_ids"]), row["context"],
        ) for row in csv.DictReader(stream)]
    targets = {record.id: record for record in records}
    if len(targets) != len(records):
        raise ValueError("Duplicate target identifiers")
    return targets


def load_mappings(path: Path, targets: dict[str, Target], concept_words: dict,
                  ranks: dict[str, int], example_limit: int) -> list[Mapping]:
    with path.open(newline="") as stream:
        return [Mapping(
            row["source_namespace"], row["source_id"], row["source_name"], row["source_path"],
            [targets[target] for target in json.loads(row["target_ids"])], row["action"],
            row["decoding_transfer"], row["encoding_transfer"], row["reason"],
            sorted(concept_words.get(row["source_id"], []),
                   key=lambda word: (ranks.get(word, float("inf")), word))[:example_limit]
            if row["source_namespace"] == "deployed_catalog_v1" else [],
        ) for row in csv.DictReader(stream)]


def audit_mappings(mappings: list[Mapping], targets: dict[str, Target]) -> MappingAudit:
    keys = [(row.namespace, row.source_id) for row in mappings]
    errors = []
    if len(keys) != len(set(keys)):
        errors.append("Duplicate source keys")
    identities = [(target.spelling, tuple(target.sounds), target.context)
                  for target in targets.values() if target.kind == TargetKind.Phonogram]
    if len(identities) != len(set(identities)):
        errors.append("Duplicate exact phonogram definitions")
    for row in mappings:
        if not row.targets:
            errors.append(f"Empty target list: {row.namespace}:{row.source_id}")
    for target in targets.values():
        if target.kind == TargetKind.Phonogram and (not target.spelling or not target.sounds):
            errors.append(f"Incomplete exact definition: {target.id}")
        for member in target.members:
            if member not in targets:
                errors.append(f"Unknown bundle member: {target.id}:{member}")
    return MappingAudit(
        len(mappings), len(targets), sum(target.kind == TargetKind.Phonogram for target in targets.values()),
        dict(Counter(row.namespace for row in mappings)),
        sorted(target.id for target in targets.values() if target.status == TargetStatus.NotModeled),
        errors, mappings,
    )
