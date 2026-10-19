from collections import Counter

RARE_LIMIT = 15
SETTING_KEYS = ("keep_top", "rare_phonogram_min", "maximum_rank")


def flag_limits(policy: dict) -> dict:
    return {key: value for key, value in policy.items() if key not in SETTING_KEYS}


def keeps(rank: int, flags: set[str], policy: dict, protected: bool = False) -> bool:
    if protected or rank <= policy.get("keep_top", 0):
        return True
    if policy.get("maximum_rank") and rank > policy["maximum_rank"]:
        return False
    for flag, limit in flag_limits(policy).items():
        if flag in flags and (limit == 0 or (limit is not None and rank > limit)):
            return False
    return True


def kept_ids(data: dict, policy: dict) -> list[int]:
    words = data["words"]
    kept = [word_id for word_id, item in words.items() if keeps(item[1], data["flags"].get(word_id, set()), policy, word_id in data["sight"])]
    minimum = policy.get("rare_phonogram_min", 0)
    while minimum:
        counts = Counter(concept for word_id in kept for concept in data["concepts"].get(word_id, ()))
        weak = {concept for concept, count in counts.items() if count < minimum}
        survivors = [w for w in kept if w in data["sight"] or words[w][1] <= policy.get("keep_top", 0) or not data["concepts"].get(w, set()) & weak]
        if len(survivors) == len(kept):
            break
        kept = survivors
    return kept


def evaluate(data: dict, policy: dict) -> dict:
    words, usage = data["words"], sum(item[2] for item in data["words"].values())
    kept = kept_ids(data, policy)
    counts = Counter(concept for word_id in kept for concept in data["concepts"].get(word_id, ()))
    rare = {concept for concept, count in counts.items() if count < RARE_LIMIT}
    return {"words": len(kept), "usage": sum(words[w][2] for w in kept) / usage, "concepts": len(counts), "rare": len(rare),
            "unmodeled": sum(1 for c in counts if data["kinds"][c] == "unmodeled"),
            "in_rare": sum(1 for w in kept if data["concepts"].get(w, set()) & rare)}
