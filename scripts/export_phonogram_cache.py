import argparse
import json
from pathlib import Path

from scripts.phonogram_cache.exporter import build

WORKSPACE = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    cache = build(WORKSPACE, arguments.database)
    arguments.output.write_text(json.dumps(cache))
    print(len(cache["concept_to_words"]), "tags written to", arguments.output)


if __name__ == "__main__":
    main()
