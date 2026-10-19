import re


def group_for(record: dict, groups: list[dict]) -> str:
    facts = {
        "section": record["section"],
        "defined": bool(record["pattern"]["definition_ids"]),
        "observed": record["word_count"] > 0,
        "excluded": record["excluded_words"] > 0,
        "rare": "rare" in record["flags"],
        "punctuation": bool(re.search(r"[^a-z_]", record["pattern"]["spelling"])),
    }
    for group in groups:
        if all(facts[key] == expected for key, expected in group["conditions"].items()):
            return group["id"]
    raise ValueError(record["pattern"]["id"])
