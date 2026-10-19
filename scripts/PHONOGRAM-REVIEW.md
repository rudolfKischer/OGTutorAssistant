# Local phonogram review

This tool reads the authoring database and deployed cache. It does not change word data, eligibility, scopes, progress, or live services.

From `OGTutorAssistant`, build the evidence:

```sh
.venv/bin/python -B scripts/audit_phonogram_baseline.py --output ../notes/issue-10-phonograms/phase-0
```

From `StructuredLearningSoftwareMain`, compare all three engines:

```sh
node scripts/phonograms/run-parity.cjs --cache infra/data/production_cache.json --output ../notes/issue-10-phonograms/phase-0/parity.json
```

The runner imports the real worker, API engine, API index builder, and browser bitset engine. It does not call AWS or an LLM. It compares full normalized final pools, practice pools and focus counts before sampling.

From `OGTutorAssistant`, serve the review UI:

```sh
.venv/bin/python -B scripts/phonogram_review.py --report ../notes/issue-10-phonograms/phase-0
```

Open <http://127.0.0.1:5002>.

## Five checks for Rudolf

1. Search `vowel_team_ea`. One old ID becomes three exact spelling/sound entries.
2. Search `phoneme_k`. The c and k spellings are separate. Neither inherits an ambiguous learned bit.
3. Search `digraph_th`. Voiced and voiceless th are separate.
4. Switch source inventory to Classic template fixture. Search `phonogram_i_short_i`. Its old `i` means short-i phonics, while deployed-catalog `i` remains a sight word.
5. Inspect `head` and `cat` in the word form. These are the current source records, including the old broad tags. The six known generation failures are deliberately still shown as baseline failures.

Expand a source row to see why it maps that way. Reading and spelling transfer policies are shown independently. Source example buttons inspect current words; they are not claims about repaired or future word membership.

## Reproduce the checks

```sh
.venv/bin/python -B -m unittest discover -s tests -v
```

The full audit requires the local ignored source files, the sibling repositories, and the mapping CSVs in workspace notes. Missing inputs fail. The frozen lock detects changed inputs and changed detector output. The source DB is opened with `mode=ro` and `query_only`; its file hash is checked again after the audit.

CI runs the 25-word frozen detector fixture and invariant tests without needing the full ignored database. The API, worker and website each run the same checksum-pinned 16-case parity fixture. Website tests fail if its fixture differs from a sibling backend checkout. No workflow has been pushed or run remotely.

All work is isolated. Rudolf is the only phase gate. Do not contact other collaborators or deploy as part of this review.
