from dataclasses import dataclass
from enum import StrEnum


class Position(StrEnum):
    Initial = "initial"
    Final = "final"


class Direction(StrEnum):
    Reading = "reading"
    Spelling = "spelling"


@dataclass(frozen=True)
class PairDefinition:
    id: str
    spelling: str
    sounds: list[str]


@dataclass(frozen=True)
class Component:
    phonogram_id: str
    start: int
    end: int


@dataclass(frozen=True)
class Blend:
    id: str
    name: str
    kind: str
    spelling: str
    sounds: list[str]
    status: str
    context: Position
    components: list[Component]

    @classmethod
    def from_record(cls, record: dict) -> "Blend":
        return cls(record["id"], record["name"], record["kind"], record["spelling"],
                   record["sounds"], record["status"], Position(record["context"]),
                   [Component(**component) for component in record["components"]])


@dataclass(frozen=True)
class Selection:
    direction: Direction
    concept_id: str
    bundle_version: str


def validate_blends(blends: list[Blend], pairs: list[PairDefinition]) -> None:
    registry = {pair.id: pair for pair in pairs}
    if len({blend.id for blend in blends}) != len(blends):
        raise ValueError("Duplicate blend identifiers")
    for blend in blends:
        validate_blend(blend, registry)


def validate_blend(blend: Blend, registry: dict[str, PairDefinition]) -> None:
    cursor = 0
    sounds = []
    for component in blend.components:
        pair = registry[component.phonogram_id]
        if component.start != cursor or component.end <= cursor:
            raise ValueError("Blend components must cover consecutive positions")
        if blend.spelling[component.start:component.end] != pair.spelling:
            raise ValueError("Component spelling disagrees with blend positions")
        cursor = component.end
        sounds.extend(pair.sounds)
    if cursor != len(blend.spelling) or sounds != blend.sounds or not sounds:
        raise ValueError("Blend spelling and sound sequence must match its components")
