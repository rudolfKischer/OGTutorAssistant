from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptRow:
    concept: str
    label: str
    kind: str
    family: str | None
    sort_key: str
    spelling: str
    sounds: list[str]
    tail: bool = False


@dataclass(frozen=True)
class PhonogramRow:
    ordinal: int
    concept: str
    layer: str
    syllable: int | None
    spelling: str
    sounds: list[str]
    spans: list[list[int]]
    phones: list[str]


@dataclass(frozen=True)
class AnalysisRow:
    word: str
    status: str
    reasons: list[str]
    syllables: list[list[int]]
    written: list[list[int]]
    warnings: list[str]
    phonograms: list[PhonogramRow]
