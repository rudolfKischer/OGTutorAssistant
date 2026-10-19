import hashlib
import json
from dataclasses import replace

from .models import Definition, Pattern, PatternKind
from .sound_ids import canonical_sounds


class Registry:
    def __init__(self, definitions: list[Definition], curriculum: dict[str, list[str]],
                 merges: frozenset[str] = frozenset(), splits: frozenset[str] = frozenset(),
                 suffixes: frozenset[str] = frozenset()):
        definitions = [replace(item, sounds=canonical_sounds(item.sounds)) for item in definitions]
        self.definitions = definitions
        self.curriculum = curriculum
        self.merges = merges
        self.splits = splits
        self.suffixes = suffixes
        self.vowel_letters = frozenset(spelling[0] for spelling in splits) - {"y"}
        self.patterns: dict[str, Pattern] = {}
        self.maximum_spelling = max(len(definition.spelling) for definition in definitions)
        self.by_spelling: dict[str, list[Definition]] = {}
        for definition in definitions:
            self.by_spelling.setdefault(definition.spelling, []).append(definition)
            self.pattern(definition.spelling, definition.sounds, definition.kind, definition.context)

    def pattern(self, spelling: str, sounds: list[str], kind: PatternKind = PatternKind.Phonogram,
                context: str = "") -> Pattern:
        sounds = canonical_sounds(sounds)
        identity = json.dumps([spelling, sounds, kind, context], separators=(",", ":"))
        key = hashlib.sha256(identity.encode()).hexdigest()
        if key not in self.patterns:
            definitions = [definition for definition in self.definitions if
                           (definition.spelling, definition.sounds, definition.kind, definition.context)
                           == (spelling, sounds, kind, context)]
            identifiers = [definition.id for definition in definitions]
            names = sorted({name for identifier in identifiers for name in self.curriculum.get(identifier, [])})
            self.patterns[key] = Pattern(key, spelling, sounds, kind, context, identifiers, names)
        return self.patterns[key]

    def matches(self, spelling: str, sounds: list[str]) -> bool:
        return any(definition.sounds == canonical_sounds(sounds) and definition.kind == PatternKind.Phonogram
                   for definition in self.by_spelling.get(spelling, []))
