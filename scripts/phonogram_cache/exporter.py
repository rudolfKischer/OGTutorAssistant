import csv
import json
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from scripts.phonogram_audit.database import connect_readonly

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())


def replaced_ids(workspace: Path) -> set[str]:
    with (workspace / SETTINGS["id_map"]).open() as stream:
        return {row["source_id"] for row in csv.DictReader(stream)
                if row["namespace"] == SETTINGS["id_map_namespace"] and row["action"] == SETTINGS["replaced_action"]}


def occurrence_tag(definition: dict) -> str:
    if definition["kind"] == SETTINGS["punctuation_kind"]:
        return ""
    if definition["definition_ids"]:
        return definition["definition_ids"][0]
    parts = [SETTINGS["unmodeled_prefix"], definition["spelling"], SETTINGS["sound_separator"].join(definition["sounds"])]
    return SETTINGS["tag_separator"].join(parts)


def phonogram_tags(database: Path) -> dict[str, set[str]]:
    tags: dict[str, set[str]] = defaultdict(set)
    with closing(connect_readonly(database)) as connection:
        for word, status, definition, layer in connection.execute(SETTINGS["observation_query"]):
            tags[word]
            if status != "consistent":
                tags[word].add(SETTINGS["unresolved_tag"])
            tag = occurrence_tag(json.loads(definition)) if definition and status == "consistent" else ""
            if tag:
                tags[word].add(tag)
    return tags


def old_tags(cache: dict) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for concept, words in cache["concept_to_words"].items():
        for word in words:
            result[word].add(concept)
    return result


def build(workspace: Path, database: Path) -> dict:
    cache = json.loads((workspace / SETTINGS["deployed_cache"]).read_text())
    removed = replaced_ids(workspace)
    combined = old_tags(cache)
    new = phonogram_tags(database)
    concept_to_words: dict[str, list[str]] = defaultdict(list)
    for word in sorted(set(combined) | set(new)):
        tags = (combined.get(word, set()) - removed) | new.get(word, {SETTINGS["unresolved_tag"]})
        for tag in tags:
            concept_to_words[tag].append(word)
    return {"concept_to_words": dict(concept_to_words), "sight_words": cache["sight_words"],
            "word_frequency_rank": cache["word_frequency_rank"], "format_version": SETTINGS["format_version"]}
