import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

from .progress import Progress
from .settings import SETTINGS

HEADWORD = re.compile(SETTINGS["headword_pattern"], re.M)
SINGLE_WORD = re.compile(SETTINGS["single_word_pattern"])


def wikitext(page: str) -> str:
    parameters = {"action": "parse", "page": page, "prop": "wikitext", "format": "json", "formatversion": 2}
    url = SETTINGS["api"] + "?" + urllib.parse.urlencode(parameters)
    time.sleep(SETTINGS["request_delay_seconds"])
    result = subprocess.run(["curl", "-sS", "-m", str(SETTINGS["timeout_seconds"]), "-A", SETTINGS["user_agent"], url],
                            capture_output=True, text=True)
    try:
        return json.loads(result.stdout)["parse"]["wikitext"]
    except (json.JSONDecodeError, KeyError):
        return ""


def headwords(text: str, wanted: set[str]) -> list[str]:
    found = {match.strip().lower() for match in HEADWORD.findall(text)}
    return sorted(word for word in found if SINGLE_WORD.match(word) and word in wanted)


def fetch(repository: Path) -> dict:
    wanted = {row[0] for row in json.loads((repository / SETTINGS["words_path"]).read_text())}
    languages = {}
    progress = Progress("wikipedia", len(SETTINGS["pages"]))
    for language, page in SETTINGS["pages"].items():
        languages[language] = headwords(wikitext(page), wanted)
        progress.advance(f"{language}: {len(languages[language])} words")
    progress.finish("loan lists downloaded")
    return {"source": SETTINGS["source"], "languages": languages}
