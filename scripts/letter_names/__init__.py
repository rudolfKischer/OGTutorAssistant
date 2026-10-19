import json
from pathlib import Path

DATA = json.loads(Path(__file__).with_name("names.json").read_text())
LETTERS = DATA["letters"]
PLURAL = DATA["plural"]
STRESS_DIGITS = "012"


def bases(phones: list[str]) -> list[str]:
    return [phone.rstrip(STRESS_DIGITS) for phone in phones]


def match(letters: str, phones: list[str]) -> list[str] | None:
    if not letters:
        return [] if not phones else None
    for sounds in LETTERS[letters[0]]["sounds"]:
        if phones[: len(sounds)] != sounds:
            continue
        rest = match(letters[1:], phones[len(sounds):])
        if rest is not None:
            return [LETTERS[letters[0]]["label"]] + rest
    return None


def labels(word: str, phones: list[str]) -> list[str] | None:
    if len(word) < 2 or any(letter not in LETTERS for letter in word):
        return None
    spoken = bases(phones)
    whole = match(word, spoken)
    if whole is not None:
        return whole
    if word.endswith(PLURAL["letter"]) and spoken[-1:] in PLURAL["sounds"]:
        stem = match(word[:-1], spoken[:-1])
        return None if stem is None else stem + [PLURAL["label"]]
    return None
