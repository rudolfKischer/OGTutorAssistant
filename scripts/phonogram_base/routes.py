import json
from pathlib import Path

from flask import Flask, abort, jsonify, request

from .models import AnalysisStatus, Reason
from .storage import read_query


def page(settings: dict) -> tuple[int, int]:
    try:
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", settings["word_page_size"]))
    except ValueError:
        abort(400)
    if offset < 0 or limit < 1 or limit > settings["word_page_maximum"]:
        abort(400)
    return limit, offset


def register_base_routes(app: Flask, repository: Path, database: Path | None = None) -> None:
    settings = json.loads((repository / "scripts/phonogram_base/settings.json").read_text())
    database = database or Path(settings["database"])

    def query(name: str, parameters: tuple = ()) -> list[tuple]:
        try:
            return read_query(database, name, parameters)
        except FileNotFoundError:
            abort(503)

    @app.get("/api/base/summary")
    def summary():
        return jsonify(json.loads(query("summary.sql")[0][0]))

    @app.get("/api/base/pattern/<identifier>/words")
    def pattern_words(identifier: str):
        if not query("find-pattern.sql", (identifier,)):
            abort(404)
        try:
            status = AnalysisStatus(request.args.get("status", AnalysisStatus.Consistent))
        except ValueError:
            abort(400)
        limit, offset = page(settings)
        rows = query("pattern-words.sql", (status, identifier, limit, offset))
        return jsonify(words=[row[0] for row in rows], offset=offset, limit=limit)

    register_excluded_routes(app, query, settings)

    @app.get("/api/base/word/<word>")
    def base_word_detail(word: str):
        rows = query("word-detail.sql", (word.lower().strip(),))
        if not rows:
            abort(404)
        return jsonify(json.loads(rows[0][0]))


def register_excluded_routes(app: Flask, query, settings: dict) -> None:
    @app.get("/api/base/excluded/<reason>/words")
    def excluded_words(reason: str):
        try:
            reason = Reason(reason)
        except ValueError:
            abort(400)
        limit, offset = page(settings)
        rows = query("excluded-words.sql", (reason, limit, offset))
        return jsonify(words=[row[0] for row in rows], offset=offset, limit=limit)

