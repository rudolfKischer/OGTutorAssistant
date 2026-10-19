import argparse
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.explorer_concepts.builder import build
from scripts.explorer_concepts.catalog import SETTINGS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=REPOSITORY / SETTINGS["output"])
    arguments = parser.parse_args()
    print(build(REPOSITORY, arguments.database, arguments.output))


if __name__ == "__main__":
    main()
