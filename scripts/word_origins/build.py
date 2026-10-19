import json
from collections import Counter
from pathlib import Path

from scripts.aligner.model import Model, SETTINGS as ALIGNER
from scripts.aligner.train import common_counts, silent_contexts
from scripts.aligner.words import align_word

from scripts.letter_names import labels as letter_labels
from .merge import add_definition_abbreviations, add_safety, add_definition_names, drop_covered_spellings, drop_short_word_flags, add_kaikki, add_proper_nouns, add_wiktionary
from .settings import SETTINGS

UNIT_SEPARATOR = ", "


def spelled_with_letter_names(word: str, phones: list[str]) -> bool:
    return letter_labels(word, phones) is not None


def unit_text(letters: str, phones: tuple[str, ...]) -> str:
    return f"{letters} > {'+'.join(phones) or 'silent'}"


def silent_reasons(aligned, contexts: Counter) -> list[str]:
    start, reasons, previous = SETTINGS["start_marker"], [], SETTINGS["start_marker"]
    for letters, units in aligned.units:
        if not units and letters.isalpha() and contexts[(previous, letters)] < SETTINGS["rare_context_count"]:
            template = SETTINGS["silent_start_template" if previous == start else "silent_context_template"]
            reasons.append(template.format(letter=letters, previous=previous))
        previous = letters
    return reasons


def computed_flags(word: str, phones: list[str], model: Model, common: dict | None = None, contexts: Counter | None = None) -> dict:
    flags: dict = {}
    aligned = align_word(word, phones, model)
    spelled = letter_labels(word, phones)
    if spelled is not None:
        flags[SETTINGS["letter_names_flag"]] = spelled
    if aligned.backoff_units and len(word) <= SETTINGS["abbreviation_maximum_letters"]:
        flags[SETTINGS["abbreviation_flag"]] = True
    seen = (lambda letters, units: common.get((letters, units), 0)) if common is not None else model.count
    rare = [unit_text(letters, units) for letters, units in aligned.units if seen(letters, units) < SETTINGS["rare_unit_count"]]
    rare += [reason for reason in (silent_reasons(aligned, contexts) if contexts is not None else [])
             if unit_text(reason.split()[0], ()) not in rare]
    if rare:
        flags[SETTINGS["unusual_flag"]] = UNIT_SEPARATOR.join(dict.fromkeys(rare))
    return flags


def build(repository: Path) -> dict:
    raw = json.loads((repository / SETTINGS["raw_path"]).read_text())
    model = Model.load(repository / ALIGNER["model_path"])
    common = common_counts(repository, SETTINGS["common_rank"], SETTINGS["rank_column"])
    contexts = silent_contexts(repository, SETTINGS["common_rank"], SETTINGS["rank_column"], SETTINGS["start_marker"])
    words: dict[str, dict] = {}
    for word, phones, *_ in json.loads((repository / SETTINGS["words_path"]).read_text()):
        flags = computed_flags(word, phones, model, common, contexts)
        if flags:
            words[word] = flags
    for language, members in raw["languages"].items():
        for word in members:
            words.setdefault(word, {}).setdefault("loan", []).append(language)
    add_proper_nouns(words, repository, [row[0] for row in json.loads((repository / SETTINGS["words_path"]).read_text())])
    add_wiktionary(words, repository)
    add_kaikki(words, repository)
    add_definition_names(words, repository)
    add_safety(words, repository)
    add_definition_abbreviations(words, repository)
    drop_covered_spellings(words)
    drop_short_word_flags(words)
    words = {word: entry for word, entry in words.items() if entry}
    for entry in words.values():
        if "loan" in entry:
            entry["loan"] = sorted(set(entry["loan"]))
    counts: dict[str, int] = {}
    for entry in words.values():
        for key in entry:
            counts[key] = counts.get(key, 0) + 1
    return {"sources": [raw["source"]], "unusual_rule": f"alignment uses a letter-sound unit seen fewer than {SETTINGS['rare_unit_count']} times among the {SETTINGS['common_rank']} most frequent words",
            "counts": counts, "words": dict(sorted(words.items()))}
