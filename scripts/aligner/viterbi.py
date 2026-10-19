from dataclasses import dataclass

from .model import Model, SETTINGS

NEGATIVE_INFINITY = float("-inf")


@dataclass(frozen=True)
class Aligned:
    units: list[tuple[str, tuple[str, ...]]]
    score: float
    weak_units: list[str]
    backoff_units: int


def strip(phone: str) -> str:
    return phone.rstrip(SETTINGS["stress_digits"])


def transitions(model: Model, word: str, phones: list[str], i: int, j: int):
    following = phones[j] if j < len(phones) else None
    for width in range(1, SETTINGS["maximum_letters"] + 1):
        letters = word[i:i + width]
        if len(letters) < width:
            break
        yield letters, (), model.candidates(letters, None), 0
        if following is None:
            continue
        for unit in model.candidates(letters, following):
            size = len(unit.phones)
            if tuple(phones[j:j + size]) == unit.phones:
                yield letters, unit.phones, [unit], size


def backoff(letters: str, phone: str | None) -> float:
    if len(letters) != 1:
        return NEGATIVE_INFINITY
    return SETTINGS["backoff_silent"] if phone is None else SETTINGS["backoff_phone"]


def align(word: str, pronunciation: list[str], model: Model) -> Aligned:
    phones = [strip(phone) for phone in pronunciation]
    n, m = len(word), len(phones)
    best = [[NEGATIVE_INFINITY] * (m + 1) for _ in range(n + 1)]
    back: dict[tuple[int, int], tuple[int, int, str, tuple[str, ...], bool]] = {}
    best[0][0] = 0.0
    for i in range(n):
        for j in range(m + 1):
            if best[i][j] == NEGATIVE_INFINITY:
                continue
            relax(model, word, phones, best, back, i, j)
    return trace(model, word, best, back, n, m)


def relax(model: Model, word: str, phones: list[str], best: list, back: dict, i: int, j: int) -> None:
    for letters, unit_phones, units, size in transitions(model, word, phones, i, j):
        for unit in units:
            update(best, back, i, j, letters, unit.phones, unit.score, False, len(word))
    letter = word[i]
    update(best, back, i, j, letter, (), backoff(letter, None), True, len(word))
    for size in range(1, SETTINGS["backoff_maximum_phones"] + 1):
        if j + size > len(phones):
            break
        extra = SETTINGS["backoff_extra_phone"] * (size - 1)
        update(best, back, i, j, letter, tuple(phones[j:j + size]), backoff(letter, phones[j]) + extra, True, len(word))


def update(best: list, back: dict, i: int, j: int, letters: str, unit_phones: tuple, score: float, is_backoff: bool,
           length: int) -> None:
    ni, nj = i + len(letters), j + len(unit_phones)
    value = best[i][j] + score
    if not unit_phones:
        value -= SETTINGS["silent_tiebreak"] * (length - i)
    if value > best[ni][nj]:
        best[ni][nj] = value
        back[(ni, nj)] = (i, j, letters, unit_phones, is_backoff)


def trace(model: Model, word: str, best: list, back: dict, n: int, m: int) -> Aligned:
    units, weak, backoffs = [], [], 0
    i, j = n, m
    while (i, j) != (0, 0):
        previous_i, previous_j, letters, phones, is_backoff = back[(i, j)]
        units.append((letters, phones))
        backoffs += is_backoff
        if is_backoff or model.count(letters, phones) < SETTINGS["weak_unit_count"]:
            weak.append(letters)
        i, j = previous_i, previous_j
    units.reverse()
    return Aligned(units, best[n][m], weak[::-1], backoffs)
