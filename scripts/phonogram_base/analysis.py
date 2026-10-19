from scripts.aligner.model import Model, SETTINGS as ALIGNER
from scripts.aligner.words import align_word

from .models import AlignmentEvidence, AnalysisStatus, Occurrence, Reason, WordAnalysis
from .normalize import blend_overlays, normalize, units
from . import syllables as syllable_rules
from .registry import Registry


def bases(phones: list[str]) -> list[str]:
    return [phone.rstrip("012") for phone in phones]


def source_reasons(word: str, pronunciation: list[str], alignment: list[list[str]],
                   known_phones: set[str], letters_only: bool) -> list[Reason]:
    reasons = []
    raw = [phone for _, token in alignment if token for phone in token.split("|")]
    if not alignment:
        reasons.append(Reason.Missing)
    if letters_only and (not word.isascii() or not word.isalpha()):
        reasons.append(Reason.Punctuation)
    if "".join(spelling for spelling, _ in alignment) != word or any(not row[0] for row in alignment):
        reasons.append(Reason.Spelling)
    if bases(raw) != bases(pronunciation):
        reasons.append(Reason.Pronunciation)
    if set(bases(raw) + bases(pronunciation)) - known_phones:
        reasons.append(Reason.Unknown)
    return reasons


def origin_reasons(word: str, flags: dict, settings: dict) -> list[Reason]:
    excluded = settings["origins"]["excluded_flags"]
    return [Reason.Abbreviation] if any(flags.get(name) for name in excluded) else []


def occurrence_reasons(word: str, pronunciation: list[str], occurrences: list[Occurrence]) -> list[Reason]:
    positions = [position for item in occurrences for span in item.spans for position in range(span.start, span.end)]
    phones = [phone for item in sorted(occurrences, key=lambda item: item.phone_start) for phone in item.phones]
    if sorted(positions) != list(range(len(word))) or bases(phones) != bases(pronunciation):
        return [Reason.Coverage]
    return []


def source_tokens(source: list[list[str]]) -> list[tuple[str, tuple[str, ...]]]:
    return [(letters, tuple(phone.rstrip(ALIGNER["stress_digits"]) for phone in token.split(ALIGNER["phone_separator"])) if token else ())
            for letters, token in source]


def model_alignment(word: str, pronunciation: list[str], source: list[list[str]],
                    model: Model) -> tuple[list[list[str]], AlignmentEvidence]:
    aligned = align_word(word, pronunciation, model)
    tokens, index = [], 0
    for letters, phones in aligned.units:
        tokens.append([letters, ALIGNER["phone_separator"].join(pronunciation[index:index + len(phones)])])
        index += len(phones)
    names = ALIGNER["evidence"]
    status = names["no_source"] if not source else (names["agrees"] if source_tokens(source) == aligned.units else names["differs"])
    confidence = ALIGNER["confidence"]["low" if aligned.weak_units else "high"]
    return tokens, AlignmentEvidence(status, round(aligned.score, 3), confidence, aligned.weak_units, aligned.backoff_units)


def analyze(word: str, pronunciation: list[str], alignment: list[list[str]], rank: int, weight: float,
            registry: Registry, settings: dict, known_phones: set[str], phonetic: dict | None = None,
            model: Model | None = None, origins: dict | None = None) -> WordAnalysis:
    evidence = None
    if model is not None:
        alignment, evidence = model_alignment(word, pronunciation, alignment, model)
    reasons = source_reasons(word, pronunciation, alignment, known_phones, model is None)
    reasons.extend(origin_reasons(word, (origins or {}).get(word, {}), settings))
    occurrences: list[Occurrence] = []
    notes: list[Reason] = []
    syllables = syllable_rules.phonetic(word, pronunciation, phonetic, settings)
    written = syllable_rules.written(word, pronunciation, settings)
    if not any(reason in reasons for reason in [Reason.Unknown, Reason.Missing, Reason.Spelling, Reason.Abbreviation]):
        items = units(alignment, pronunciation, Reason.Pronunciation not in reasons)
        occurrences = normalize(items, registry, settings["layers"]["base"])
        reasons.extend(occurrence_reasons(word, pronunciation, occurrences))
        notes = syllable_rules.warnings(word, written, len(syllables), occurrences)
        if model is not None and not word.isalpha():
            notes.append(Reason.Punctuation)
        occurrences = syllable_rules.assign(occurrences, syllables)
        occurrences.extend(blend_overlays(word, items, registry, settings["layers"]["overlay"]))
    status = AnalysisStatus.Excluded if reasons else AnalysisStatus.Consistent
    return WordAnalysis(word, status, list(dict.fromkeys(reasons)), pronunciation, written, occurrences,
                        rank, weight, evidence, syllables, list(dict.fromkeys(notes)))
