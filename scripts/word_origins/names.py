import csv
import io
import json
import zipfile
from pathlib import Path

from .download import curl
from .forms import base_forms
from .progress import Progress
from .settings import SETTINGS

NAMES = SETTINGS["names"]
DOWNLOADS = NAMES["downloads"]
NAME_COLUMN = 0
GEONAMES_NAME, GEONAMES_ASCII, GEONAMES_ALTERNATES = 1, 2, 3
COUNTRY_COLUMN = 4


def member(name: str, data: bytes, key: str) -> str:
    return zipfile.ZipFile(io.BytesIO(data)).read(DOWNLOADS[key]["member"]).decode("utf-8", "replace")


def surnames(wanted: set[str]) -> set[str]:
    text = member("census_surnames", curl(DOWNLOADS["census_surnames"]["url"]), "census_surnames")
    rows = csv.reader(io.StringIO(text))
    next(rows)
    return {row[NAME_COLUMN].lower() for row in rows} & wanted


def first_names(wanted: set[str]) -> set[str]:
    found: set[str] = set()
    for key in ("census_male_first", "census_female_first"):
        lines = curl(DOWNLOADS[key]["url"]).decode().splitlines()
        found |= {line.split()[0].lower() for line in lines if line.strip()}
    return found & wanted


def places(wanted: set[str]) -> set[str]:
    text = member("geonames_cities", curl(DOWNLOADS["geonames_cities"]["url"]), "geonames_cities")
    found: set[str] = set()
    for line in text.splitlines():
        parts = line.split("\t")
        found.update(parts[GEONAMES_ALTERNATES].lower().split(","))
        found.update({parts[GEONAMES_NAME].lower(), parts[GEONAMES_ASCII].lower()})
    countries = curl(DOWNLOADS["geonames_countries"]["url"]).decode().splitlines()
    found.update(line.split("\t")[COUNTRY_COLUMN].lower() for line in countries if not line.startswith("#"))
    return found & wanted


def exceptions(archive: zipfile.ZipFile, common: set[str], wanted: set[str]) -> set[str]:
    found: set[str] = set()
    for part in NAMES["wordnet_files"]:
        for line in archive.read(NAMES["wordnet_exceptions"].format(part)).decode().splitlines():
            irregular, *bases = line.split()
            found.update({irregular} if common & set(bases) and irregular in wanted else set())
    return found


def stopwords() -> set[str]:
    data = zipfile.ZipFile(io.BytesIO(curl(DOWNLOADS["stopwords"]["url"]))).read(DOWNLOADS["stopwords"]["member"])
    return {line.strip().lower() for line in data.decode().splitlines() if line.strip()}


def wordnet(wanted_forms: set[str]) -> dict[str, set[str]]:
    archive = zipfile.ZipFile(io.BytesIO(curl(DOWNLOADS["wordnet"]["url"])))
    common: set[str] = set()
    proper: set[str] = set()
    acronyms: set[str] = set()
    for part in NAMES["wordnet_files"]:
        for line in archive.read(NAMES["wordnet_member"].format(part)).decode().splitlines():
            if line.startswith(" "):
                continue
            fields = line.split()
            for index in range(int(fields[3], 16)):
                lemma = fields[4 + 2 * index].split("(")[0]
                bucket = common if lemma[0].islower() else proper
                if lemma.isupper() and len(lemma) >= NAMES["acronym_minimum_letters"]:
                    bucket = acronyms
                if "_" not in lemma and lemma.lower() in wanted_forms:
                    bucket.add(lemma.lower())
    common |= exceptions(archive, common, wanted_forms) | stopwords()
    return {"common": common, "proper": proper - common, "acronyms": acronyms - common}


def wordnet_lists(words: set[str], forms: set[str]) -> dict[str, set[str]]:
    found = wordnet(forms)
    return {"wordnet_proper": found["proper"] & words, "wordnet_acronym": found["acronyms"] & words, "wordnet_common": found["common"]}


STEPS = {
    "surname": lambda words, forms: surnames(words),
    "first_name": lambda words, forms: first_names(words),
    "place": lambda words, forms: places(words),
    "wordnet": wordnet_lists,
}


def size(found) -> int:
    return sum(len(item) for item in found.values()) if isinstance(found, dict) else len(found)


def collect(repository: Path) -> dict:
    words = {row[0] for row in json.loads((repository / SETTINGS["words_path"]).read_text())}
    forms = set().union(*(base_forms(word) for word in words))
    progress = Progress("names", len(STEPS))
    lists: dict = {}
    for key, build in STEPS.items():
        lists[key] = build(words, forms)
        progress.advance(f"{key}: {size(lists[key])} words")
    progress.finish("name lists built")
    lists.update(lists.pop("wordnet"))
    sources = {key: item["license"] for key, item in DOWNLOADS.items()}
    return {"sources": sources, "lists": {key: sorted(value) for key, value in lists.items()}}
