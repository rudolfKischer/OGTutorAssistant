import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import cmudict


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.phonogram_base.analysis import analyze
from scripts.phonogram_base.inputs import load_registry, words
from scripts.phonogram_base.syllables import load_table
from scripts.aligner.model import Model, SETTINGS as ALIGNER
from scripts.phonogram_base.corrections import Corrections
from scripts.phonogram_base.pronunciations import analyze_options, load_heteronyms, options_for
from scripts.phonogram_base.storage import BaseWriter


SETTINGS_PATH = REPOSITORY / "scripts/phonogram_base/settings.json"


def snapshots(settings: dict) -> dict[str, str]:
    paths = [REPOSITORY / value for value in settings["word_sources"] + settings["definition_sources"]]
    paths += [SETTINGS_PATH, REPOSITORY / "data/mappings/arpabet_to_og.json",
              REPOSITORY / "db_builder/og_syllable_divider.py", REPOSITORY / "db_builder/phoneme_converter.py",
              REPOSITORY.parent / "notes/issue-10-phonograms/phase-0/baseline.json"]
    paths += list((REPOSITORY / "scripts/phonogram_base").rglob("*.py"))
    paths += list((REPOSITORY / "scripts/phonogram_base").rglob("*.sql"))
    paths += list((REPOSITORY / "scripts/aligner").rglob("*.py")) + [REPOSITORY / "scripts/aligner/settings.json", REPOSITORY / ALIGNER["model_path"]]
    paths.append(Path(__file__).resolve())
    result = {}
    for path in paths:
        with path.open("rb") as stream:
            result[str(path.relative_to(REPOSITORY.parent))] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def populate(writer: BaseWriter, settings: dict) -> None:
    pronunciations = {row[0]: row[1] for row in json.loads((REPOSITORY / "data/words.json").read_text())}
    alignments = json.loads((REPOSITORY / "data/g2p_aligned.json").read_text())
    mappings = json.loads((REPOSITORY / "data/mappings/arpabet_to_og.json").read_text())
    registry = load_registry(REPOSITORY, settings)
    for pattern in registry.patterns.values():
        writer.add_pattern(pattern)
    dictionary = cmudict.dict()
    heteronyms = load_heteronyms(REPOSITORY, settings)
    corrections = Corrections.load(REPOSITORY, settings)
    origins = json.loads((REPOSITORY / settings["origins"]["path"]).read_text())["words"]
    known = set(mappings["arpabet_to_og"])
    phonetic = load_table(REPOSITORY / settings["phonetic_syllables_path"], settings)
    model = Model.load(REPOSITORY / ALIGNER["model_path"])
    for word, rank, weight in words(REPOSITORY):
        alignment = alignments.get(word, [])
        selected, variants = corrections.apply(word, pronunciations[word], dictionary.get(word, []))
        analysis = analyze(word, selected, alignment, rank, weight, registry, settings, known, phonetic, model, origins)
        options = options_for(word, selected, variants, heteronyms.get(word), settings)
        if len(options) > 1:
            analyze_options(options, analysis, word, alignment, registry, settings, known, phonetic, model, origins)
        writer.add(analysis)
        if len(options) > 1:
            writer.add_pronunciations(word, options)


def build(output: Path, settings: dict):
    sources = snapshots(settings)
    if output.resolve() in [(REPOSITORY.parent / source).resolve() for source in sources]:
        raise ValueError("The output cannot overwrite an input")
    version = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(dir=output.parent, suffix=".sqlite")
    os.close(handle)
    temporary = Path(temporary_name)
    writer = BaseWriter(temporary)
    try:
        try:
            populate(writer, settings)
            if snapshots(settings) != sources:
                raise ValueError("Source data changed while building the inventory")
            summary = writer.summarize(version, sources, settings)
            writer.finish(summary)
        finally:
            writer.close()
        temporary.replace(output)
        return summary
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    settings = json.loads(SETTINGS_PATH.read_text())
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(settings["database"]))
    parser.add_argument("--report-directory", type=Path, required=True)
    arguments = parser.parse_args()
    summary = build(arguments.output, settings)
    arguments.report_directory.mkdir(parents=True, exist_ok=True)
    (arguments.report_directory / settings["summary_output"]).write_text(json.dumps(asdict(summary), indent=2) + "\n")
    print(json.dumps(dict(words=summary.source_words, consistent=summary.consistent_words,
                          excluded=summary.excluded_words, patterns=len(summary.patterns),
                          excluded_frequency_share=summary.excluded_frequency_share)))


if __name__ == "__main__":
    main()
