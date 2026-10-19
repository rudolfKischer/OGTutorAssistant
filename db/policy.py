import json

from sqlalchemy import and_, func, or_, select, true

from db.facets import facet_counts_within
from db.overlay import overlay_concepts, overlay_origin_flags, overlay_word_concepts, overlay_word_rarity
from db.tables import sight_words, words

RARE_PHONOGRAM_LIMIT = 15
RARITY_KINDS = ('phonogram', 'unmodeled')
ALLOWED_FLAGS = frozenset({'proper_noun', 'loan', 'acronym', 'abbreviation', 'letter_names', 'unusual_spelling', 'inappropriate'})
ABSOLUTE_FLAGS = ('inappropriate',)


def parse(raw: str | None) -> dict:
    try:
        policy = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    return policy if isinstance(policy, dict) else {}


def count(policy: dict, key: str) -> int:
    value = policy.get(key, 0)
    return value if isinstance(value, int) and value > 0 else 0


def flag_removals(policy: dict, skip: tuple = ()) -> list:
    removals = []
    for flag, limit in (policy.get('limits') or {}).items():
        if flag not in ALLOWED_FLAGS or flag in skip or not isinstance(limit, int) or limit < 0:
            continue
        flagged = words.c.id.in_(select(overlay_origin_flags.c.word_id).where(overlay_origin_flags.c.flag == flag))
        removals.append(and_(flagged, words.c.frequency_rank > limit))
    return removals


def removal_parts(policy: dict) -> list:
    parts = flag_removals(policy, ABSOLUTE_FLAGS)
    if count(policy, 'max_rank'):
        parts.append(words.c.frequency_rank > count(policy, 'max_rank'))
    if count(policy, 'rare'):
        parts.append(words.c.id.in_(select(overlay_word_rarity.c.word_id).where(overlay_word_rarity.c.weakest < count(policy, 'rare'))))
    return parts


def absolute_removal(policy: dict):
    limits = policy.get('limits') or {}
    chosen = [flag for flag in ABSOLUTE_FLAGS if limits.get(flag) == 0]
    if not chosen:
        return None
    return words.c.id.in_(select(overlay_origin_flags.c.word_id).where(overlay_origin_flags.c.flag.in_(chosen)))


def condition(raw: str | None):
    policy = parse(raw)
    parts = removal_parts(policy)
    protected = or_(words.c.frequency_rank <= count(policy, 'keep_top'), words.c.word.in_(select(sight_words.c.word)))
    base = or_(protected, ~or_(*parts)) if parts else true()
    absolute = absolute_removal(policy)
    return and_(~absolute, base) if absolute is not None else base


def group_counts(conn, groups: dict, kept) -> dict:
    result = {}
    for name, flags in groups.items():
        chosen = [flag for flag in flags if flag in ALLOWED_FLAGS]
        members = select(overlay_origin_flags.c.word_id).where(overlay_origin_flags.c.flag.in_(chosen))
        total = conn.execute(select(func.count()).select_from(words).where(words.c.id.in_(members))).scalar()
        left = conn.execute(select(func.count()).select_from(words).where(words.c.id.in_(members), kept)).scalar()
        result[name] = {'total': total, 'kept': left}
    return result


def preview(conn, raw: str | None, groups: dict | None = None) -> dict:
    kept = condition(raw)
    total_words, total_usage = conn.execute(select(func.count(), func.sum(words.c.frequency_per_million))).one()
    kept_words, kept_usage = conn.execute(select(func.count(), func.sum(words.c.frequency_per_million)).where(kept)).one()
    counts = conn.execute(
        select(overlay_word_concepts.c.concept, func.count())
        .join(overlay_concepts, overlay_concepts.c.concept == overlay_word_concepts.c.concept)
        .where(overlay_concepts.c.kind.in_(RARITY_KINDS), overlay_word_concepts.c.word_id.in_(select(words.c.id).where(kept)))
        .group_by(overlay_word_concepts.c.concept)).all()
    return {'words': kept_words, 'total_words': total_words, 'usage_share': (kept_usage or 0) / total_usage,
            'phonograms': len(counts), 'rare_phonograms': sum(1 for _, n in counts if n < RARE_PHONOGRAM_LIMIT),
            'groups': group_counts(conn, groups or {}, kept)}


EXAMPLE_COUNT = 5


def rank_scale(conn, ranks: list[int]) -> dict:
    ordinary = ~words.c.id.in_(select(overlay_origin_flags.c.word_id))
    scale = {}
    for rank in ranks:
        at = conn.execute(select(words.c.frequency_rank, words.c.frequency_per_million).where(words.c.frequency_rank >= max(rank, 1))
                          .order_by(words.c.frequency_rank).limit(1)).first()
        examples = conn.execute(select(words.c.word).where(ordinary, words.c.word.op('NOT GLOB')('*[^a-z]*'), words.c.frequency_rank <= max(rank, 1))
                                .order_by(words.c.frequency_rank.desc()).limit(EXAMPLE_COUNT)).scalars().all()
        scale[str(rank)] = {'rank': at[0] if at else None, 'per_million': at[1] if at else None, 'examples': examples}
    return scale


def present_concepts(conn, kept_ids) -> list[str]:
    concepts = conn.execute(select(overlay_word_concepts.c.concept.distinct()).where(overlay_word_concepts.c.word_id.in_(kept_ids))).scalars().all()
    facets = facet_counts_within(conn, kept_ids)
    return sorted(set(concepts) | {key for key, value in facets.items() if value})
