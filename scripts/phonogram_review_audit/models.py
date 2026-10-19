from dataclasses import dataclass


@dataclass(frozen=True)
class WordEvidence:
    word: str
    status: str
    rank: int
    weight: float
    reasons: str


@dataclass(frozen=True)
class Assessment:
    category: str
    status: str
    fix_ids: list[str]
    note: str


@dataclass(frozen=True)
class PatternReview:
    pattern_id: str
    spelling: str
    sounds: list[str]
    section: str
    group: str
    word_count: int
    excluded_words: int
    affected_frequency_weight: float
    consistent_examples: list[str]
    excluded_examples: list[str]
    assessment: Assessment


@dataclass(frozen=True)
class ReviewReport:
    bundle_version: str
    audit_version: str
    reviewed_patterns: int
    group_counts: dict[str, int]
    assessments: dict[str, int]
    unique_affected_words: int
    findings: list[PatternReview]
