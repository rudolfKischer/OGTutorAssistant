import json
import math
import re
import time
import urllib.parse
from pathlib import Path

from .download import curl
from .progress import Progress
from .settings import SETTINGS

WIKTIONARY = SETTINGS["wiktionary"]
WORD = re.compile(WIKTIONARY["word_pattern"])


def request(category: str, token: str | None) -> dict | None:
    parameters = {"action": "query", "list": "categorymembers", "cmtitle": f"Category:{category}", "cmlimit": WIKTIONARY["page_size"],
                  "cmtype": "page", "format": "json", "formatversion": 2}
    if token:
        parameters["cmcontinue"] = token
    time.sleep(WIKTIONARY["request_delay_seconds"])
    try:
        return json.loads(curl(WIKTIONARY["api"] + "?" + urllib.parse.urlencode(parameters)))
    except (RuntimeError, json.JSONDecodeError):
        return None


def category_size(category: str) -> int:
    parameters = {"action": "query", "prop": "categoryinfo", "titles": f"Category:{category}", "format": "json", "formatversion": 2}
    time.sleep(WIKTIONARY["request_delay_seconds"])
    try:
        page = json.loads(curl(WIKTIONARY["api"] + "?" + urllib.parse.urlencode(parameters)))["query"]["pages"][0]
        return page["categoryinfo"]["pages"]
    except (RuntimeError, json.JSONDecodeError, KeyError):
        return WIKTIONARY["fallback_size"]


def requests_needed(entry: dict) -> int:
    if entry.get("complete"):
        return 0
    return max(math.ceil(entry["size"] / WIKTIONARY["page_size"]) - entry.get("requests", 0), 0)


def load(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {"source": WIKTIONARY["source"], "categories": {}}


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n")


def pull(name: str, category: str, entry: dict, wanted: set[str], failures: list[int], progress: Progress) -> bool:
    while not entry.get("complete"):
        payload = request(category, entry.get("continue"))
        if payload is None or "query" not in payload:
            failures[0] += 1
            if failures[0] >= WIKTIONARY["maximum_failures"]:
                return False
            progress.message(f"{name}: rate limited, waiting {WIKTIONARY['retry_delay_seconds']}s (failure {failures[0]}/{WIKTIONARY['maximum_failures']})")
            time.sleep(WIKTIONARY["retry_delay_seconds"])
            continue
        failures[0] = 0
        titles = {item["title"].lower() for item in payload["query"]["categorymembers"]}
        entry["members"] = sorted(set(entry.get("members", [])) | {title for title in titles if WORD.match(title) and title in wanted})
        entry["continue"] = payload.get("continue", {}).get("cmcontinue")
        entry["complete"] = entry["continue"] is None
        entry["requests"] = entry.get("requests", 0) + 1
        progress.advance(f"{name}: {len(entry['members'])} words matched" + (" (category complete)" if entry["complete"] else ""))
    return True


def prepare(data: dict, path: Path) -> list[tuple[str, str, dict]]:
    plan = []
    for name, category in WIKTIONARY["categories"].items():
        entry = data["categories"].setdefault(name, {"category": category})
        if "size" not in entry and not entry.get("complete"):
            print(f"measuring {category} ...", flush=True)
            entry["size"] = category_size(category)
            save(path, data)
        plan.append((name, category, entry))
    return plan


def fetch(repository: Path) -> dict:
    path = repository / WIKTIONARY["raw_path"]
    wanted = {row[0] for row in json.loads((repository / SETTINGS["words_path"]).read_text())}
    data = load(path)
    plan = prepare(data, path)
    total = sum(requests_needed(entry) for _, _, entry in plan)
    print(f"wiktionary: {len(plan)} categories, {total} requests left, about {total * (WIKTIONARY['request_delay_seconds'] + 1) // 60} minutes", flush=True)
    progress, failures = Progress("wiktionary", total), [0]
    for name, category, entry in plan:
        finished = pull(name, category, entry, wanted, failures, progress)
        save(path, data)
        if not finished:
            print("\nstopped early (rate limit); progress saved, run the same command again to resume", flush=True)
            return data
    progress.finish("all categories downloaded")
    return data
