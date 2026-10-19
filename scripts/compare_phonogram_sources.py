import argparse
import json
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.phonogram_review_audit.benchmarks import benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--no-publish", action="store_true")
    arguments = parser.parse_args()
    settings = json.loads((REPOSITORY / "scripts/phonogram_base/settings.json").read_text())
    report = benchmark(REPOSITORY, arguments.database or Path(settings["database"]))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    document = json.dumps(report, indent=2) + "\n"
    arguments.output.write_text(document)
    if not arguments.no_publish:
        (REPOSITORY / "static/phonogram-review/source-comparison.json").write_text(document)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
