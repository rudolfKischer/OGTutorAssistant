import cmudict

from .models import AlignmentAudit, Loss, WordInputs


def bases(sequence: list[str]) -> list[str]:
    return [sound.rstrip("012") for sound in sequence]


def loss(ids: set[int], inputs: WordInputs, example_limit: int) -> Loss:
    words = [word for word in inputs.words if word.id in ids]
    total = sum(word.frequency_per_million for word in inputs.words)
    weight = sum(word.frequency_per_million for word in words)
    return Loss(
        len(words), len(words) / len(inputs.words), weight, weight / total,
        [word.word for word in sorted(words, key=lambda word: word.frequency_rank)[:example_limit]],
    )


def audit_alignment(inputs: WordInputs, pronunciations: dict[str, list[str]],
                    alignments: dict[str, list[list[str | None]]], example_limit: int) -> AlignmentAudit:
    variants = cmudict.dict()
    strict, raw_bad, mechanical, alternatives, missing = set(), set(), set(), set(), set()
    for word in inputs.words:
        pairs = alignments.get(word.word)
        if not pairs:
            missing.add(word.id)
            continue
        raw = [sound for _, token in pairs if token for sound in token.split("|")]
        agrees = bases(raw) == bases(pronunciations[word.word])
        sounded = [sound for _, _, sound, silent in inputs.graphemes.get(word.id, [])
                   if sound and not silent]
        if sounded != inputs.phonemes.get(word.id, []):
            strict.add(word.id)
            if agrees:
                mechanical.add(word.id)
        if not agrees:
            raw_bad.add(word.id)
            options = variants.get(word.word, variants.get(word.word.replace("-", ""), []))
            if bases(raw) in [bases(option) for option in options]:
                alternatives.add(word.id)
    return AlignmentAudit(
        len(inputs.words), sum(word.frequency_per_million for word in inputs.words),
        loss(strict | missing, inputs, example_limit), loss(raw_bad | missing, inputs, example_limit),
        loss(mechanical, inputs, example_limit), loss(alternatives, inputs, example_limit),
        loss((raw_bad - alternatives) | missing, inputs, example_limit),
    )
