import json
from contextlib import closing
from pathlib import Path

from scripts.phonogram_base.normalize import sounds
from scripts.phonogram_cache.exporter import occurrence_tag
from scripts.phonogram_audit.database import connect_readonly
from .catalog import SETTINGS, SQL
from .analyses import phone_ranges, phonogram_row, written_ranges
from dataclasses import asdict


def analysis_blob(status: str, reasons: list[str], detail: dict) -> dict:
    base = [phonogram_row(index, item) for index, item in enumerate(detail.get("occurrences", []))]
    return {"status": status, "reasons": reasons, "evidence": detail.get("evidence"),
            "syllables": phone_ranges(detail), "written": written_ranges(detail), "warnings": detail.get("warnings", []),
            "phonograms": [asdict(item) for item in base]}


def read_pronunciations(database: Path) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    with closing(connect_readonly(database)) as connection:
        for word, ordinal, source, phones, senses, status, reasons, detail in connection.execute((SQL / "pronunciations.sql").read_text()):
            document = json.loads(detail)
            blob = analysis_blob(status, json.loads(reasons), document) if document else None
            result.setdefault(word, []).append({"ordinal": ordinal, "source": source, "phones": json.loads(phones),
                                                "sounds": sounds(json.loads(phones)), "senses": json.loads(senses),
                                                "analysis": blob})
    return result


def read_heteronyms(repository: Path) -> dict[str, dict]:
    data = json.loads((repository / SETTINGS["heteronyms_path"]).read_text())
    return {entry["spelling"]: entry for entry in data["entries"]}


def heteronym_link(word: str) -> str:
    return SETTINGS["heteronym_link"].format(word=word)
