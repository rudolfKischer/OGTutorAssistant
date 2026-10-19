import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.word_origins.build import build
from scripts.word_origins.fetch import SETTINGS


def main() -> None:
    data = build(REPOSITORY)
    path = REPOSITORY / SETTINGS["output_path"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0) + "\n")
    print(len(data["words"]), "flagged words", data["counts"], "->", path)


if __name__ == "__main__":
    main()
