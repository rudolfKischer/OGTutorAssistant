import json
from pathlib import Path

from scripts.heteronyms.ipa import to_arpabet

from .analysis import analyze, bases
from scripts.aligner.model import Model

from .models import PronunciationOption, WordAnalysis
from .normalize import sounds
from .registry import Registry

IPA_VARIANT_SEPARATOR = ", "
UNSTRESSED_DIGIT = "0"
UNSTRESSED_PHONE = "AH0"
STRESS = "012"
VOWELS = set(json.loads(Path(__file__).with_name("settings.json").read_text())["vowels"])


def relaxed(phones: list[str], equivalents: dict[str, str], exempt: list[str]) -> list[str]:
    return [UNSTRESSED_PHONE if phone.endswith(UNSTRESSED_DIGIT) and phone[:-1] in VOWELS and phone[:-1] not in exempt
            else equivalents.get(phone.rstrip(STRESS), phone.rstrip(STRESS)) + phone[len(phone.rstrip(STRESS)):]
            for phone in phones]


def without_accent_sounds(phones: list[str], rules: dict) -> list[str]:
    result = []
    for index, phone in enumerate(phones):
        following = phones[index + 1].rstrip(STRESS) if index + 1 < len(phones) else None
        if following in rules["drop_before"].get(phone.rstrip(STRESS), []):
            continue
        result.append(phone)
    return result


def merged_sequences(phones: list[str], rules: dict) -> list[str]:
    result = list(phones)
    for pattern, replacement in rules["merge"]:
        index = 0
        while index <= len(result) - len(pattern):
            if [phone.rstrip(STRESS) for phone in result[index:index + len(pattern)]] == pattern:
                stress = result[index][len(result[index].rstrip(STRESS)):]
                result[index:index + len(pattern)] = [replacement[0] + stress]
            index += 1
    return result


def key(phones: list[str]) -> tuple[str, ...]:
    return tuple(sounds(phones))


def sense_key(phones: list[str], settings: dict) -> tuple[str, ...]:
    rules = settings["pronunciation"]["same_pronunciation"]
    prepared = relaxed(phones, settings["pronunciation"]["equivalent_vowels"], rules["unstressed_exempt"])
    return tuple(sounds(merged_sequences(without_accent_sounds(prepared, rules), rules)))


def load_heteronyms(repository: Path, settings: dict) -> dict[str, dict]:
    data = json.loads((repository / settings["heteronyms_path"]).read_text())
    return {entry["spelling"]: entry for entry in data["entries"]}


def collect(selected: list[str], dictionary: list[list[str]], settings: dict) -> list[PronunciationOption]:
    sources = settings["pronunciation"]["option_sources"]
    options = [PronunciationOption(0, sources["selected"], selected)]
    seen = {key(selected)}
    for phones in dictionary:
        if key(phones) not in seen:
            seen.add(key(phones))
            options.append(PronunciationOption(len(options), sources["dictionary"], phones))
    return options


def attach_senses(options: list[PronunciationOption], senses: list[dict], settings: dict) -> None:
    sources = settings["pronunciation"]["option_sources"]
    for index, sense in enumerate(senses):
        for ipa in sense["ipa"].split(IPA_VARIANT_SEPARATOR):
            phones = to_arpabet(ipa)
            if not phones:
                continue
            match = next((option for option in options if sense_key(option.phones, settings) == sense_key(phones, settings)), None)
            if match is None:
                match = PronunciationOption(len(options), sources["ipa"], phones)
                options.append(match)
            if index not in [item["index"] for item in match.senses]:
                match.senses.append({"index": index, "ipa": ipa, **{k: sense[k] for k in ("source", "part_of_speech", "meaning")}})


def options_for(word: str, selected: list[str], dictionary: list[list[str]], heteronym: dict | None,
                settings: dict) -> list[PronunciationOption]:
    options = collect(selected, dictionary, settings)
    if heteronym:
        attach_senses(options, heteronym["senses"], settings)
    return options


def analyze_options(options: list[PronunciationOption], primary: WordAnalysis, word: str, alignment: list,
                    registry: Registry, settings: dict, known_phones: set[str], phonetic: dict | None = None,
                    model: Model | None = None, origins: dict | None = None) -> None:
    for option in options:
        if option.ordinal == 0:
            option.analysis = primary
            continue
        option.analysis = analyze(word, option.phones, alignment, primary.frequency_rank,
                                  primary.frequency_weight, registry, settings, known_phones, phonetic, model, origins)
