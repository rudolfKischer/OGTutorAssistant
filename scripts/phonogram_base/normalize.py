from db_builder.phoneme_converter import convert_phoneme_sequence

from .models import Occurrence, PatternKind, Span, Unit
from .registry import Registry
from .silent_merge import merge_silent
from .sound_ids import canonical_sounds


def sounds(phones: list[str]) -> list[str]:
    return canonical_sounds([sound for _, sound in convert_phoneme_sequence(phones)])


def units(alignment: list[list[str]], pronunciation: list[str], consistent: bool) -> list[Unit]:
    result = []
    position = phone_position = 0
    for spelling, token in alignment:
        raw = token.split("|") if token else []
        phones = pronunciation[phone_position:phone_position + len(raw)] if consistent else raw
        result.append(Unit(spelling, phones, position, position + len(spelling),
                           phone_position, phone_position + len(raw)))
        position += len(spelling)
        phone_position += len(raw)
    return result


def split_vowel_at(items: list[Unit], index: int, registry: Registry, layer: str, consumed: set[int]) -> Occurrence | None:
    unit = items[index]
    if unit.spelling != "e" or unit.phones or index < 2 or {index - 2, index - 1, index} & consumed:
        return None
    vowel, consonant = items[index - 2], items[index - 1]
    if len(vowel.spelling) != 1 or len(consonant.spelling) != 1 or not consonant.phones or not vowel.phones:
        return None
    if consonant.spelling in registry.vowel_letters:
        return None
    spelling = vowel.spelling + "_e"
    if vowel.spelling + consonant.spelling + "e" in registry.merges:
        return None
    if spelling not in registry.splits and not registry.matches(spelling, sounds(vowel.phones)):
        return None
    pattern = registry.pattern(spelling, sounds(vowel.phones))
    return Occurrence(pattern, [Span(vowel.start, vowel.end), Span(unit.start, unit.end)],
                      vowel.phone_start, vowel.phone_end, vowel.phones, layer)


def split_vowels(items: list[Unit], registry: Registry, layer: str) -> tuple[list[Occurrence], set[int]]:
    occurrences: list[Occurrence] = []
    consumed: set[int] = set()
    for index in range(len(items)):
        occurrence = split_vowel_at(items, index, registry, layer, consumed)
        if occurrence is not None:
            occurrences.append(occurrence)
            consumed |= {index - 2, index}
    return occurrences, consumed


def longest_match(items: list[Unit], index: int, consumed: set[int], registry: Registry) -> int:
    chosen = index + 1
    spelling = ""
    phones = []
    for end in range(index, len(items)):
        if end in consumed:
            break
        spelling += items[end].spelling
        if len(spelling) > registry.maximum_spelling:
            break
        phones.extend(items[end].phones)
        if registry.matches(spelling, sounds(phones)):
            chosen = end + 1
    return chosen


def pattern_kind(spelling: str, phones: list[str]) -> PatternKind:
    if phones:
        return PatternKind.Phonogram
    return PatternKind.Silent if any(character.isalpha() for character in spelling) else PatternKind.Punctuation


def normalize(items: list[Unit], registry: Registry, layer: str) -> list[Occurrence]:
    occurrences, consumed = split_vowels(items, registry, layer)
    items, consumed = merge_silent(items, registry.merges, consumed, registry.suffixes)
    index = 0
    while index < len(items):
        if index in consumed:
            index += 1
            continue
        end = longest_match(items, index, consumed, registry)
        group = items[index:end]
        phones = [phone for item in group for phone in item.phones]
        spelling = "".join(item.spelling for item in group)
        kind = pattern_kind(spelling, phones)
        pattern = registry.pattern(spelling, sounds(phones), kind)
        occurrences.append(Occurrence(pattern, [Span(group[0].start, group[-1].end)],
                                      group[0].phone_start, group[-1].phone_end, phones, layer))
        index = end
    return sorted(occurrences, key=lambda occurrence: occurrence.spans[0].start)


def blend_overlays(word: str, items: list[Unit], registry: Registry, layer: str) -> list[Occurrence]:
    result = []
    for definition in registry.definitions:
        if definition.kind != PatternKind.Blend:
            continue
        start = 0 if definition.context == "initial" else len(word) - len(definition.spelling)
        end = start + len(definition.spelling)
        group = [item for item in items if item.start >= start and item.end <= end]
        phones = [phone for item in group for phone in item.phones]
        if "".join(item.spelling for item in group) != definition.spelling or sounds(phones) != definition.sounds:
            continue
        pattern = registry.pattern(definition.spelling, definition.sounds, definition.kind, definition.context)
        result.append(Occurrence(pattern, [Span(start, end)], group[0].phone_start, group[-1].phone_end, phones, layer))
    return result
