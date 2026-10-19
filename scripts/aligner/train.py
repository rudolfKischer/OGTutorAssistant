import json
from collections import Counter
from pathlib import Path

from .model import Model, SETTINGS
from .viterbi import strip


def tokens(token: str | None) -> tuple[str, ...]:
    if not token:
        return ()
    return tuple(strip(phone) for phone in token.split(SETTINGS["phone_separator"]))


def trusted(alignment: list, pronunciation: list[str]) -> bool:
    raw = [phone for _, token in alignment for phone in tokens(token)]
    return bool(alignment) and raw == [strip(phone) for phone in pronunciation]


def read_seeds(path: Path) -> Counter:
    if not path.exists():
        return Counter()
    return Counter({(row["letters"], tuple(row["phones"])): row["count"] for row in json.loads(path.read_text())["units"]})


def train(repository: Path, excluded: set[str] | None = None) -> Model:
    excluded = excluded or set()
    pronunciations = {row[0]: row[1] for row in json.loads((repository / SETTINGS["source_words"]).read_text())}
    alignments = json.loads((repository / SETTINGS["source_alignments"]).read_text())
    counts: Counter = read_seeds(repository / SETTINGS["seeds_path"])
    for word, alignment in alignments.items():
        if word in excluded or word not in pronunciations or not trusted(alignment, pronunciations[word]):
            continue
        if "".join(letters for letters, _ in alignment) != word:
            continue
        counts.update((letters, tokens(token)) for letters, token in alignment)
    return Model(dict(counts))


def common_counts(repository: Path, maximum_rank: int, rank_column: int) -> Counter:
    rows = json.loads((repository / SETTINGS["source_words"]).read_text())
    alignments = json.loads((repository / SETTINGS["source_alignments"]).read_text())
    counts: Counter = Counter()
    for row in rows:
        word, pronunciation = row[0], row[1]
        alignment = alignments.get(word)
        if row[rank_column] > maximum_rank or not alignment or not trusted(alignment, pronunciation):
            continue
        counts.update((letters, tokens(token)) for letters, token in alignment)
    return counts


def silent_contexts(repository: Path, maximum_rank: int, rank_column: int, start: str) -> Counter:
    rows = json.loads((repository / SETTINGS["source_words"]).read_text())
    alignments = json.loads((repository / SETTINGS["source_alignments"]).read_text())
    counts: Counter = Counter()
    for row in rows:
        alignment = alignments.get(row[0])
        if row[rank_column] > maximum_rank or not alignment or not trusted(alignment, row[1]):
            continue
        previous = start
        for letters, token in alignment:
            if not tokens(token):
                counts[(previous, letters)] += 1
            previous = letters
    return counts
