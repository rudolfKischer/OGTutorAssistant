import json
import re
from pathlib import Path

from .models import Sense

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
SOURCE = SETTINGS["sources"]["wikipedia_table"]
SPELLING = re.compile(SETTINGS["spelling_pattern"])
MARKUP = re.compile(SETTINGS["markup_pattern"], re.S)
TEMPLATE = re.compile(r"\{\{" + SETTINGS["ipa_template"] + r"\|([^}]*)\}\}")
VARIANT_JOINER = ", "


def clean(text: str) -> str:
    return " ".join(MARKUP.sub(lambda match: match.group(1) or "", text).split())


def ipa_of(template: str) -> str:
    text = "".join(template.split(SETTINGS["ipa_separator"]))
    for old, new in SETTINGS["ipa_replacements"].items():
        text = text.replace(old, new)
    return text


def table_rows(text: str) -> list[list[str]]:
    start = text.index(SETTINGS["table_start"])
    end = text.index(SETTINGS["table_end"], start)
    body = text[start:end].split(SETTINGS["row_separator"])[1:]
    return [[line[1:] for line in chunk.strip().splitlines() if line.startswith("|")] for chunk in body]


def sense_of(cells: list[str]) -> Sense | None:
    if len(cells) < 3:
        return None
    ipa = VARIANT_JOINER.join(ipa_of(match) for match in TEMPLATE.findall(cells[0]))
    pos = clean(cells[1]).lower()
    return Sense(SOURCE["id"], ipa, SETTINGS["pos_aliases"].get(pos, pos), clean(cells[2]))


def read(repository: Path) -> dict[str, list[Sense]]:
    text = (repository / SOURCE["raw_path"]).read_text()
    result: dict[str, list[Sense]] = {}
    current, remaining = "", 0
    for cells in table_rows(text):
        if not cells:
            continue
        if remaining == 0:
            match = SPELLING.match(cells[0])
            current, remaining, cells = clean(match.group(2)).lower(), int(match.group(1) or 1), cells[1:]
        remaining -= 1
        sense = sense_of(cells)
        if sense:
            result.setdefault(current, []).append(sense)
    return result
