import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

SETTINGS = json.loads(Path(__file__).with_name("settings.json").read_text())


@dataclass(frozen=True)
class Unit:
    letters: str
    phones: tuple[str, ...]
    count: int
    score: float


class Model:
    def __init__(self, counts: dict[tuple[str, tuple[str, ...]], int]):
        self.total = sum(counts.values())
        self.counts = counts
        self.by_start: dict[tuple[str, str | None], list[Unit]] = defaultdict(list)
        self.phones = sorted({phone for _, phones in counts for phone in phones})
        for (letters, phones), count in counts.items():
            unit = Unit(letters, phones, count, math.log(count / self.total))
            self.by_start[(letters, phones[0] if phones else None)].append(unit)

    def candidates(self, letters: str, first_phone: str | None) -> list[Unit]:
        return self.by_start.get((letters, first_phone), [])

    def count(self, letters: str, phones: tuple[str, ...]) -> int:
        return self.counts.get((letters, phones), 0)

    def save(self, path: Path) -> None:
        rows = sorted(([letters, SETTINGS["phone_separator"].join(phones), count]
                       for (letters, phones), count in self.counts.items()), key=lambda row: (-row[2], row[0], row[1]))
        path.write_text(json.dumps({"units": len(rows), "total": self.total, "rows": rows}, separators=(",", ":")) + "\n")

    @classmethod
    def load(cls, path: Path) -> "Model":
        data = json.loads(path.read_text())
        separator = SETTINGS["phone_separator"]
        counts = {(letters, tuple(phones.split(separator)) if phones else ()): count for letters, phones, count in data["rows"]}
        return cls(counts)
