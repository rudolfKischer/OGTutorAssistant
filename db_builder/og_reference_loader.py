import json

from db.tables import og_phonemes, og_graphemes
from .mappings import _load_json


def load_og_reference(conn):
    """Load OG phoneme and grapheme reference data into DB."""
    print("Loading OG reference data...")

    arpa = _load_json('arpabet_to_og.json')
    phoneme_rows = [
        {'id': pid, 'sound': m['sound'], 'type': m['type'],
         'keyword': m['keyword'], 'voiced': int(m['voiced'])}
        for pid, m in arpa['og_phonemes'].items()
    ]
    conn.execute(og_phonemes.insert(), phoneme_rows)
    print(f"  {len(phoneme_rows)} phonemes")

    grapheme_data = _load_json('og_grapheme_spellings.json')
    grapheme_rows = [
        {'grapheme': g['grapheme'], 'phoneme_id': g['phoneme_id'],
         'category': g['category'], 'position': g['position'],
         'examples': json.dumps(g['examples']), 'notes': g.get('notes')}
        for g in grapheme_data
    ]
    conn.execute(og_graphemes.insert(), grapheme_rows)
    print(f"  {len(grapheme_rows)} grapheme-phoneme entries")

    conn.commit()
