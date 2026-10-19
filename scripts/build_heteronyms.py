import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.heteronyms.merge import SETTINGS, build


def main() -> None:
    data = build(REPOSITORY)
    path = REPOSITORY / SETTINGS["output_path"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(data["words"], "heteronyms,", data["senses"], "senses ->", path)


if __name__ == "__main__":
    main()
