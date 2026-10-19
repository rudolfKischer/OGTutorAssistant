import json
from pathlib import Path

TABLE = json.loads(Path(__file__).with_name("ipa-arpabet.json").read_text())
SEQUENCES = sorted(TABLE["sequences"], key=len, reverse=True)
VOWELS = set(TABLE["vowels"])
STRESS = TABLE["stress"]
SEQUENCE_LENGTH = max(len(key) for key in SEQUENCES)


def phones_at(text: str, index: int) -> tuple[list[str], int]:
    for key in SEQUENCES:
        if text.startswith(key, index):
            return TABLE["sequences"][key], len(key)
    symbol = text[index]
    return TABLE["symbols"].get(symbol, []), 1


def to_arpabet(ipa: str) -> list[str] | None:
    result: list[str] = []
    pending = STRESS["none"]
    index = 0
    while index < len(ipa):
        symbol = ipa[index]
        if symbol in (TABLE["primary"], TABLE["secondary"]):
            pending = STRESS["primary"] if symbol == TABLE["primary"] else STRESS["secondary"]
            index += 1
            continue
        if symbol in TABLE["ignored"]:
            index += 1
            continue
        phones, width = phones_at(ipa, index)
        if not phones:
            return None
        for phone in phones:
            if phone in VOWELS:
                result.append(phone + pending)
                pending = STRESS["none"]
            else:
                result.append(phone)
        index += width
    return result or None
