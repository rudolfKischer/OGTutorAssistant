import json
from pathlib import Path

from .definitions import abbreviation_flags, name_origins, read_senses, sense_profiles
from .forms import base_forms
from .settings import SETTINGS

NAMES = SETTINGS["names"]
LOAN_PREFIX = "loan:"
SAFETY_CATEGORIES = {"unsafe:vulgar": "vulgar", "unsafe:offensive": "offensive"}
NAME_KINDS = ("surname", "first_name", "place", "wordnet_proper")


def read(repository: Path, key: str) -> dict:
    path = repository / key
    return json.loads(path.read_text()) if path.exists() else {}


def add(words: dict, word: str, flag: str, values: list[str]) -> None:
    entry = words.setdefault(word, {})
    entry[flag] = sorted(set(entry.get(flag, [])) | set(values))


def common_words(repository: Path) -> set[str]:
    lists = read(repository, NAMES["raw_path"]).get("lists", {})
    return set(lists.get("wordnet_common", [])) | set(NAMES["closed_class"])


def is_common(word: str, common: set[str]) -> bool:
    return bool(base_forms(word) & common)


def add_proper_nouns(words: dict, repository: Path, vocabulary: list[str]) -> None:
    lists = read(repository, NAMES["raw_path"]).get("lists", {})
    common = common_words(repository)
    kinds = {kind: set(lists.get(kind, [])) for kind in NAME_KINDS}
    for word in vocabulary:
        found = [kind for kind, members in kinds.items() if word in members]
        if found and not is_common(word, common):
            add(words, word, NAMES["proper_flag"], found)
    for word in lists.get("wordnet_acronym", []):
        if not is_common(word, common):
            add(words, word, NAMES["acronym_flag"], ["wordnet"])


def add_wiktionary(words: dict, repository: Path) -> None:
    categories = read(repository, SETTINGS["wiktionary"]["raw_path"]).get("categories", {})
    common = common_words(repository)
    for name in SETTINGS["wiktionary"]["categories"]:
        entry = categories.get(name, {})
        flag, _, value = name.partition(":")
        for word in entry.get("members", []):
            if flag == "unsafe":
                continue
            if flag == "loan":
                add(words, word, flag, [value])
            elif not is_common(word, common):
                add(words, word, NAMES["acronym_flag"], [name])


def origin_name(code: str) -> str | None:
    kaikki = SETTINGS["kaikki"]
    if code in kaikki["skip_origins"] or code.startswith(tuple(kaikki["skip_origin_prefixes"])):
        return None
    for candidate in (code, code.split("-")[0]):
        if candidate in kaikki["languages"]:
            return kaikki["languages"][candidate]
    return None


def add_kaikki(words: dict, repository: Path) -> None:
    kaikki = SETTINGS["kaikki"]
    found = read(repository, kaikki["raw_path"]).get("words", {})
    for word, item in found.items():
        if item["lower"]:
            words.get(word, {}).pop(NAMES["proper_flag"], None)
            continue
        if item["name"]:
            add(words, word, NAMES["proper_flag"], ["wiktionary"])
        tags = [tag for tag in item["acronym"] if tag in kaikki["flag_acronym_tags"]]
        if tags:
            add(words, word, NAMES["acronym_flag"], tags)
    for word, item in found.items():
        names = sorted({name for code in item["loan"] if (name := origin_name(code))})
        if names and len(word) >= kaikki["loan_minimum_letters"]:
            add(words, word, "loan", names)


def add_definition_names(words: dict, repository: Path) -> None:
    senses = read_senses(repository)
    for word, (kinds, ordinary) in sense_profiles(repository).items():
        origins = name_origins(senses[word])
        if ordinary:
            demote(words, word, kinds + origins)
        elif kinds:
            add(words, word, NAMES["proper_flag"], kinds + origins + [SETTINGS["definitions"]["flag_value"]])


def demote(words: dict, word: str, kinds: list[str]) -> None:
    entry = words.get(word, {})
    carried = entry.pop(NAMES["proper_flag"], [])
    labels = set(NAMES["source_labels"]) | {SETTINGS["definitions"]["flag_value"]}
    found = kinds or [kind for kind in carried if kind not in labels]
    if found:
        add(words, word, NAMES["mixed_flag"], found)


def add_definition_abbreviations(words: dict, repository: Path) -> None:
    abbreviations, profiles = abbreviation_flags(repository)
    for word in abbreviations:
        if SETTINGS["unusual_flag"] in words.get(word, {}):
            words[word][SETTINGS["abbreviation_flag"]] = True
    for word, (kinds, ordinary) in profiles.items():
        if ordinary:
            demote_acronym(words, word, kinds)
        elif kinds:
            add(words, word, NAMES["acronym_flag"], kinds)


def demote_acronym(words: dict, word: str, kinds: list[str]) -> None:
    entry = words.get(word, {})
    carried = entry.pop(NAMES["acronym_flag"], [])
    found = kinds or [kind for kind in carried if kind not in NAMES["source_labels"]]
    if found:
        add(words, word, NAMES["acronym_mixed_flag"], found)


def drop_covered_spellings(words: dict) -> None:
    covered = (SETTINGS["abbreviation_flag"], SETTINGS["letter_names_flag"])
    for entry in words.values():
        if any(flag in entry for flag in covered):
            entry.pop(SETTINGS["unusual_flag"], None)


def drop_short_word_flags(words: dict) -> None:
    minimum = SETTINGS["kaikki"]["loan_minimum_letters"]
    for word, entry in words.items():
        if len(word) < minimum:
            entry.pop("loan", None)
        if len(word) == 1:
            entry.pop(SETTINGS["unusual_flag"], None)


def add_safety(words: dict, repository: Path) -> None:
    safety = SETTINGS["safety"]
    listed = set(read(repository, safety["raw_path"]).get("words", []))
    common = common_words(repository)
    categories = read(repository, SETTINGS["wiktionary"]["raw_path"]).get("categories", {})
    for word in listed:
        add(words, word, safety["flag"], ["profanity"])
    for name, kind in SAFETY_CATEGORIES.items():
        for word in categories.get(name, {}).get("members", []):
            if word not in listed and not is_common(word, common):
                add(words, word, safety["flag"], [kind])
