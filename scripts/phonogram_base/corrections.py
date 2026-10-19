import json
from pathlib import Path

DIGITS = "012"


def bases(phones: list[str]) -> tuple[str, ...]:
    return tuple(phone.rstrip(DIGITS) for phone in phones)


class Corrections:
    def __init__(self, entries: list[dict], settings: dict):
        actions = settings["pronunciation"]["correction_actions"]
        self.prefer: dict[str, list[str]] = {}
        self.drop: dict[str, set[tuple[str, ...]]] = {}
        for entry in entries:
            if entry["action"] == actions["prefer"]:
                self.prefer[entry["word"]] = entry["pronunciation"]
            elif entry["action"] == actions["drop"]:
                self.drop.setdefault(entry["word"], set()).add(bases(entry["pronunciation"]))

    @classmethod
    def load(cls, repository: Path, settings: dict) -> "Corrections":
        path = repository / settings["pronunciation"]["corrections_path"]
        return cls(json.loads(path.read_text())["entries"], settings)

    def apply(self, word: str, selected: list[str], variants: list[list[str]]) -> tuple[list[str], list[list[str]]]:
        dropped = self.drop.get(word, set())
        kept = [variant for variant in variants if bases(variant) not in dropped]
        if bases(selected) in dropped:
            selected, kept = (kept[0], kept[1:]) if kept else (selected, kept)
        preferred = self.prefer.get(word)
        if preferred is None:
            return selected, kept
        original = [] if bases(selected) in dropped else [selected]
        return preferred, original + [variant for variant in kept if bases(variant) != bases(selected)]
