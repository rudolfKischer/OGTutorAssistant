import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.aligner.model import SETTINGS
from scripts.aligner.train import train


def main() -> None:
    model = train(REPOSITORY)
    path = REPOSITORY / SETTINGS["model_path"]
    model.save(path)
    print(len(model.counts), "units from", model.total, "trusted unit occurrences ->", path)


if __name__ == "__main__":
    main()
