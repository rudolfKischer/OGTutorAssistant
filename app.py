import os
from config import CMU_DICT_PATH, ARPA_DICT_PATH, PHONEME_WORDS_FILE
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

def build_word_masks(cmu_dict):
    all_phonemes = [
        'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'B', 'CH', 'D', 'DH',
        'EH', 'ER', 'EY', 'F', 'G', 'HH', 'IH', 'IY', 'JH', 'K',
        'L', 'M', 'N', 'NG', 'OW', 'OY', 'P', 'R', 'S', 'SH',
        'T', 'TH', 'UH', 'UW', 'V', 'W', 'Y', 'Z', 'ZH'
    ]
    phoneme_to_bit = {ph: (1 << i) for i, ph in enumerate(all_phonemes)}

    word_masks = {}
    for word, pronunciations in cmu_dict.items():
        mask = 0
        for ph in pronunciations[0]:  # First pronunciation
            base = ph.rstrip('012')   # Strip stress digits
            if base in phoneme_to_bit:
                mask |= phoneme_to_bit[base]
        word_masks[word] = mask

    return phoneme_to_bit, word_masks

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

def get_phoneme_word_sets(cmu_dict):
    phoneme_word_sets = {}
    for word, pronunciations in cmu_dict.items():
        pronunciation = pronunciations[0]  # Take the first pronunciation
        for phoneme in pronunciation:
            if phoneme not in phoneme_word_sets:
                phoneme_word_sets[phoneme] = []
            phoneme_word_sets[phoneme].append(word)
    return phoneme_word_sets

def load_phoneme_word_sets(cmu_dict):
    if PHONEME_WORDS_FILE not in os.listdir():
        phoneme_word_sets = get_phoneme_word_sets(cmu_dict)
        with open(PHONEME_WORDS_FILE, 'w', encoding='utf-8') as file:
            json.dump(phoneme_word_sets, file, ensure_ascii=False, indent=4)
    else:
        phoneme_word_sets = load_json(PHONEME_WORDS_FILE)
    
    # convert the lists to sets for faster intersection
    for phoneme in phoneme_word_sets:
        phoneme_word_sets[phoneme] = set(phoneme_word_sets[phoneme])
    return phoneme_word_sets


def get_words_from_phonemes_list(phonemes_list, phoneme_to_bit, word_masks):
    allowed_mask = 0
    for ph in phonemes_list:
        base = ph.rstrip('012')
        allowed_mask |= phoneme_to_bit[base]

    return [w for w, m in word_masks.items() if m & ~allowed_mask == 0]

def get_phonems_from_words_tool(cmu_dict, arpa_dict):

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


def run():
    cmu_dict = parse_cmu_dict(CMU_DICT_PATH)
    arpa_dict = parse_arpa_dict(ARPA_DICT_PATH)

    phoneme_to_bit, word_masks = build_word_masks(cmu_dict)

    phonemes_list = {"K", "AE1", "T", "S", "EH"}
    valid_words = get_words_from_phonemes_list(phonemes_list, phoneme_to_bit, word_masks)
    print(f"Words that contain the phonemes {phonemes_list}: {valid_words}")




    


    

def main():

    # cmu_dict = parse_cmu_dict(CMU_DICT_PATH)
    # arpa_dict = parse_arpa_dict(ARPA_DICT_PATH)
    run()



if __name__ == "__main__":
    main()
