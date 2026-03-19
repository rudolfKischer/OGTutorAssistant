import os
from config import CMU_DICT_PATH, ARPA_DICT_PATH
import json

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def parse_cmu_dict(path):
    cmu_dict = {}

    with open(path, "r", encoding="latin-1") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith(";;;"):
                continue

            parts = line.split()
            word = parts[0]
            phonemes = parts[1:]

            cmu_dict.setdefault(word, []).append(phonemes)

    return cmu_dict

def parse_arpa_dict(path):
    # contains a mapping of arpa symbols to
    # their ipa symbol, their graphemes, and example words
    arpa_dict = load_json(ARPA_DICT_PATH)
    return arpa_dict

def get_phoneme_info(word, cmu_dict, arpa_dict):
    word = word.upper()
    if word not in cmu_dict:
        return None

    phoneme_info = []
    for phoneme in cmu_dict[word][0]:  # Take the first pronunciation
        if phoneme in arpa_dict:
            info = arpa_dict[phoneme]
            phoneme_info.append({
                "arpa": phoneme,
                "ipa": info.get("ipa_symbol", ""),
                "graphemes": info.get("graphemes", []),
                "examples": info.get("examples", [])
            })
        else:
            phoneme_info.append({
                "arpa": phoneme,
                "ipa": "",
                "graphemes": [],
                "examples": []
            })

    return phoneme_info

def display_phoneme_info(word, phoneme_info):
    print(f"Phoneme information for '{word}':")
    for info in phoneme_info:
        print(f"  ARPA: {info['arpa']}")
        print(f"  IPA: {info['ipa']}")
        print(f"  Graphemes: {', '.join(info['graphemes'])}")
        print(f"  Examples: {', '.join(info['examples'])}")
        print()

def get_user_input():
    word = input("Enter a word to get its phoneme information (or 'exit' to quit): ")
    return word.strip()

def get_words_from_phonemes_list(phonemes_list):
    # we want to take a list of phonemes
    # and only return words that contain all of those phonemes
    # and only those phonemes, not more, not less
    # to do this we can get a candidate list of 
    pass

def run():
    cmu_dict = parse_cmu_dict(CMU_DICT_PATH)
    arpa_dict = parse_arpa_dict(ARPA_DICT_PATH)


    print("Enter a word to get its phoneme information.")
    print("Type 'exit' or press Ctrl+C to quit.")

    while True:
        try:
            word = get_user_input()
            if word.lower() == 'exit':
                print("Exiting...")
                break

            phoneme_info = get_phoneme_info(word, cmu_dict, arpa_dict)
            if phoneme_info:
                display_phoneme_info(word, phoneme_info)
            else:
                print(f"No phoneme information found for '{word}'.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break

def main():

    # cmu_dict = parse_cmu_dict(CMU_DICT_PATH)
    # arpa_dict = parse_arpa_dict(ARPA_DICT_PATH)
    run()



if __name__ == "__main__":
    main()
