import json
from pathlib import Path

from .catalog import SETTINGS

LIST_FLAGS = ("loan", "proper_noun", "acronym", "name_sense", "letter_names", "acronym_sense", "inappropriate")


def read_origins(repository: Path) -> dict[str, dict]:
    return json.loads((repository / SETTINGS["origins_path"]).read_text())["words"]


def origin_rows(word_id: int, flags: dict) -> list[tuple[int, str, str]]:
    rows = []
    for flag, value in flags.items():
        detail = ", ".join(value) if flag in LIST_FLAGS else ""
        rows.append((word_id, flag, detail))
    return rows
