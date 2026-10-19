import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .models import Blend, Direction, PairDefinition, Selection, validate_blends


SQL_DIRECTORY = Path(__file__).with_name("sql")


def sql(name: str) -> str:
    return (SQL_DIRECTORY / name).read_text()


class BlendStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(sql("foreign-keys.sql"))
            with connection:
                yield connection
        finally:
            connection.close()

    def seed(self, blends: list[Blend], pairs: list[PairDefinition], version: str) -> None:
        validate_blends(blends, pairs)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(sql("schema.sql"))
            connection.executemany(sql("save-pair.sql"),
                                   [(pair.id, pair.spelling, json.dumps(pair.sounds)) for pair in pairs])
            connection.executemany(sql("save-blend.sql"),
                                   [(blend.id, json.dumps(asdict(blend)), version) for blend in blends])
            for blend in blends:
                connection.execute(sql("clear-components.sql"), (blend.id,))
                connection.executemany(sql("save-component.sql"), [
                    (blend.id, ordinal, component.phonogram_id, component.start, component.end)
                    for ordinal, component in enumerate(blend.components)
                ])

    def definitions(self) -> list[Blend]:
        with self.connect() as connection:
            return [Blend.from_record(json.loads(row[0])) for row in connection.execute(sql("list-blends.sql"))]

    def save_selection(self, direction: Direction, concept_id: str) -> Selection:
        direction = Direction(direction)
        with self.connect() as connection:
            row = connection.execute(sql("find-blend.sql"), (concept_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown blend concept")
            connection.execute(sql("save-selection.sql"), (direction, concept_id, row[0]))
        return Selection(direction, concept_id, row[0])

    def selections(self) -> list[Selection]:
        with self.connect() as connection:
            return [Selection(Direction(row[0]), row[1], row[2])
                    for row in connection.execute(sql("list-selections.sql"))]
