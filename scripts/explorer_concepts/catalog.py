import json
import re
from contextlib import closing
from pathlib import Path

from scripts.phonogram_audit.database import connect_readonly
from scripts.phonogram_cache.exporter import SETTINGS as CACHE
from .models import ConceptRow

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
SQL = Path(__file__).with_name("sql")
KINDS = SETTINGS["kinds"]


class SoundNames:
    def __init__(self, repository: Path):
        ui = json.loads((repository / SETTINGS["ui_config"]).read_text())
        prefix = SETTINGS["sound_label_prefix"]
        self.labels = {key[len(prefix):]: value for key, value in ui["concepts"]["labels"].items() if key.startswith(prefix)}
        self.categories = {sound: category for category, sounds in SETTINGS["vowel_categories"].items() for sound in sounds}
        for category, family_id in SETTINGS["ui_category_families"].items():
            family = next(item for item in ui["conceptFamilies"] if item["id"] == family_id)
            self.categories.update({sound: category for sound in family["filter"]})

    def label(self, sound: str) -> str:
        return self.labels.get(sound, sound.replace("_", " "))

    def join(self, sounds: list[str]) -> str:
        if not sounds:
            return SETTINGS["silent_label"]
        return SETTINGS["sound_separator"].join(self.label(sound) for sound in sounds)

    def family(self, sounds: list[str], spelling: str) -> str:
        if not sounds:
            return SETTINGS["silent_family"]
        if len(sounds) > 1:
            return SETTINGS["sequence_family"]
        traits = {"category": self.categories.get(sounds[0]), "shape": spelling_shape(spelling)}
        rule = next((rule for rule in SETTINGS["family_rules"]
                     if all(traits[key] == value for key, value in rule.items() if key != "family")), None)
        return rule["family"] if rule else SETTINGS["default_family"]


def spelling_shape(spelling: str) -> str:
    if SETTINGS["split_marker"] in spelling:
        return "split"
    return "single" if len(spelling) == 1 else "multi"


def blend_family(definition: dict) -> str | None:
    for rule in SETTINGS["blend_rules"]:
        if rule["context"] != definition["context"]:
            continue
        if re.search(rule.get("spelling_pattern", ""), definition["spelling"]):
            return rule["family"]
    return None


def defined_patterns(database: Path) -> dict[str, dict]:
    result = {}
    with closing(connect_readonly(database)) as connection:
        for (text,) in connection.execute((SQL / "patterns.sql").read_text()):
            definition = json.loads(text)
            if definition["definition_ids"]:
                result[definition["definition_ids"][0]] = definition
    return result


def unmodeled_row(tag: str, names: SoundNames) -> ConceptRow:
    _, spelling, joined = tag.split(CACHE["tag_separator"], 2)
    sounds = [sound for sound in joined.split(CACHE["sound_separator"]) if sound]
    label = SETTINGS["unmodeled_template"].format(spelling=spelling, sounds=names.join(sounds))
    family = names.family(sounds, spelling)
    return ConceptRow(tag, label, KINDS["unmodeled"], family, f"{names.join(sounds)}|{spelling}", spelling, sounds, True)


def defined_row(tag: str, definition: dict, names: SoundNames) -> ConceptRow:
    sounds, spelling = definition["sounds"], definition["spelling"]
    label = SETTINGS["label_template"].format(sounds=names.join(sounds), spelling=spelling)
    family = blend_family(definition) if definition["kind"] == KINDS["blend"] else names.family(sounds, spelling)
    return ConceptRow(tag, label, definition["kind"], family, f"{names.join(sounds)}|{spelling}", spelling, sounds)


def concept_row(tag: str, definitions: dict[str, dict], names: SoundNames) -> ConceptRow | None:
    if tag == CACHE["unresolved_tag"]:
        label = SETTINGS["unresolved_label"]
        return ConceptRow(tag, label, KINDS["unresolved"], SETTINGS["unresolved_family"], tag, "", [])
    if tag.startswith(CACHE["unmodeled_prefix"] + CACHE["tag_separator"]):
        return unmodeled_row(tag, names)
    if tag in definitions:
        return defined_row(tag, definitions[tag], names)
    return None


def notation_rows(workspace: Path) -> list[tuple]:
    copy = json.loads((workspace / SETTINGS["notation_source"]).read_text())["phonemes"]
    prefix = SETTINGS["notation_prefix"]
    return [(key[len(prefix):], item["b"], item["h"], item["l"], item["n"]) for key, item in copy.items()]
