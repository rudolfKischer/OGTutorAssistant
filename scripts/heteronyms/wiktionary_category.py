import json
import re
from pathlib import Path

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
SOURCE = SETTINGS["sources"]["wiktionary_category"]
WORD = re.compile(SETTINGS["word_pattern"])


def read(repository: Path) -> list[str]:
    members = json.loads((repository / SOURCE["raw_path"]).read_text())["members"]
    return sorted({member for member in members if WORD.match(member)})
