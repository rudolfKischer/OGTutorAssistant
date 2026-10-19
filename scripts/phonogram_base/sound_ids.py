import json
from pathlib import Path


ALIAS_PATH = Path(__file__).resolve().parents[2] / "data/mappings/phonogram-sound-aliases.json"
ALIASES = json.loads(ALIAS_PATH.read_text())["aliases"]


def canonical_sounds(sounds: list[str]) -> list[str]:
    return [component for sound in sounds for component in ALIASES.get(sound, [sound])]
