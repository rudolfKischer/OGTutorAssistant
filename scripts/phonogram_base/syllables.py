import re
from dataclasses import replace
from pathlib import Path

from db_builder.og_syllable_divider import og_divide

from .models import Occurrence, PhoneticSyllable, Reason, Syllable


def bases(phones: list[str], digits: str) -> list[str]:
    return [phone.rstrip(digits) for phone in phones]


def written(word: str, pronunciation: list[str], settings: dict) -> list[Syllable]:
    digits = settings["syllables"]["unstressed_digits"]
    if sum(phone in settings["vowels"] for phone in bases(pronunciation, digits)) == 1:
        return [Syllable(word, 0, len(word))]
    result, position = [], 0
    for text in og_divide(word):
        result.append(Syllable(text, position, position + len(text)))
        position += len(text)
    return result


def load_table(path: Path, settings: dict) -> dict[str, list[list[list[str]]]]:
    rules = settings["syllables"]
    variant = re.compile(rules["variant_pattern"])
    table: dict[str, list[list[list[str]]]] = {}
    for line in path.read_text().splitlines():
        if line.startswith(rules["comment_prefix"]) or "  " not in line:
            continue
        name, phones = line.strip().split("  ", 1)
        syllables, current = [], []
        for phone in phones.split():
            if phone == rules["table_separator"]:
                syllables.append(current)
                current = []
            else:
                current.append(phone)
        syllables.append(current)
        table.setdefault(variant.sub("", name).lower(), []).append(syllables)
    return table


def from_table(pronunciation: list[str], candidates: list, settings: dict) -> list[PhoneticSyllable] | None:
    digits = settings["syllables"]["unstressed_digits"]
    target = bases(pronunciation, digits)
    for syllables in candidates:
        if bases([phone for syllable in syllables for phone in syllable], digits) != target:
            continue
        result, position = [], 0
        for syllable in syllables:
            result.append(PhoneticSyllable(position, position + len(syllable), settings["syllables"]["source_table"]))
            position += len(syllable)
        return result
    return None


def by_nuclei(pronunciation: list[str], settings: dict) -> list[PhoneticSyllable]:
    digits = settings["syllables"]["unstressed_digits"]
    vowels = [index for index, phone in enumerate(bases(pronunciation, digits)) if phone in settings["vowels"]]
    source = settings["syllables"]["source_rule"]
    if len(vowels) < 2:
        return [PhoneticSyllable(0, len(pronunciation), source)]
    cuts = [0] + [nucleus - 1 if nucleus - previous > 1 else nucleus for previous, nucleus in zip(vowels, vowels[1:])]
    cuts.append(len(pronunciation))
    return [PhoneticSyllable(start, end, source) for start, end in zip(cuts, cuts[1:])]


def phonetic(word: str, pronunciation: list[str], table: dict | None, settings: dict) -> list[PhoneticSyllable]:
    found = from_table(pronunciation, (table or {}).get(word, []), settings)
    return found or by_nuclei(pronunciation, settings)


def syllable_of(occurrence: Occurrence, syllables: list[PhoneticSyllable], previous: int) -> int:
    if occurrence.phone_end == occurrence.phone_start:
        return previous
    return next((index for index, item in enumerate(syllables) if item.phone_start <= occurrence.phone_start < item.phone_end), previous)


def assign(occurrences: list[Occurrence], syllables: list[PhoneticSyllable]) -> list[Occurrence]:
    result, previous = [], 0
    for occurrence in sorted(occurrences, key=lambda item: item.spans[0].start):
        previous = syllable_of(occurrence, syllables, previous)
        result.append(replace(occurrence, syllable=previous))
    return result


def warnings(word: str, segments: list[Syllable], phonetic_count: int, occurrences: list[Occurrence]) -> list[Reason]:
    result = []
    if "".join(segment.text for segment in segments) != word:
        result.append(Reason.Syllables)
    if len(segments) != phonetic_count:
        result.append(Reason.Count)
    boundaries = {segment.end for segment in segments[:-1]}
    if any(item.spans[0].start < boundary < item.spans[-1].end for item in occurrences for boundary in boundaries):
        result.append(Reason.Boundary)
    return result
