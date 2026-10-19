import json
from contextlib import closing
from pathlib import Path

from scripts.phonogram_audit.database import connect_readonly
from .models import Definition, PatternKind
from .registry import Registry


SQL_DIRECTORY = Path(__file__).with_name("sql")


def definitions(repository: Path) -> list[Definition]:
    inventory = json.loads((repository / "static/phonogram-review/inventories.json").read_text())
    blends = json.loads((repository / "data/mappings/blend-phonograms.json").read_text())
    return [Definition(row["id"], row["spelling"], row["sounds"], PatternKind(row["kind"]), row["context"])
            for row in inventory["phonograms"] + blends["definitions"]]


def silent_rules(repository: Path, settings: dict) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    rules = json.loads((repository / settings["silent_merge_path"]).read_text())
    merges = frozenset(spelling for item in rules["classes"] for spelling in item["spellings"])
    return merges, frozenset(rules["split_vowels"]["spellings"]), frozenset(rules["suffix_endings"]["spellings"])


def load_registry(repository: Path, settings: dict) -> Registry:
    inventory = json.loads((repository / "static/phonogram-review/inventories.json").read_text())
    curriculum_rows = {str(row["row"]): row for row in inventory["curriculum"]}
    baseline = repository.parent / "notes/issue-10-phonograms/phase-0/baseline.json"
    report = json.loads(baseline.read_text())
    curriculum = {}
    for mapping in report["mapping"]["mappings"]:
        if mapping["namespace"] != settings["curriculum_namespace"]:
            continue
        row = curriculum_rows[mapping["source_id"]]
        if row["group"] != settings["phonics_group"]:
            continue
        for target in mapping["targets"]:
            curriculum.setdefault(target["id"], []).append(row["name"])
    merges, splits, suffixes = silent_rules(repository, settings)
    return Registry(definitions(repository), curriculum, merges, splits, suffixes)


def words(repository: Path) -> list[tuple]:
    with closing(connect_readonly(repository / "data/words.db")) as connection:
        return connection.execute((SQL_DIRECTORY / "source-words.sql").read_text()).fetchall()
