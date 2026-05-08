import json

from flask import Flask, send_from_directory, jsonify, request
from sqlalchemy import select, func, and_, or_

from config import DB_PATH, FLASK_PORT, DEFAULT_WORD_LIMIT, MAX_WORD_LIMIT
from db.connection import get_engine
from db.tables import (
    words, word_phonemes, word_graphemes, word_syllables,
    word_pos, word_morphemes, word_concepts, word_definitions,
    sight_words, og_phonemes, og_graphemes,
)
from db.queries import batch_fetch, group_rows

app = Flask(__name__, static_folder='static')

engine = get_engine(DB_PATH)


SORT_ORDERS = {
    'frequency': words.c.frequency_zipf.desc(),
    'rank': words.c.frequency_rank.asc(),
    'alpha': words.c.word.asc(),
    'syllables': (words.c.syllable_count.asc(), words.c.frequency_zipf.desc()),
}


# --- Shared helpers ---

def _first_irregularity(sight_word_rows):
    for s in sight_word_rows:
        if s.irregularity_reason:
            return json.loads(s.irregularity_reason)
    return None


def _format_word_summary(row, maps):
    wid = row.id
    sw = maps['sight_words'].get(row.word, [])
    return {
        'word': row.word,
        'syllable_count': row.syllable_count,
        'frequency_zipf': row.frequency_zipf,
        'frequency_per_million': row.frequency_per_million,
        'frequency_rank': row.frequency_rank,
        'alignment': [[a.grapheme, a.og_phoneme_id] for a in maps['graphemes'].get(wid, [])],
        'syllables': [{'cv': s.cv_pattern, 'type': s.og_type} for s in maps['syllables'].get(wid, [])],
        'pos': maps['pos'].get(wid, []),
        'is_sight_word': len(sw) > 0,
        'sight_word_sources': [{'source': s.source, 'grade': s.grade_level} for s in sw],
        'irregularity_reasons': _first_irregularity(sw),
        'morphemes': [{'morpheme': m.morpheme, 'type': m.morpheme_type} for m in maps['morphemes'].get(wid, [])],
        'concepts': maps['concepts'].get(wid, []),
        'definition': maps['definitions'].get(wid),
    }


def _fetch_related_maps(conn, word_ids, word_rows):
    """Batch-fetch all related data for a set of words into lookup dicts."""
    return {
        'graphemes': batch_fetch(conn, word_graphemes, word_ids,
                                 order_by=(word_graphemes.c.word_id, word_graphemes.c.position)),
        'syllables': batch_fetch(conn, word_syllables, word_ids,
                                 order_by=(word_syllables.c.word_id, word_syllables.c.position)),
        'morphemes': batch_fetch(conn, word_morphemes, word_ids,
                                 order_by=(word_morphemes.c.word_id, word_morphemes.c.position)),
        'pos': batch_fetch(conn, word_pos, word_ids, val_fn=lambda r: r.pos),
        'concepts': batch_fetch(conn, word_concepts, word_ids,
                                order_by=(word_concepts.c.word_id, word_concepts.c.concept),
                                val_fn=lambda r: r.concept),
        'definitions': {
            row.word_id: row.definition
            for row in conn.execute(
                select(word_definitions).where(and_(
                    word_definitions.c.word_id.in_(word_ids),
                    word_definitions.c.position == 0,
                ))
            )
        },
        'sight_words': group_rows(
            conn,
            select(sight_words).where(sight_words.c.word.in_([r.word for r in word_rows])),
            key_fn=lambda r: r.word,
        ) if word_rows else {},
    }


def build_word_summary(conn, word_ids, word_rows):
    if not word_ids:
        return []
    maps = _fetch_related_maps(conn, word_ids, word_rows)
    return [_format_word_summary(r, maps) for r in word_rows]


# --- Search query builder ---


def _collect_search_filters(args):
    """Parse request args into (joins, conditions) lists.

    Concept filters are combined according to concept_mode (any/all/only).
    Refine filters (frequency, POS, sight word, syllable count, etc.) are
    always AND'd.
    """
    joins = []
    conditions = []

    concept_mode = args.get('concept_mode', 'any')
    concept_raw = args.get('concept')
    concept_list = [c.strip() for c in concept_raw.split(',') if c.strip()] if concept_raw else []

    if concept_list:
        if concept_mode == 'only':
            # Decodability: word's concepts must be a subset of selected set.
            # Adding more concepts always GROWS the result pool.
            wc_out = word_concepts.alias('wc_out')
            conditions.append(
                ~words.c.id.in_(
                    select(wc_out.c.word_id).where(
                        ~wc_out.c.concept.in_(concept_list)
                    )
                )
            )
        elif concept_mode == 'any':
            conditions.append(or_(*[
                words.c.id.in_(select(word_concepts.c.word_id).where(word_concepts.c.concept == c))
                for c in concept_list
            ]))
        elif concept_mode == 'all':
            for c in concept_list:
                conditions.append(
                    words.c.id.in_(select(word_concepts.c.word_id).where(word_concepts.c.concept == c))
                )

    # --- Refine filters: always AND'd ---
    syllables = args.get('syllables', default='')
    if syllables:
        if syllables.endswith('+'):
            conditions.append(words.c.syllable_count >= int(syllables[:-1]))
        else:
            conditions.append(words.c.syllable_count == int(syllables))

    syl_type = args.get('syl_type')
    if syl_type:
        ws_t = word_syllables.alias('ws_t')
        joins.append((ws_t, ws_t.c.word_id == words.c.id))
        conditions.append(ws_t.c.og_type == syl_type)

    cv_pattern = args.get('cv_pattern')
    if cv_pattern:
        ws_cv = word_syllables.alias('ws_cv')
        joins.append((ws_cv, ws_cv.c.word_id == words.c.id))
        conditions.append(ws_cv.c.cv_pattern == cv_pattern)

    min_zipf = args.get('min_zipf', type=float)
    if min_zipf is not None:
        conditions.append(words.c.frequency_zipf >= min_zipf)

    max_zipf = args.get('max_zipf', type=float)
    if max_zipf is not None:
        conditions.append(words.c.frequency_zipf <= max_zipf)

    min_per_million = args.get('min_per_million', type=float)
    if min_per_million is not None:
        conditions.append(words.c.frequency_per_million >= min_per_million)

    pos = args.get('pos')
    if pos:
        joins.append((word_pos, word_pos.c.word_id == words.c.id))
        conditions.append(word_pos.c.pos == pos)

    sight_word = args.get('sight_word')
    if sight_word == 'yes':
        joins.append((sight_words, sight_words.c.word == words.c.word))
    elif sight_word == 'no':
        conditions.append(~words.c.word.in_(select(sight_words.c.word)))

    morpheme = args.get('morpheme')
    morpheme_type = args.get('morpheme_type')
    if morpheme or morpheme_type:
        joins.append((word_morphemes, word_morphemes.c.word_id == words.c.id))
        if morpheme:
            conditions.append(word_morphemes.c.morpheme == morpheme)
        if morpheme_type:
            conditions.append(word_morphemes.c.morpheme_type == morpheme_type)

    return joins, conditions


def _apply_filters(base_query, joins, conditions):
    for table, on_clause in joins:
        base_query = base_query.join(table, on_clause)
    for cond in conditions:
        base_query = base_query.where(cond)
    return base_query


def build_search_query(args):
    joins, conditions = _collect_search_filters(args)
    query = _apply_filters(select(words).distinct(), joins, conditions)
    count_query = _apply_filters(select(func.count(words.c.id.distinct())), joins, conditions)
    return query, count_query


# --- Routes ---

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/concepts')
def get_concepts():
    with engine.connect() as conn:
        rows = conn.execute(
            select(word_concepts.c.concept, func.count(word_concepts.c.word_id).label('word_count'))
            .group_by(word_concepts.c.concept)
            .order_by(word_concepts.c.concept)
        ).fetchall()
    return jsonify([{'concept': r.concept, 'word_count': r.word_count} for r in rows])


@app.route('/api/phonemes')
def get_phonemes():
    with engine.connect() as conn:
        rows = conn.execute(select(og_phonemes)).fetchall()
    return jsonify([
        {'id': r.id, 'sound': r.sound, 'type': r.type,
         'keyword': r.keyword, 'voiced': bool(r.voiced)}
        for r in rows
    ])


@app.route('/api/graphemes')
def get_graphemes():
    with engine.connect() as conn:
        rows = conn.execute(
            select(og_graphemes, og_phonemes.c.sound)
            .outerjoin(og_phonemes, og_graphemes.c.phoneme_id == og_phonemes.c.id)
        ).fetchall()
    return jsonify([
        {'grapheme': r.grapheme, 'phoneme_id': r.phoneme_id,
         'sound': r.sound or r.phoneme_id, 'category': r.category,
         'position': r.position, 'examples': json.loads(r.examples), 'notes': r.notes}
        for r in rows
    ])


@app.route('/api/phoneme-stats')
def phoneme_stats():
    with engine.connect() as conn:
        ph_rows = conn.execute(select(og_phonemes)).fetchall()
        counts = {}
        for row in conn.execute(
            select(word_phonemes.c.og_phoneme_id,
                   func.count(word_phonemes.c.word_id.distinct()).label('ct'))
            .group_by(word_phonemes.c.og_phoneme_id)
        ):
            counts[row.og_phoneme_id] = row.ct
    return jsonify([
        {'id': r.id, 'sound': r.sound, 'type': r.type,
         'keyword': r.keyword, 'voiced': bool(r.voiced),
         'word_count': counts.get(r.id, 0)}
        for r in ph_rows
    ])


@app.route('/api/grapheme-stats')
def grapheme_stats():
    with engine.connect() as conn:
        gr_rows = conn.execute(
            select(og_graphemes, og_phonemes.c.sound)
            .outerjoin(og_phonemes, og_graphemes.c.phoneme_id == og_phonemes.c.id)
        ).fetchall()
        counts = {}
        for row in conn.execute(
            select(word_graphemes.c.grapheme,
                   func.count(word_graphemes.c.word_id.distinct()).label('ct'))
            .group_by(word_graphemes.c.grapheme)
        ):
            counts[row.grapheme] = row.ct
    return jsonify([
        {'grapheme': r.grapheme, 'phoneme_id': r.phoneme_id,
         'sound': r.sound or r.phoneme_id, 'category': r.category,
         'position': r.position, 'examples': json.loads(r.examples), 'notes': r.notes,
         'word_count': counts.get(r.grapheme, 0)}
        for r in gr_rows
    ])


@app.route('/api/feature-catalog')
def feature_catalog():
    """Return all concept IDs with their word counts."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(word_concepts.c.concept, func.count(word_concepts.c.word_id).label('ct'))
            .group_by(word_concepts.c.concept)
        ).fetchall()
    return jsonify({r.concept: r.ct for r in rows})


@app.route('/api/words')
def search_words():
    sort = request.args.get('sort', 'frequency')
    limit = min(request.args.get('limit', DEFAULT_WORD_LIMIT, type=int), MAX_WORD_LIMIT)
    offset = request.args.get('offset', 0, type=int)

    query, count_query = build_search_query(request.args)

    order = SORT_ORDERS.get(sort, words.c.frequency_zipf.desc())
    if isinstance(order, tuple):
        query = query.order_by(*order)
    else:
        query = query.order_by(order)

    query = query.limit(limit).offset(offset)

    with engine.connect() as conn:
        total = conn.execute(count_query).scalar()
        rows = conn.execute(query).fetchall()
        word_ids = [r.id for r in rows]
        result_words = build_word_summary(conn, word_ids, rows)

    return jsonify({'words': result_words, 'total': total, 'limit': limit, 'offset': offset})


# --- Word detail ---

def _assign_syllable_indices(alignment, syl_phoneme_counts):
    ph_idx = 0
    syl_idx = 0
    result = []
    for a in alignment:
        if a.grapheme == '-':
            result.append({
                'grapheme': '-', 'arpabet': a.arpabet,
                'og_phoneme_id': a.og_phoneme_id, 'silent': True,
                'syllable': syl_idx,
            })
            continue

        if a.is_silent:
            result.append({
                'grapheme': a.grapheme, 'arpabet': a.arpabet,
                'og_phoneme_id': a.og_phoneme_id, 'silent': True,
                'syllable': syl_idx,
            })
            continue

        syl_idx = _phoneme_to_syllable(ph_idx, syl_phoneme_counts)
        ph_count = len(a.arpabet.split('|')) if a.arpabet and '|' in a.arpabet else 1
        result.append({
            'grapheme': a.grapheme, 'arpabet': a.arpabet,
            'og_phoneme_id': a.og_phoneme_id, 'silent': False,
            'syllable': syl_idx,
        })
        ph_idx += ph_count

    return result


def _phoneme_to_syllable(ph_idx, syl_phoneme_counts):
    counter = 0
    for si, cnt in enumerate(syl_phoneme_counts):
        if ph_idx < counter + cnt:
            return si
        counter += cnt
    return len(syl_phoneme_counts) - 1


def _fetch_word_detail(conn, wid, word_text):
    """Fetch all detail data for a single word."""
    phonemes = conn.execute(
        select(word_phonemes).where(word_phonemes.c.word_id == wid)
        .order_by(word_phonemes.c.position)
    ).fetchall()

    alignment = conn.execute(
        select(word_graphemes).where(word_graphemes.c.word_id == wid)
        .order_by(word_graphemes.c.position)
    ).fetchall()

    syllables_info = conn.execute(
        select(word_syllables).where(word_syllables.c.word_id == wid)
        .order_by(word_syllables.c.position)
    ).fetchall()

    pos_tags = [r.pos for r in conn.execute(
        select(word_pos.c.pos).where(word_pos.c.word_id == wid)
    )]

    sw = conn.execute(
        select(sight_words).where(sight_words.c.word == word_text)
    ).fetchall()

    morphemes = conn.execute(
        select(word_morphemes).where(word_morphemes.c.word_id == wid)
        .order_by(word_morphemes.c.position)
    ).fetchall()

    concepts = [r.concept for r in conn.execute(
        select(word_concepts.c.concept).where(word_concepts.c.word_id == wid)
        .order_by(word_concepts.c.concept)
    )]

    definitions = conn.execute(
        select(word_definitions).where(word_definitions.c.word_id == wid)
        .order_by(word_definitions.c.position)
    ).fetchall()

    return phonemes, alignment, syllables_info, pos_tags, sw, morphemes, concepts, definitions


_VOWEL_BASES = {'AA','AE','AH','AO','AW','AY','EH','ER','EY','IH','IY','OW','OY','UH','UW'}


def _split_phoneme_counts(phonemes, alignment):
    has_hyphen = any(a.grapheme == '-' for a in alignment) if alignment else False
    arpabets = [p.arpabet for p in phonemes]

    if has_hyphen and alignment:
        segments = []
        count = 0
        for a in alignment:
            if a.grapheme == '-':
                segments.append(count)
                count = 0
            elif a.arpabet:
                count += len(a.arpabet.split('|'))
        segments.append(count)

        result = []
        offset = 0
        for seg_len in segments:
            seg = arpabets[offset:offset + seg_len]
            result.extend(_split_by_vowel(seg))
            offset += seg_len
        return result

    return _split_by_vowel(arpabets)


def _is_vowel_arpabet(arpabet):
    base = arpabet.rstrip('012')
    if base in _VOWEL_BASES:
        return True
    return '+' in base and any(p in _VOWEL_BASES for p in base.split('+'))


def _split_by_vowel(arpabets):
    counts = []
    count = 0
    for a in arpabets:
        count += 1
        if _is_vowel_arpabet(a):
            counts.append(count)
            count = 0
    if count and counts:
        counts[-1] += count
    elif count:
        counts.append(count)
    return counts


def _assign_syllable_indices_by_spelling(alignment, word, num_syllables):
    """Assign syllable indices to alignment entries using OG character boundaries."""
    from db_builder.og_syllable_divider import og_divide
    og_syls = og_divide(word)
    num_og = len(og_syls)

    # Build char→syllable map, accounting for hyphens in the original word
    char_to_syl = {}
    syl_idx_iter = 0
    word_pos = 0
    for si, syl in enumerate(og_syls):
        # Skip hyphens in the original word
        while word_pos < len(word) and word[word_pos] == '-':
            char_to_syl[word_pos] = si  # hyphen belongs to next syllable
            word_pos += 1
        for j in range(len(syl)):
            char_to_syl[word_pos] = si
            word_pos += 1

    # Build result, splitting graphemes that span syllable boundaries
    result = []
    char_pos = 0
    prev_syl = 0
    for a in alignment:
        if a.grapheme == '-':
            result.append({
                'grapheme': '-', 'arpabet': a.arpabet,
                'og_phoneme_id': a.og_phoneme_id, 'silent': True,
                'syllable': prev_syl,
            })
            char_pos += 1
            continue

        g_len = len(a.grapheme)
        first_syl = char_to_syl.get(char_pos, prev_syl)
        last_syl = char_to_syl.get(char_pos + g_len - 1, first_syl)

        if first_syl == last_syl:
            # Grapheme fits in one syllable
            result.append({
                'grapheme': a.grapheme, 'arpabet': a.arpabet,
                'og_phoneme_id': a.og_phoneme_id,
                'silent': bool(a.is_silent),
                'syllable': first_syl,
            })
        else:
            # Grapheme spans syllable boundary — split by syllable
            for si in range(first_syl, last_syl + 1):
                chars_in_syl = ''.join(
                    a.grapheme[j] for j in range(g_len)
                    if char_to_syl.get(char_pos + j, first_syl) == si
                )
                if chars_in_syl:
                    result.append({
                        'grapheme': chars_in_syl,
                        'arpabet': a.arpabet if si == first_syl else None,
                        'og_phoneme_id': a.og_phoneme_id,
                        'silent': bool(a.is_silent),
                        'syllable': si,
                    })

        if not a.is_silent:
            prev_syl = last_syl
        char_pos += g_len

    return result


def _format_word_detail(row, phonemes, alignment, syllables_info, pos_tags, sw, morphemes, concepts, definitions):
    num_syls = len(syllables_info)
    if num_syls > 0 and alignment:
        aligned = _assign_syllable_indices_by_spelling(alignment, row.word, num_syls)
    else:
        syl_phoneme_counts = _split_phoneme_counts(phonemes, alignment)
        aligned = _assign_syllable_indices(alignment, syl_phoneme_counts)
    return {
        'word': row.word,
        'syllable_count': row.syllable_count,
        'frequency_zipf': row.frequency_zipf,
        'frequency_per_million': row.frequency_per_million,
        'frequency_rank': row.frequency_rank,
        'phonemes': [{'arpabet': p.arpabet, 'og_id': p.og_phoneme_id} for p in phonemes],
        'alignment': aligned,
        'syllables': [{'cv': s.cv_pattern, 'type': s.og_type} for s in syllables_info],
        'pos': pos_tags,
        'is_sight_word': len(sw) > 0,
        'sight_word_sources': [{'source': s.source, 'grade': s.grade_level} for s in sw],
        'irregularity_reasons': _first_irregularity(sw),
        'morphemes': [{'morpheme': m.morpheme, 'type': m.morpheme_type} for m in morphemes],
        'concepts': concepts,
        'definitions': [{'pos': d.pos, 'definition': d.definition, 'example': d.example} for d in definitions],
    }


@app.route('/api/browse-counts')
def browse_counts():
    """Return dynamic concept counts for the browse panel.

    For 'any' mode: static counts suffice (no call needed).
    For 'all' mode: count of words matching current filters AND each concept.
    For 'only' mode: marginal counts — how many words each concept unlocks.
    """
    concept_mode = request.args.get('concept_mode', 'any')
    if concept_mode == 'any':
        return jsonify({'mode': 'any'})

    concept_raw = request.args.get('concept')
    concept_list = [c.strip() for c in concept_raw.split(',') if c.strip()] if concept_raw else []

    with engine.connect() as conn:
        joins, conditions = _collect_search_filters(request.args)
        base_ids = select(words.c.id.distinct())
        for table, on_clause in joins:
            base_ids = base_ids.join(table, on_clause)
        for cond in conditions:
            base_ids = base_ids.where(cond)

        base_total = conn.execute(
            select(func.count()).select_from(base_ids.subquery())
        ).scalar()

        concept_counts = {}

        if concept_mode == 'all':
            for row in conn.execute(
                select(word_concepts.c.concept, func.count(word_concepts.c.word_id.distinct()).label('ct'))
                .where(word_concepts.c.word_id.in_(base_ids))
                .group_by(word_concepts.c.concept)
            ):
                concept_counts[row.concept] = row.ct

        elif concept_mode == 'only':
            # Selected concepts show the current pool size
            for c in concept_list:
                concept_counts[c] = base_total

            # Unselected concepts: marginal count — words with exactly 1
            # missing concept that IS this concept
            if concept_list:
                missing_q = (
                    select(word_concepts.c.word_id, word_concepts.c.concept)
                    .where(~word_concepts.c.concept.in_(concept_list))
                ).cte('missing')
                single_missing = (
                    select(
                        missing_q.c.word_id,
                        func.min(missing_q.c.concept).label('needed')
                    )
                    .group_by(missing_q.c.word_id)
                    .having(func.count(missing_q.c.concept.distinct()) == 1)
                ).cte('single_missing')
                for row in conn.execute(
                    select(single_missing.c.needed, func.count().label('ct'))
                    .group_by(single_missing.c.needed)
                ):
                    concept_counts[row.needed] = row.ct
            else:
                # No concepts selected — marginal = words with ONLY this concept
                for row in conn.execute(
                    select(word_concepts.c.concept, func.count(word_concepts.c.word_id.distinct()).label('ct'))
                    .where(~word_concepts.c.word_id.in_(
                        select(word_concepts.c.word_id)
                        .group_by(word_concepts.c.word_id)
                        .having(func.count(word_concepts.c.concept.distinct()) > 1)
                    ))
                    .group_by(word_concepts.c.concept)
                ):
                    concept_counts[row.concept] = row.ct

            # Removal marginal: for each selected concept, how many current-pool
            # words have that concept (removing it would exclude them)
            if concept_list:
                base_sub = base_ids.subquery()
                wc_rm = word_concepts.alias('wc_rm')
                for row in conn.execute(
                    select(wc_rm.c.concept, func.count(wc_rm.c.word_id.distinct()).label('ct'))
                    .where(wc_rm.c.word_id.in_(select(base_sub.c.id)))
                    .where(wc_rm.c.concept.in_(concept_list))
                    .group_by(wc_rm.c.concept)
                ):
                    concept_counts[row.concept + '_remove'] = row.ct

    return jsonify({
        'mode': concept_mode,
        'base_total': base_total,
        'concepts': concept_counts,
    })


@app.route('/api/word/<word>')
def word_detail(word):
    with engine.connect() as conn:
        row = conn.execute(
            select(words).where(words.c.word == word.lower())
        ).fetchone()
        if not row:
            return jsonify({'error': 'Word not found'}), 404

        data = _fetch_word_detail(conn, row.id, row.word)

    return jsonify(_format_word_detail(row, *data))


if __name__ == '__main__':
    app.run(debug=True, port=FLASK_PORT)
