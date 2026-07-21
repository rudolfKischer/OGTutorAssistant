# Plan: Expose Morphology Units as Filterable Concepts

## Goal

Let a user pick items from the "Introduction to Morphology" scope (prefixes,
suffixes, bound roots) the same way they currently pick a phonics concept
(blend, vowel team, syllable type, ...) — as an entry in the concept
browse/filter panel, combinable with `any` / `all` / `only` logic and other
refine filters — and get back all matching words.

## Current architecture (recap)

Two separate tables already exist ([db/tables.py](../db/tables.py)):

- `word_concepts(word_id, concept)` — flat tag table. Populated by
  [concept_detector.py](../db_builder/concept_detector.py) /
  [concept_loader.py](../db_builder/concept_loader.py). Driven entirely by
  the concept catalog baked into that detector's code — there's no separate
  `concepts` table, just whatever strings the detector emits. This is what
  powers `/api/concepts`, `/api/feature-catalog`, the `concept`/`concept_mode`
  search filter, and the browse-panel marginal-count logic in
  [web_app.py](../web_app.py).
- `word_morphemes(word_id, position, morpheme, morpheme_type)` — ordered,
  typed decomposition (`prefix`/`root`/`suffix`), populated from MorphoLex by
  [morpheme_loader.py](../db_builder/morpheme_loader.py). Already filterable
  today via `/api/words?morpheme=re&morpheme_type=prefix`, but only as a
  single exact-string equality filter — no set logic, no browse panel entry,
  no catalog endpoint.

So the mechanism the user wants ("pick a concept, get a word list, combine
with others") already exists for `word_concepts`, not for `word_morphemes`.
The most direct path is to **generate new `word_concepts` rows derived from
`word_morphemes`**, rather than building a second, parallel filter UI for
morphemes.

## Data reality check (important — read before implementing)

I queried the actual MorphoLex-derived data
([data/morpholex_parsed.json](../data/morpholex_parsed.json), and the built
`word_morphemes` table in [data/words.db](../data/words.db)) against the
requested list. The curriculum's naming for prefixes/suffixes/roots does
**not** map 1:1 onto the literal strings MorphoLex stores. Three distinct
problems came up:

**1. Assimilated prefixes are normalized away.**
`con-` never appears as `"con"` in the data (0 matches) — MorphoLex encodes
it as `"co"` (484 matches, e.g. `construction → co+struct+ion`,
`compress → co+press`). Similarly `dis-` sometimes collapses to `"di"`
(`dissect → di+sect`). A concept for "con-" must match `{"con", "co", "com",
"col", "cor"}`, not a literal `"con"`.

**2. Some suffixes never exist as their taught spelling — only a collapsed form.**
`-tion`, `-ation`, `-sion` all collapse to a bare suffix `"ion"` in MorphoLex
(1,707 words use suffix `"ion"`; `"tion"`/`"ation"`/`"sion"` as literal
morpheme strings: 0 matches each). MorphoLex also never stores a `-ture`
root/suffix, or an `-ence` suffix at all. These four items **cannot** be
implemented as a `word_morphemes` lookup — they need to fall back to a
spelling-pattern check on the word itself (the same technique
`concept_detector.py` already uses for FLOSS/`-ng`/`-nk` endings), e.g. "word
ends in `tion`" / `ends in ture`, optionally gated by requiring the word to
already have an `"ion"` suffix morpheme (to keep it a real morphological
boundary, not a coincidental spelling).

**3. Some requested roots are barely decomposed at all — a real coverage gap.**
`-cur-` is the worst case: `concur`, `occur`, `recur`, `current` are all
stored as **monomorphemic** whole words in MorphoLex (root = `"concur"`,
`"occur"`, etc.), not `con+cur`. Literal `morpheme='cur'` matches exactly
**1 word** in the built DB. Likewise `respect`, `suspect`, `support`,
`insect`, `collect`, `correct`, `permit`, `curious`, `serious`, `stadium`
are all monomorphemic in MorphoLex despite having a visible prefix/root/
suffix — so `-spect-`, `-port-`, `-sect-`, `con-`(via `collect`/`correct`),
`per-`(via `permit`), `-ious`(via `curious`/`serious`), `-ium`(via `stadium`)
will all under-count relative to what a tutor would expect to see. This is a
MorphoLex data-quality limit, not something fixable in our code without
hand-curating an override word list for the worst-affected items (I'd
flag `-cur-` specifically as needing a small hand-curated word list rather
than relying on the derived data — the automatic yield will be close to
zero).

Actual counts I pulled from the built DB for the cleaner items (context for
sizing, not final): `s`→9,146 words, `ed`→4,200, `ing`→3,881, `er`→2,164,
`ion`→1,707, `ly`→1,280, `y`→1,171, `able`→511, `ious`→298, `ness`→318,
`ian`→195, `ful`→187, `less`→156, `ium`→38. Prefixes: `re`→770, `co`→484,
`un`→514, `dis`→352, `de`→337, `mis`→159, `pro`→159, `ex`→167, `sub`→106,
`trans`→71, `per`→60, `mid`→17. Roots: `act`→83, `duct`→97 (`duce`→0),
`ject`→55, `struct`→49, `fuse`→35 (`fus`→0), `tract`→36, `port`→61,
`spect`→35, `tort`→22, `sect`→24, `cur`→1, `ture`→0 (word-ending-in-`ture`
count via spelling pattern would be 79).

## Recommended approach

Add a **morphology concept-mapping table** + a small detector function, and
call it from the existing concept-generation pipeline so the new tags land
in `word_concepts` alongside everything else, for free, in the existing UI.

1. **New mapping file** — `db_builder/morphology_concepts.py`:
   A list of records, each either:
   - `{'id': 'morph_prefix_con', 'label': 'con-', 'kind': 'morpheme',
      'morpheme_type': 'prefix', 'match': ['con', 'co', 'com', 'col', 'cor']}`
     (morpheme-table lookup, possibly matching multiple surface spellings)
   - `{'id': 'morph_suffix_tion', 'label': '-tion', 'kind': 'spelling',
      'word_suffix': 'tion', 'requires_morpheme': ('suffix', 'ion')}`
     (spelling-pattern fallback, optionally gated by a real suffix boundary)

   This is the single place that encodes every judgment call above (which
   surface spellings count as "the same" prefix/root, which items need the
   spelling fallback). It's also the natural place to note `-cur-` as
   low-yield/needs manual word list.

2. **New detector** — `detect_morphology_concepts(word, morpheme_parts)` in
   `concept_detector.py`, called from `detect_concepts()` alongside the
   existing `_detect_*` calls (it already receives `morpheme_parts` as a
   parameter — currently only used for the `syllable_div_compound` check).
   For each mapping record: check morpheme-table membership or spelling
   pattern, and if it matches, add `concepts.add(record['id'])`.

3. **`concept_loader.py`** needs no changes — it already writes whatever
   `detect_concepts()` returns into `word_concepts`.

4. **`static/data/ui-config.json`** — add a `labels`/`colors` entry per new
   concept id, plus a new `conceptFamilies` group (e.g. `{"id": "morphology",
   "label": "Morphology", "group": "Morphology", "filter": [<all new ids>]}`)
   so the browse panel renders them as their own section, matching the
   pattern already used for `blend_initial`, `vowel_team`, etc. "Introduction
   to Morphology" itself is a lesson-title, not a concept — it becomes the
   section's group label, not a taggable item.

5. **Rebuild the DB** — rerun `python build_word_db.py` (drops and rebuilds
   `data/words.db` from scratch, including the new concept rows). No schema
   migration needed since we're not touching table structure, only what
   values land in the existing `concept` column.

### Why not just use the existing `/api/words?morpheme=...&morpheme_type=...` filter as-is?

It already technically works today for a single exact-string match, with
zero code changes. But it can't express: multiple surface spellings as one
concept (plurals = `s` OR `es`; `con-` = `con`/`co`/`com`/...), the
spelling-pattern items (`-tion`/`-sion`/`-ation`/`-ture`), combination with
other concepts via `any`/`all`/`only`, or a catalog/word-count entry in the
browse panel. Recommending against building the whole feature on top of it.

### Why not a query-time alias layer instead of writing new rows?

Considered: keep `word_concepts` untouched and have `_collect_search_filters`
translate a `concept=morph_prefix_re` into a `word_morphemes` join
dynamically. Rejected — it would need per-concept special-case logic in the
query builder (mirroring the mapping table anyway), and would break the flat
`/api/concepts` / `/api/feature-catalog` counting queries and the `only`-mode
marginal-count logic, which all assume `word_concepts` is a plain group-by-able
tag column. Writing derived rows once at build time is simpler and keeps
every existing endpoint working unmodified.

## Full mapping table (curriculum item → concept id → mechanism)

| Curriculum item | concept id | mechanism | match | Notes |
|---|---|---|---|---|
| Introduction to Morphology | *(n/a — section header)* | — | — | Not a taggable concept; becomes the UI group label |
| Plurals (-s, -es) | `morph_suffix_plural` | morpheme | suffix `s`, `es` | |
| -ing | `morph_suffix_ing` | morpheme | suffix `ing` | (list had "iing", treated as typo) |
| -ed | `morph_suffix_ed` | morpheme | suffix `ed` | |
| -er | `morph_suffix_er` | morpheme | suffix `er` | |
| -ful | `morph_suffix_ful` | morpheme | suffix `ful` | |
| -less | `morph_suffix_less` | morpheme | suffix `less` | |
| -est | `morph_suffix_est` | morpheme | suffix `est` | |
| -y | `morph_suffix_y` | morpheme | suffix `y` | |
| -ly | `morph_suffix_ly` | morpheme | suffix `ly` | |
| -ness | `morph_suffix_ness` | morpheme | suffix `ness` | |
| re- | `morph_prefix_re` | morpheme | prefix `re` | |
| pre- | `morph_prefix_pre` | morpheme | prefix `pre` | |
| un- | `morph_prefix_un` | morpheme | prefix `un` | |
| -tion | `morph_suffix_tion` | spelling | word ends `tion`, gate: has suffix `ion` | collapses in data |
| -ation | `morph_suffix_ation` | spelling | word ends `ation`, gate: has suffix `ion` | collapses in data |
| -ject- | `morph_root_ject` | morpheme | root `ject` | |
| -struct- | `morph_root_struct` | morpheme | root `struct` | |
| -act- | `morph_root_act` | morpheme | root `act` | |
| -tract- | `morph_root_tract` | morpheme | root `tract` | under-counts (`attract` stored whole) |
| -spect- | `morph_root_spect` | morpheme | root `spect` | under-counts (`respect`/`suspect` stored whole) |
| pro- | `morph_prefix_pro` | morpheme | prefix `pro` | |
| ex- | `morph_prefix_ex` | morpheme | prefix `ex` | |
| -sion | `morph_suffix_sion` | spelling | word ends `sion`, gate: has suffix `ion` | collapses in data |
| -ence | `morph_suffix_ence` | spelling | word ends `ence` | never appears as a morpheme at all |
| -duce- | `morph_root_duce` | morpheme | root `duce`, `duct` | canonical spelling is `duct` |
| -tur(e) | `morph_root_ture` | spelling | word ends `ture` | never decomposed as a morpheme |
| -port- | `morph_root_port` | morpheme | root `port` | under-counts (`support` stored whole) |
| -tort- | `morph_root_tort` | morpheme | root `tort` | |
| -able | `morph_suffix_able` | morpheme | suffix `able` | |
| -sect- | `morph_root_sect` | morpheme | root `sect` | under-counts (`insect` stored whole) |
| con- | `morph_prefix_con` | morpheme | prefix `con`, `co`, `com`, `col`, `cor` | assimilated forms |
| sub- | `morph_prefix_sub` | morpheme | prefix `sub` | |
| de- | `morph_prefix_de` | morpheme | prefix `de` | |
| mid- | `morph_prefix_mid` | morpheme | prefix `mid` | |
| mis- | `morph_prefix_mis` | morpheme | prefix `mis` | |
| trans- | `morph_prefix_trans` | morpheme | prefix `trans` | |
| dis- | `morph_prefix_dis` | morpheme | prefix `dis`, `di` | assimilated form |
| per- | `morph_prefix_per` | morpheme | prefix `per` | under-counts (`permit`/`percent` stored whole) |
| -cur- | `morph_root_cur` | **manual list** | — | MorphoLex barely decomposes this (1 word); needs a small hand-curated word list (`concur`, `occur`, `recur`, `current`, `curriculum`, ...) rather than a derived rule |
| -fus(e)- | `morph_root_fuse` | morpheme | root `fuse`, `fus` | `confuse` stored whole (under-counts slightly) |
| -able (2nd listing) | *(dup of above)* | — | — | list has `-able` twice |
| -ious | `morph_suffix_ious` | morpheme | suffix `ious` | under-counts (`curious`/`serious` stored whole) |
| -ian | `morph_suffix_ian` | morpheme | suffix `ian` | |
| -ium | `morph_suffix_ium` | morpheme | suffix `ium` | under-counts (`stadium`/`premium` stored whole) |

## Implementation steps

1. Write `db_builder/morphology_concepts.py` with the mapping table above.
2. Add `detect_morphology_concepts()` to `concept_detector.py`; wire into
   `detect_concepts()`.
3. Add labels/colors + a `morphology` conceptFamily to `static/data/ui-config.json`.
4. Hand-curate the `-cur-` word list (small, ~10-20 words) as a constant in
   the mapping file.
5. Rerun `python build_word_db.py`; check the printed concept-count summary
   for the new `morph_*` ids against the table above as a sanity check.
6. Spot-check in the running app: pick each new concept in the browse panel,
   confirm returned words actually contain that morpheme, and confirm
   `any`/`all`/`only` combine correctly with existing phonics concepts.

## Effort estimate

- Mapping file + detector function: small, mechanical (~1-2 hrs).
- ui-config.json additions: small (~30 min).
- `-cur-` manual list curation + spot-checking under-counted items
  (`-tract-`, `-spect-`, `-port-`, `-sect-`, `-ious`, `-ium`, `per-`, `con-`)
  against real words to decide if any need their own manual overrides: this
  is the long pole — budget a review pass rather than assuming the automated
  rule is "done" for these ~8 items.
- Full DB rebuild: a few minutes, no manual steps.
