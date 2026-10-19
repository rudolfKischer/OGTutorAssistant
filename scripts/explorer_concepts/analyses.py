import json
from contextlib import closing
from pathlib import Path

from scripts.phonogram_audit.database import connect_readonly
from scripts.phonogram_cache.exporter import occurrence_tag
from .catalog import SQL
from .models import AnalysisRow, PhonogramRow


def phonogram_row(ordinal: int, occurrence: dict) -> PhonogramRow:
    pattern = occurrence["pattern"]
    spans = [[span["start"], span["end"]] for span in occurrence["spans"]]
    return PhonogramRow(ordinal, occurrence_tag(pattern), occurrence["layer"], occurrence.get("syllable"), pattern["spelling"],
                        pattern["sounds"], spans, occurrence["phones"])


def phone_ranges(document: dict) -> list[list[int]]:
    return [[item["phone_start"], item["phone_end"]] for item in document.get("phonetic_syllables", [])]


def written_ranges(document: dict) -> list[list[int]]:
    return [[item["start"], item["end"]] for item in document.get("syllables", [])]


def read_analyses(database: Path) -> list[AnalysisRow]:
    rows = []
    with closing(connect_readonly(database)) as connection:
        for word, status, reasons, detail in connection.execute((SQL / "analyses.sql").read_text()):
            document = json.loads(detail)
            phonograms = [phonogram_row(index, item) for index, item in enumerate(document["occurrences"])]
            rows.append(AnalysisRow(word, status, json.loads(reasons), phone_ranges(document), written_ranges(document), document.get("warnings", []), phonograms))
    return rows
