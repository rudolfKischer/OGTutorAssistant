import json
from dataclasses import asdict
from pathlib import Path

from flask import Flask, abort, jsonify, request

from db_builder.phonograms.models import Blend, Direction, PairDefinition
from db_builder.phonograms.store import BlendStore


def load_store(repository: Path, database: Path) -> tuple[BlendStore, str]:
    if database.resolve() == (repository / "data/words.db").resolve():
        raise ValueError("The authoring database cannot be used for review selections")
    document = json.loads((repository / "data/mappings/blend-phonograms.json").read_text())
    inventory = json.loads((repository / "static/phonogram-review/inventories.json").read_text())
    pairs = [PairDefinition(row["id"], row["spelling"], row["sounds"]) for row in inventory["phonograms"]]
    store = BlendStore(database)
    store.seed([Blend.from_record(row) for row in document["definitions"]], pairs, document["bundle_version"])
    return store, document["bundle_version"]


def register_blend_routes(app: Flask, repository: Path, database: Path) -> None:
    store, version = load_store(repository, database)

    @app.get("/api/blends")
    def blends():
        return jsonify(definitions=[asdict(blend) for blend in store.definitions()],
                       selections=[asdict(selection) for selection in store.selections()], bundle_version=version)

    @app.post("/api/blends/selection")
    def select_blend():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) != {"direction", "concept_id"}:
            abort(400)
        if not all(isinstance(value, str) for value in body.values()):
            abort(400)
        try:
            selection = store.save_selection(Direction(body["direction"]), body["concept_id"])
        except ValueError:
            abort(400)
        return jsonify(asdict(selection))
