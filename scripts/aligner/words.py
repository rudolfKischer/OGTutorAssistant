from functools import lru_cache

import cmudict

from .model import Model, SETTINGS
from .viterbi import Aligned, NEGATIVE_INFINITY, align, strip

SEPARATOR = "-"
LOOSE_RATIO = 2


@lru_cache(maxsize=1)
def dictionary() -> dict:
    return cmudict.dict()


def variants(part: str) -> list[tuple[str, ...]]:
    return [tuple(strip(phone) for phone in entry) for entry in dictionary().get(part.lower(), [])]


def distance(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    row = list(range(len(right) + 1))
    for i, phone in enumerate(left, 1):
        previous, row[0] = row[0], i
        for j, other in enumerate(right, 1):
            previous, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, previous + (phone != other))
    return row[-1]


def mismatch(part: str, phones: tuple[str, ...]) -> int:
    known = variants(part)
    return min(distance(entry, phones) for entry in known) if known else 0


def safe_align(part: str, phones: tuple[str, ...], model: Model) -> Aligned | None:
    try:
        return align(part, list(phones), model)
    except KeyError:
        return None


def phone_range(part: str, remaining: int) -> range:
    low = max(1, len(part) // LOOSE_RATIO)
    return range(low, min(remaining, LOOSE_RATIO * len(part) + 1) + 1)


def join(pieces: list[Aligned]) -> Aligned:
    units: list = []
    for index, piece in enumerate(pieces):
        units.extend(([(SEPARATOR, ())] if index else []) + list(piece.units))
    return Aligned(units, sum(piece.score for piece in pieces), [letters for piece in pieces for letters in piece.weak_units],
                   sum(piece.backoff_units for piece in pieces))


def split_align(parts: list[str], phones: list[str], model: Model) -> Aligned | None:
    stripped = tuple(strip(phone) for phone in phones)
    memo: dict = {}

    def piece(index: int, start: int, end: int) -> tuple | None:
        key = (index, start, end)
        if key not in memo:
            aligned = safe_align(parts[index], stripped[start:end], model)
            memo[key] = None if aligned is None or aligned.score == NEGATIVE_INFINITY else (aligned, mismatch(parts[index], stripped[start:end]))
        return memo[key]

    best: dict = {(0, 0): ((0, 0.0), [])}
    for index, part in enumerate(parts):
        following: dict = {}
        for (done, start), ((missed, score), pieces) in best.items():
            for size in phone_range(part, len(stripped) - start):
                found = piece(index, start, start + size)
                if found is None:
                    continue
                value = (missed - found[1], score + found[0].score)
                key = (index + 1, start + size)
                if key not in following or value > following[key][0]:
                    following[key] = (value, pieces + [found[0]])
        best = following
    result = best.get((len(parts), len(stripped)))
    return join(result[1]) if result else None


def align_word(word: str, pronunciation: list[str], model: Model) -> Aligned:
    parts = word.split(SEPARATOR)
    if len(parts) > 1 and all(parts):
        joined = split_align(parts, pronunciation, model)
        if joined is not None:
            return joined
    return align(word, pronunciation, model)
