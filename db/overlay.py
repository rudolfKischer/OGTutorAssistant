import json
import os

from sqlalchemy import Column, Integer, MetaData, Table, Text, event, select

from config import EXPLORER_CONCEPTS_PATH, EXPLORER_CONCEPTS_SCHEMA

SCHEMA = EXPLORER_CONCEPTS_SCHEMA
_metadata = MetaData(schema=SCHEMA)

overlay_word_concepts = Table('word_concepts', _metadata,
    Column('word_id', Integer, primary_key=True), Column('concept', Text, primary_key=True))
overlay_concepts = Table('concepts', _metadata,
    Column('concept', Text, primary_key=True), Column('label', Text), Column('kind', Text),
    Column('family', Text), Column('sort_key', Text), Column('spelling', Text), Column('sounds', Text), Column('tail', Integer))
overlay_families = Table('families', _metadata,
    Column('family', Text, primary_key=True), Column('label', Text), Column('grp', Text),
    Column('ordinal', Integer), Column('collapsed', Integer), Column('lens', Text))
overlay_concept_sounds = Table('concept_sounds', _metadata,
    Column('concept', Text, primary_key=True), Column('sound', Text, primary_key=True))
overlay_facet_counts = Table('facet_counts', _metadata,
    Column('concept', Text, primary_key=True), Column('words', Integer))
overlay_analysis = Table('word_analysis', _metadata,
    Column('word_id', Integer, primary_key=True), Column('status', Text), Column('reasons', Text),
    Column('syllables', Text), Column('written', Text), Column('warnings', Text))
overlay_phonograms = Table('word_phonograms', _metadata,
    Column('word_id', Integer, primary_key=True), Column('ordinal', Integer, primary_key=True),
    Column('concept', Text), Column('layer', Text), Column('syllable', Integer), Column('spelling', Text), Column('sounds', Text),
    Column('spans', Text), Column('phones', Text))
overlay_sounds = Table('sounds', _metadata,
    Column('sound', Text, primary_key=True), Column('plain', Text), Column('dictionary', Text),
    Column('ipa', Text), Column('example', Text))
overlay_heteronyms = Table('heteronyms', _metadata,
    Column('word_id', Integer, primary_key=True), Column('sources', Text), Column('senses', Text), Column('link', Text), Column('confidence', Text))
overlay_pronunciations = Table('pronunciations', _metadata,
    Column('word_id', Integer, primary_key=True), Column('ordinal', Integer, primary_key=True),
    Column('source', Text), Column('sounds', Text), Column('senses', Text), Column('analysis', Text))
overlay_origin_flags = Table('word_origin_flags', _metadata,
    Column('word_id', Integer, primary_key=True), Column('flag', Text, primary_key=True), Column('detail', Text))
overlay_word_rarity = Table('word_rarity', _metadata,
    Column('word_id', Integer, primary_key=True), Column('weakest', Integer))
overlay_meta = Table('meta', _metadata, Column('key', Text, primary_key=True), Column('value', Text))


def overlay_available() -> bool:
    return os.path.exists(EXPLORER_CONCEPTS_PATH)


def attach_overlay(engine) -> None:
    @event.listens_for(engine, 'connect')
    def _attach(dbapi_conn, _):
        dbapi_conn.execute(f"ATTACH DATABASE '{EXPLORER_CONCEPTS_PATH}' AS {SCHEMA}")


def concept_catalog(conn) -> list[dict]:
    rows = conn.execute(select(overlay_concepts)).fetchall()
    return [{'concept': r.concept, 'label': r.label, 'kind': r.kind, 'family': r.family,
             'sort_key': r.sort_key, 'spelling': r.spelling, 'sounds': json.loads(r.sounds), 'tail': bool(r.tail)} for r in rows]


def family_catalog(conn) -> list[dict]:
    rows = conn.execute(select(overlay_families).order_by(overlay_families.c.ordinal)).fetchall()
    return [{'id': r.family, 'label': r.label, 'group': r.grp, 'collapsed': bool(r.collapsed), 'lens': r.lens} for r in rows]


def word_phonogram_detail(conn, word_id: int) -> dict:
    analysis = conn.execute(select(overlay_analysis).where(overlay_analysis.c.word_id == word_id)).fetchone()
    rows = conn.execute(select(overlay_phonograms).where(overlay_phonograms.c.word_id == word_id)
                        .order_by(overlay_phonograms.c.ordinal)).fetchall()
    return {
        'status': analysis.status if analysis else None,
        'reasons': json.loads(analysis.reasons) if analysis else [],
        'syllables': json.loads(analysis.syllables) if analysis else [],
        'written': json.loads(analysis.written) if analysis else [],
        'warnings': json.loads(analysis.warnings) if analysis else [],
        'phonograms': [{'concept': r.concept, 'layer': r.layer, 'syllable': r.syllable, 'spelling': r.spelling,
                        'sounds': json.loads(r.sounds), 'spans': json.loads(r.spans),
                        'phones': json.loads(r.phones)} for r in rows],
    }


def sound_catalog(conn) -> dict:
    rows = conn.execute(select(overlay_sounds)).fetchall()
    return {r.sound: {'plain': r.plain, 'dictionary': r.dictionary, 'ipa': r.ipa, 'example': r.example} for r in rows}


def word_pronunciations(conn, word_id: int) -> dict:
    hetero = conn.execute(select(overlay_heteronyms).where(overlay_heteronyms.c.word_id == word_id)).fetchone()
    rows = conn.execute(select(overlay_pronunciations).where(overlay_pronunciations.c.word_id == word_id)
                        .order_by(overlay_pronunciations.c.ordinal)).fetchall()
    origin_rows = conn.execute(select(overlay_origin_flags).where(overlay_origin_flags.c.word_id == word_id)).fetchall()
    return {
        'origins': {r.flag: r.detail for r in origin_rows},
        'heteronym': {'sources': json.loads(hetero.sources), 'senses': json.loads(hetero.senses), 'link': hetero.link, 'confidence': hetero.confidence} if hetero else None,
        'pronunciations': [{'ordinal': r.ordinal, 'source': r.source, 'sounds': json.loads(r.sounds),
                            'senses': json.loads(r.senses), 'analysis': json.loads(r.analysis)} for r in rows],
    }
