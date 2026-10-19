import csv
import json
import re
from pathlib import Path

from .models import Sense

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
SOURCE = SETTINGS["sources"]["homograph_data"]
COLUMNS = SETTINGS["homograph_columns"]
POS_KIND = "PoS"


def ipa_of(text: str) -> str:
    text = text.replace("'", "ˈ")
    return re.sub(r"\d", "", text)


def read(repository: Path) -> dict[str, list[Sense]]:
    result: dict[str, list[Sense]] = {}
    with (repository / SOURCE["raw_path"]).open(newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            label = row[COLUMNS["label"]]
            pos = label if row[COLUMNS["fine_type"]] == POS_KIND else ""
            sense = Sense(SOURCE["id"], ipa_of(row[COLUMNS["ipa"]]), pos, label, row[COLUMNS["type"]])
            result.setdefault(row[COLUMNS["word"]].lower(), []).append(sense)
    return result
