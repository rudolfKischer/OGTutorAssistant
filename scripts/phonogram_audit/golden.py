import json
from pathlib import Path

from db_builder.concept_detector import detect_concepts

from .models import WordInputs


def sample_records(inputs: WordInputs, tags: dict[str, list[str]], words: list[str]) -> list[dict]:
    selected = set(words)
    records = []
    for word in inputs.words:
        if word.word not in selected:
            continue
        arguments = [word.word, inputs.graphemes.get(word.id, []), inputs.phonemes.get(word.id, []),
                     [[] for _ in range(word.syllable_count)], inputs.syllables.get(word.id, []),
                     inputs.morphemes.get(word.id, [])]
        if detect_concepts(*arguments) != tags[word.word]:
            raise ValueError(f"Sample requires global base-word context: {word.word}")
        records.append(dict(word=word.word, arguments=arguments, expected=tags[word.word]))
    return records


def check_golden(path: Path) -> list[str]:
    records = json.loads(path.read_text())
    return [record["word"] for record in records
            if detect_concepts(*record["arguments"]) != record["expected"]]
