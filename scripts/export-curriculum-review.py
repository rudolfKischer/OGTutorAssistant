import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from openpyxl import load_workbook


REPOSITORY = Path(__file__).resolve().parents[1]
WORKSPACE = REPOSITORY.parent


@dataclass(frozen=True)
class CurriculumRow:
    row: int
    name: str
    group: str
    subgroup: str | None
    level: float | None
    grapheme: str | None
    phoneme: str | None
    legacy_id: str | None


@dataclass(frozen=True)
class Phonogram:
    id: str
    name: str
    kind: str
    spelling: str
    sounds: list[str]
    status: str
    context: str


def curriculum_rows() -> list[CurriculumRow]:
    workbook = load_workbook(WORKSPACE / "references/concepts-2026-10-11.xlsx", read_only=True, data_only=True)
    rows = list(workbook["Concept List"].values)
    rows = [tuple(row) + (None,) * (len(rows[0]) - len(row)) for row in rows]
    records = [CurriculumRow(index, row[6], row[3], row[4], row[2], row[9], row[10], row[13])
               for index, row in enumerate(rows[1:], 2) if len(row) > 6 and row[6]]
    workbook.close()
    return records


def phonogram_rows() -> list[Phonogram]:
    source = WORKSPACE / "notes/issue-10-phonograms/MASTER-PLAN-CATALOG.csv"
    with source.open(newline="") as stream:
        return [Phonogram(row["concept_id"], row["concept_name"], row["kind"], row["spelling"],
                          json.loads(row["phonemes"]), row["model_status"], row["context"])
                for row in csv.DictReader(stream) if row["kind"] == "phonogram"]


def main() -> None:
    data = {"curriculum": [asdict(row) for row in curriculum_rows()],
            "phonograms": [asdict(row) for row in phonogram_rows()]}
    output = REPOSITORY / "static/phonogram-review/inventories.json"
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: len(value) for key, value in data.items()}))


if __name__ == "__main__":
    main()
