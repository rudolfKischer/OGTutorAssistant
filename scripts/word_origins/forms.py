from .settings import SETTINGS

MINIMUM_STEM = 3
STRIPS = SETTINGS["names"]["suffix_strips"]


def base_forms(word: str) -> set[str]:
    forms = {word}
    for suffix in STRIPS:
        if word.endswith(suffix) and len(word) - len(suffix) >= MINIMUM_STEM:
            stem = word[: -len(suffix)]
            forms.update({stem, stem + "e"})
    if word.endswith("ies"):
        forms.add(word[:-3] + "y")
    if len(word) > MINIMUM_STEM + 1 and word[-1] == word[-2]:
        forms.add(word[:-1])
    return forms
