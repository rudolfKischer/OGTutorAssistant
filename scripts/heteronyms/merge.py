import json
from dataclasses import asdict
from pathlib import Path

from . import homograph_data, wikipedia_table, wiktionary_category
from .models import Heteronym

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
SOURCES = SETTINGS["sources"]


def merge(repository: Path) -> list[Heteronym]:
    entries: dict[str, Heteronym] = {}
    for source, senses in [(SOURCES["wikipedia_table"]["id"], wikipedia_table.read(repository)),
                           (SOURCES["homograph_data"]["id"], homograph_data.read(repository))]:
        for spelling, items in senses.items():
            entry = entries.setdefault(spelling, Heteronym(spelling))
            entry.sources.append(source)
            entry.senses.extend(items)
    for spelling in wiktionary_category.read(repository):
        entry = entries.setdefault(spelling, Heteronym(spelling))
        entry.sources.append(SOURCES["wiktionary_category"]["id"])
    return sorted(entries.values(), key=lambda entry: entry.spelling)


def build(repository: Path) -> dict:
    entries = merge(repository)
    return {"sources": list(SOURCES.values()), "attribution": SETTINGS["attribution"],
            "words": len(entries), "senses": sum(len(entry.senses) for entry in entries),
            "entries": [asdict(entry) for entry in entries]}
