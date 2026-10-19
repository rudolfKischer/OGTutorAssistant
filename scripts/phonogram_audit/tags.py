import hashlib
import json
from collections import defaultdict

from db_builder import concept_loader
from db_builder.concept_detector import detect_concepts

from .models import TagBaseline, WordInputs


def invert(concept_words: dict[str, list[str]]) -> dict[str, set[str]]:
    tags = defaultdict(set)
    for concept, words in concept_words.items():
        for word in words:
            tags[word].add(concept)
    return dict(tags)


def current_tags(inputs: WordInputs) -> dict[str, list[str]]:
    bases = (
        concept_loader._compute_111_base_words(inputs.words, inputs.phonemes, inputs.pos),
        concept_loader._compute_final_e_base_words(inputs.words, inputs.pos),
        concept_loader._compute_final_y_base_words(inputs.words, inputs.pos),
        concept_loader._compute_211_base_words(
            inputs.words, inputs.syllables, inputs.pos,
            concept_loader._load_final_syllable_stress(),
        ),
    )
    return {
        word.word: detect_concepts(
            word.word, inputs.graphemes.get(word.id, []), inputs.phonemes.get(word.id, []),
            [[] for _ in range(word.syllable_count)], inputs.syllables.get(word.id, []),
            inputs.morphemes.get(word.id, []), *bases,
        ) for word in inputs.words
    }


def audit_tags(current: dict[str, list[str]], deployed: dict[str, set[str]]) -> TagBaseline:
    common = current.keys() & deployed.keys()
    mismatches = sorted(word for word in common if set(current[word]) != deployed[word])
    canonical = json.dumps(current, sort_keys=True, separators=(",", ":"))
    return TagBaseline(
        len(current), len(deployed), len({tag for tags in current.values() for tag in tags}),
        len(common), len(common) - len(mismatches), sorted(current.keys() - deployed.keys()),
        sorted(deployed.keys() - current.keys()), mismatches,
        hashlib.sha256(canonical.encode()).hexdigest(),
    )
