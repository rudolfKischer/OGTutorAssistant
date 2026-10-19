from .models import Assessment


def assessment_for(record: dict, group: str, settings: dict) -> Assessment:
    category = category_for(record, group, settings)
    data = settings["assessments"][category]
    return Assessment(category, data["status"], data["fix_ids"], data["note"])


def category_for(record: dict, group: str, settings: dict) -> str:
    pattern = record["pattern"]
    spelling, sounds = pattern["spelling"], pattern["sounds"]
    if group == "defined_unobserved" and sounds == ["y", "long_oo"]:
        return "canonical_alias"
    if group == "silent_punctuation":
        return "silent_punctuation"
    if pattern["kind"] == "silent":
        return "silent_grouping"
    if [spelling, sounds] in settings["consonant_le_pairs"]:
        return "consonant_le"
    if [spelling, sounds] in settings["exception_pairs"]:
        return "exception"
    if len(sounds) > 1 and settings["letter_names"].get(spelling) == sounds:
        return "letter_name"
    if record["pattern"]["definition_ids"]:
        return "defined_rare"
    for rule in settings["overrides"]:
        if spelling in rule["spellings"]:
            return rule["category"]
    if group == "excluded_only":
        return "excluded_evidence"
    return "unresolved"
