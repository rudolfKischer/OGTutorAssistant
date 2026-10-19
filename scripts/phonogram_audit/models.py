from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class TargetKind(StrEnum):
    Phonogram = "phonogram"
    Compound = "compound"
    SpellingRule = "spelling_rule"
    Morphology = "morphology"
    Structure = "structure"
    SyllableType = "syllable_type"
    SyllableDivision = "syllable_division"
    SightWord = "sight_word"
    TeachingBundle = "teaching_bundle"
    Analysis = "analysis"


class TargetStatus(StrEnum):
    Modeled = "modeled"
    NotModeled = "not_modeled"
    Deprecated = "deprecated"


@dataclass(frozen=True)
class AuditPaths:
    workspace: Path
    database: Path
    cache: Path
    catalog: Path
    mapping: Path
    target_catalog: Path
    output: Path


@dataclass(frozen=True)
class Word:
    id: int
    word: str
    syllable_count: int
    frequency_zipf: float
    frequency_per_million: float
    frequency_rank: int


@dataclass
class WordInputs:
    words: list[Word]
    graphemes: dict[int, list[tuple[str, str | None, str | None, int]]]
    phonemes: dict[int, list[str]]
    syllables: dict[int, list[dict[str, str]]]
    morphemes: dict[int, list[tuple[str, str]]]
    pos: dict[int, list[str]]


@dataclass(frozen=True)
class TagBaseline:
    local_words: int
    deployed_words: int
    concepts: int
    shared_words: int
    identical_words: int
    local_only: list[str]
    deployed_only: list[str]
    mismatches: list[str]
    tags_sha256: str


@dataclass(frozen=True)
class Loss:
    words: int
    word_share: float
    frequency_weight: float
    frequency_share: float
    examples: list[str]


@dataclass(frozen=True)
class AlignmentAudit:
    denominator_words: int
    denominator_frequency: float
    strict: Loss
    raw: Loss
    mechanical_candidates: Loss
    alternative_variant: Loss
    residual: Loss


@dataclass(frozen=True)
class Target:
    id: str
    name: str
    kind: TargetKind
    spelling: str
    sounds: list[str]
    status: TargetStatus
    members: list[str]
    context: str = ""


@dataclass(frozen=True)
class Mapping:
    namespace: str
    source_id: str
    source_name: str
    source_path: str
    targets: list[Target]
    action: str
    decoding: str
    encoding: str
    reason: str
    examples: list[str]


@dataclass(frozen=True)
class MappingAudit:
    source_rows: int
    target_rows: int
    phonogram_definitions: int
    namespaces: dict[str, int]
    inactive: list[str]
    errors: list[str]
    mappings: list[Mapping] = field(repr=False)


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class RepoState:
    name: str
    head: str
    branch: str


@dataclass(frozen=True)
class BaselineReport:
    schema_version: int
    phase: str
    generated_at: str
    repositories: list[RepoState]
    sources: list[SourceFile]
    tags: TagBaseline
    alignment: AlignmentAudit
    mapping: MappingAudit


@dataclass(frozen=True)
class BaselineLock:
    schema_version: int
    tags_sha256: str
    local_words: int
    shared_words: int
    deployed_words: int
    sources: list[SourceFile]

