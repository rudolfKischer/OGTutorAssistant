import json
import re
from pathlib import Path

from .download import curl
from .settings import SETTINGS

SAFETY = SETTINGS["safety"]
WORD = re.compile(SAFETY["word_pattern"])


def fetch(repository: Path) -> dict:
    vocabulary = {row[0] for row in json.loads((repository / SETTINGS["words_path"]).read_text())}
    entries = [line.strip().lower() for line in curl(SAFETY["url"]).decode().splitlines() if line.strip()]
    single = sorted({entry for entry in entries if WORD.match(entry) and entry in vocabulary})
    print(f"safety: {len(entries)} entries, {len(single)} single words in our word bank", flush=True)
    return {"source": SAFETY["source"], "entries": len(entries), "words": single}
