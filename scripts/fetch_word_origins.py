import argparse
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.word_origins import kaikki, names, safety, wiktionary
from scripts.word_origins.fetch import SETTINGS, fetch

SOURCES = ("wikipedia", "names", "wiktionary", "kaikki", "safety")


def run_wikipedia() -> None:
    path = REPOSITORY / SETTINGS["raw_path"]
    path.write_text(json.dumps(fetch(REPOSITORY), ensure_ascii=False) + "\n")
    print("saved", path)


def run_names() -> None:
    data = names.collect(REPOSITORY)
    path = REPOSITORY / SETTINGS["names"]["raw_path"]
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n")
    print("saved", path, {key: len(value) for key, value in data["lists"].items()})


def run_wiktionary() -> None:
    wiktionary.fetch(REPOSITORY)


def run_kaikki() -> None:
    path = REPOSITORY / SETTINGS["kaikki"]["raw_path"]
    path.write_text(json.dumps(kaikki.fetch(REPOSITORY), ensure_ascii=False) + "\n")
    print("saved", path)


def run_safety() -> None:
    path = REPOSITORY / SETTINGS["safety"]["raw_path"]
    path.write_text(json.dumps(safety.fetch(REPOSITORY), ensure_ascii=False) + "\n")
    print("saved", path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download origin sources. Each source is resumable and independent.")
    parser.add_argument("--only", choices=SOURCES, action="append")
    runners = dict(wikipedia=run_wikipedia, names=run_names, wiktionary=run_wiktionary, kaikki=run_kaikki, safety=run_safety)
    for source in parser.parse_args().only or SOURCES:
        runners[source]()


if __name__ == "__main__":
    main()
