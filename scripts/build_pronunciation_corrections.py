import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.pronunciation_corrections.build import SETTINGS, build


def main() -> None:
    data = build(REPOSITORY)
    path = REPOSITORY / SETTINGS["output_path"]
    path.write_text(json.dumps(data, indent=1) + "\n")
    print(len(data["entries"]), "corrections ->", path)
    for entry in data["entries"]:
        print(entry["action"], entry["word"], entry["rule"] if "rule" in entry else "manual")


if __name__ == "__main__":
    main()
