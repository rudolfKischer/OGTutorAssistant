import json
import re
from pathlib import Path

import cmudict

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())
ACTIONS = SETTINGS["actions"]
DIGITS = SETTINGS["stress_digits"]


def bases(phones: list[str]) -> list[str]:
    return [phone.rstrip(DIGITS) for phone in phones]


def in_prefix_entries(words: dict[str, list[str]]) -> list[dict]:
    rule = SETTINGS["in_prefix"]
    pattern = re.compile(rule["pattern"])
    result = []
    for word, phones in words.items():
        if not pattern.match(word) or len(phones) < 2:
            continue
        if bases(phones)[0] != rule["vowel"] or bases(phones)[1] in rule["missing"]:
            continue
        fixed = phones[:1] + [rule["insert"]] + phones[1:]
        result.append(dict(word=word, action=ACTIONS["prefer"], pronunciation=fixed, rule=rule["rule"], reason=rule["reason"]))
    return result


def extra_z_entries(dictionary: dict) -> list[dict]:
    rule = SETTINGS["extra_final_z"]
    result = []
    for word, variants in dictionary.items():
        if word.endswith(tuple(rule["skip_endings"])):
            continue
        keys = {tuple(bases(variant)) for variant in variants}
        for variant in variants:
            if bases(variant)[-1:] == [rule["extra"]] and tuple(bases(variant)[:-1]) in keys:
                result.append(dict(word=word, action=ACTIONS["drop"], pronunciation=variant, rule=rule["rule"], reason=rule["reason"]))
    return result


def build(repository: Path) -> dict:
    words = {row[0]: row[1] for row in json.loads((repository / SETTINGS["words_path"]).read_text())}
    dictionary = {word: variants for word, variants in cmudict.dict().items() if word in words}
    entries = in_prefix_entries(words) + extra_z_entries(dictionary) + SETTINGS["manual"]
    entries.sort(key=lambda entry: (entry["word"], entry["action"]))
    return {"description": "Dictionary pronunciation corrections. prefer: make this the main pronunciation and keep the dictionary one as an alternate. drop: remove this dictionary variant.",
            "entries": entries}
