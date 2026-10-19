from dataclasses import dataclass, field


@dataclass(frozen=True)
class Sense:
    source: str
    ipa: str
    part_of_speech: str
    meaning: str
    kind: str = ""


@dataclass
class Heteronym:
    spelling: str
    sources: list[str] = field(default_factory=list)
    senses: list[Sense] = field(default_factory=list)
