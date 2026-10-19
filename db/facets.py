import json
from pathlib import Path

from sqlalchemy import func, select

from db.overlay import overlay_concept_sounds, overlay_concepts, overlay_facet_counts, overlay_word_concepts

SETTINGS = json.loads(Path(__file__).resolve().parents[1].joinpath('scripts/explorer_concepts/settings.json').read_text())['facets']
GRAPHEME = SETTINGS['prefixes']['grapheme']
PHONEME = SETTINGS['prefixes']['phoneme']


def is_facet(token: str) -> bool:
    return token.startswith((GRAPHEME, PHONEME))


def expand_token(conn, token: str) -> list[str]:
    if token.startswith(GRAPHEME):
        query = select(overlay_concepts.c.concept).where(
            overlay_concepts.c.kind.in_(SETTINGS['source_kinds']), overlay_concepts.c.spelling == token[len(GRAPHEME):])
    elif token.startswith(PHONEME):
        query = select(overlay_concept_sounds.c.concept).where(overlay_concept_sounds.c.sound == token[len(PHONEME):])
    else:
        return [token]
    return [row[0] for row in conn.execute(query)]


def selection_terms(conn, tokens: list[str], enabled: bool) -> list[list[str]]:
    if not enabled:
        return [[token] for token in tokens]
    return [expand_token(conn, token) for token in tokens]


def facet_catalog_counts(conn) -> dict[str, int]:
    return {row.concept: row.words for row in conn.execute(select(overlay_facet_counts))}


def facet_counts_within(conn, base_ids) -> dict[str, int]:
    word = overlay_word_concepts
    graphemes = conn.execute(
        select(overlay_concepts.c.spelling, func.count(word.c.word_id.distinct()))
        .join(word, word.c.concept == overlay_concepts.c.concept)
        .where(overlay_concepts.c.kind.in_(SETTINGS['source_kinds']), word.c.word_id.in_(base_ids))
        .group_by(overlay_concepts.c.spelling))
    sounds = conn.execute(
        select(overlay_concept_sounds.c.sound, func.count(word.c.word_id.distinct()))
        .join(word, word.c.concept == overlay_concept_sounds.c.concept)
        .where(word.c.word_id.in_(base_ids))
        .group_by(overlay_concept_sounds.c.sound))
    result = {GRAPHEME + spelling: count for spelling, count in graphemes}
    result.update({PHONEME + sound: count for sound, count in sounds})
    return result
