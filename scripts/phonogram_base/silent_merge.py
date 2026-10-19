from dataclasses import replace

from .models import Unit

LOOKBACK_SIZES = (2, 1)
LOOKAHEAD_SILENT = (2, 1)


def combine(units: list[Unit]) -> Unit:
    sounding = [unit for unit in units if unit.phones]
    phones = [phone for unit in sounding for phone in unit.phones]
    return replace(sounding[0], spelling="".join(unit.spelling for unit in units), start=units[0].start, end=units[-1].end,
                   phones=phones, phone_start=sounding[0].phone_start, phone_end=sounding[-1].phone_end)


def lookback(result: list[Unit], locked: set[int], unit: Unit, merges: frozenset[str]) -> int:
    for size in LOOKBACK_SIZES:
        group = result[-size:]
        slots = set(range(len(result) - size, len(result)))
        if len(group) == size and all(item.phones and item.spelling.isalpha() for item in group) and not slots & locked \
                and "".join(item.spelling for item in group) + unit.spelling in merges:
            return size
    return 0


def lookahead(items: list[Unit], index: int, protected: set[int], merges: frozenset[str]) -> int:
    for silent in LOOKAHEAD_SILENT:
        end = index + silent
        group = items[index:end + 1]
        if len(group) != silent + 1 or any(item.phones or not item.spelling.isalpha() for item in group[:-1]) or not group[-1].phones:
            continue
        if protected & set(range(index, end + 1)):
            continue
        if "".join(item.spelling for item in group) in merges:
            return silent
    return 0


def closes_word(items: list[Unit], index: int) -> bool:
    return index + 2 == len(items)


def prefers_suffix(items: list[Unit], index: int, protected: set[int], suffixes: frozenset[str]) -> bool:
    following = items[index + 1] if index + 1 < len(items) else None
    return following is not None and following.phones and index + 1 not in protected \
        and closes_word(items, index) and items[index].spelling + following.spelling in suffixes


def merge_silent(items: list[Unit], merges: frozenset[str], protected: set[int],
                 suffixes: frozenset[str] = frozenset()) -> tuple[list[Unit], set[int]]:
    result: list[Unit] = []
    locked: set[int] = set()
    index = 0
    while index < len(items):
        unit = items[index]
        mergeable = not unit.phones and index not in protected and unit.spelling.isalpha()
        suffix = mergeable and prefers_suffix(items, index, protected, suffixes)
        size = lookback(result, locked, unit, merges) if mergeable and not suffix else 0
        ahead = lookahead(items, index, protected, merges) if mergeable and not size else 0
        if size:
            result[-size:] = [combine(result[-size:] + [unit])]
        elif ahead:
            result.append(combine(items[index:index + ahead + 1]))
            index += ahead
        else:
            result.append(unit)
            if index in protected:
                locked.add(len(result) - 1)
        index += 1
    return result, locked
