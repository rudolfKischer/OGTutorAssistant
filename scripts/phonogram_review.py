import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from flask import Flask, abort, jsonify, send_file, send_from_directory


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from scripts.phonogram_audit.database import SQL_DIRECTORY, connect_readonly
from scripts.phonogram_blend_routes import register_blend_routes
from scripts.phonogram_base.routes import register_base_routes


@dataclass(frozen=True)
class AlignmentUnit:
    grapheme: str
    arpabet: str | None
    sound: str | None
    silent: bool


@dataclass(frozen=True)
class WordDetail:
    word: str
    pronunciation: list[str]
    alignment: list[AlignmentUnit]
    deployed_tags: list[str]


def create_app(report_directory: Path, workspace: Path = REPOSITORY.parent,
               blend_database: Path | None = None, base_database: Path | None = None) -> Flask:
    settings = json.loads((REPOSITORY / "scripts/phonogram_audit/settings.json").read_text())
    assets = REPOSITORY / settings["review_path"]
    cache_path = workspace / "StructuredLearningSoftwareMain/infra/data/production_cache.json"
    cache = json.loads(cache_path.read_text())
    pronunciations = {row[0]: row[1] for row in json.loads((REPOSITORY / "data/words.json").read_text())}
    app = Flask(__name__, static_folder=None)
    app.add_url_rule("/", endpoint="home", view_func=lambda: send_from_directory(assets, "index.html"))
    app.add_url_rule("/assets/<path:name>", endpoint="assets", view_func=lambda name: send_from_directory(assets, name))
    app.add_url_rule("/api/report", endpoint="report", view_func=lambda: send_file(report_directory / settings["report_filename"]))
    app.add_url_rule("/api/parity", endpoint="parity", view_func=lambda: send_file(report_directory / settings["parity_filename"]))
    copy_path = workspace / "DecodifyWebsite/src/content/phonogram-review.json"
    app.add_url_rule("/api/copy", endpoint="copy", view_func=lambda: send_file(copy_path))
    register_blend_routes(app, REPOSITORY, blend_database or Path(settings["blend_database"]))
    register_base_routes(app, REPOSITORY, base_database)

    @app.get("/api/word/<word>")
    def word_detail(word: str):
        normalized = word.lower().strip()
        if normalized not in pronunciations:
            abort(404)
        with connect_readonly(REPOSITORY / "data/words.db") as connection:
            rows = connection.execute((SQL_DIRECTORY / "audit_word_detail.sql").read_text(), (normalized,)).fetchall()
        detail = WordDetail(
            normalized, pronunciations[normalized], [AlignmentUnit(*row[:3], bool(row[3])) for row in rows],
            sorted(concept for concept, words in cache["concept_to_words"].items() if normalized in words),
        )
        return jsonify(asdict(detail))

    return app


def main() -> None:
    settings = json.loads((REPOSITORY / "scripts/phonogram_audit/settings.json").read_text())
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--port", type=int, default=settings["review_port"])
    arguments = parser.parse_args()
    directory = arguments.report.resolve()
    for name in [settings["report_filename"], settings["parity_filename"]]:
        if not (directory / name).is_file():
            raise FileNotFoundError(directory / name)
    create_app(directory).run(host=settings["review_host"], port=arguments.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
