import json
import subprocess
from pathlib import Path

from .progress import Progress
from .settings import SETTINGS

KAIKKI = SETTINGS["kaikki"]
MEGABYTE = 1024 * 1024
ORIGIN_ARGUMENT = "2"


def size_of(url: str) -> int:
    head = subprocess.run(["curl", "-sIL", "-A", SETTINGS["user_agent"], url], capture_output=True, text=True).stdout
    lengths = [int(line.split(":")[1]) for line in head.splitlines() if line.lower().startswith("content-length")]
    return lengths[-1] if lengths else 0


def origins(entry: dict) -> list[str]:
    found = []
    for template in entry.get("etymology_templates", []):
        arguments = template.get("args", {})
        if template.get("name") in KAIKKI["loan_templates"] and ORIGIN_ARGUMENT in arguments:
            found.append(arguments[ORIGIN_ARGUMENT])
    return found


def acronym_tags(entry: dict) -> list[str]:
    tags = {tag for sense in entry.get("senses", []) for tag in sense.get("tags", [])}
    return sorted(tags & set(KAIKKI["acronym_tags"]))


def record(found: dict, word: str, entry: dict) -> None:
    item = found.setdefault(word.lower(), {"lower": False, "name": False, "acronym": [], "loan": []})
    if entry.get("pos") == KAIKKI["name_pos"]:
        item["name"] = True
        return
    if word == word.lower() and not acronym_tags(entry):
        item["lower"] = True
    item["acronym"] = sorted(set(item["acronym"]) | set(acronym_tags(entry)))
    item["loan"] = sorted(set(item["loan"]) | set(origins(entry)))


def stream(wanted: set[str]) -> dict:
    total = size_of(KAIKKI["url"]) // (KAIKKI["progress_megabytes"] * MEGABYTE) + 1
    progress, found, read = Progress("kaikki", total), {}, 0
    process = subprocess.Popen(["curl", "-sSL", "-A", SETTINGS["user_agent"], KAIKKI["url"]], stdout=subprocess.PIPE)
    chunks = 0
    for line in process.stdout:
        read += len(line)
        if read // (KAIKKI["progress_megabytes"] * MEGABYTE) > chunks:
            chunks += 1
            progress.advance(f"{read // MEGABYTE} MB read, {len(found)} of our words seen")
        entry = json.loads(line)
        word = entry.get("word", "")
        if word.lower() in wanted:
            record(found, word, entry)
    if process.wait() != 0:
        raise RuntimeError("kaikki download failed; run the same command again")
    progress.finish(f"complete, {len(found)} of our words found")
    return found


def fetch(repository: Path) -> dict:
    wanted = {row[0] for row in json.loads((repository / SETTINGS["words_path"]).read_text())}
    return {"source": KAIKKI["source"], "words": stream(wanted)}
