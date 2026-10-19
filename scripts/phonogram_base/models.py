from dataclasses import dataclass, field
from enum import StrEnum


class AnalysisStatus(StrEnum):
    Consistent = "consistent"
    Excluded = "excluded"


class PatternKind(StrEnum):
    Phonogram = "phonogram"
    Blend = "blend"
    Silent = "silent"
    Punctuation = "punctuation"


class Section(StrEnum):
    Teaching = "teaching"
    Review = "review"
    Silent = "silent"


class Reason(StrEnum):
    Missing = "missing_alignment"
    Spelling = "spelling_mismatch"
    Pronunciation = "pronunciation_mismatch"
    Unknown = "unknown_phoneme"
    Punctuation = "unsupported_spelling"
    Syllables = "syllable_reconstruction"
    Count = "syllable_count"
    Boundary = "syllable_boundary"
    Abbreviation = "initialism_or_abbreviation"
    Coverage = "incomplete_coverage"


@dataclass(frozen=True)
class Span:
    start: int
    end: int


@dataclass(frozen=True)
class Syllable:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class PhoneticSyllable:
    phone_start: int
    phone_end: int
    source: str


@dataclass(frozen=True)
class Unit:
    spelling: str
    phones: list[str]
    start: int
    end: int
    phone_start: int
    phone_end: int


@dataclass(frozen=True)
class Pattern:
    id: str
    spelling: str
    sounds: list[str]
    kind: PatternKind
    context: str
    definition_ids: list[str] = field(default_factory=list)
    curriculum: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Occurrence:
    pattern: Pattern
    spans: list[Span]
    phone_start: int
    phone_end: int
    phones: list[str]
    layer: str
    syllable: int | None = None


@dataclass(frozen=True)
class WordAnalysis:
    word: str
    status: AnalysisStatus
    reasons: list[Reason]
    pronunciation: list[str]
    syllables: list[Syllable]
    occurrences: list[Occurrence]
    frequency_rank: int
    frequency_weight: float
    evidence: "AlignmentEvidence | None" = None
    phonetic_syllables: list[PhoneticSyllable] = field(default_factory=list)
    warnings: list[Reason] = field(default_factory=list)


@dataclass(frozen=True)
class Definition:
    id: str
    spelling: str
    sounds: list[str]
    kind: PatternKind
    context: str = ""


@dataclass(frozen=True)
class PatternSummary:
    pattern: Pattern
    word_count: int
    excluded_words: int
    occurrence_count: int
    section: Section
    flags: list[str]


@dataclass(frozen=True)
class BaseSummary:
    bundle_version: str
    source_words: int
    consistent_words: int
    excluded_words: int
    excluded_frequency_share: float
    reasons: dict[str, int]
    sources: dict[str, str]
    rare_word_threshold: int
    patterns: list[PatternSummary]


@dataclass(frozen=True)
class AlignmentEvidence:
    status: str
    score: float
    confidence: str
    weak_units: list[str]
    backoff_units: int = 0


@dataclass
class PronunciationOption:
    ordinal: int
    source: str
    phones: list[str]
    senses: list[dict] = field(default_factory=list)
    analysis: "WordAnalysis | None" = None
