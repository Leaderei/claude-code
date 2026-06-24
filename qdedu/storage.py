"""Persistência em SQLite (resumível/idempotente) e exportação CSV."""
from __future__ import annotations

import csv
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS municipalities (
    territory_id TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    uf           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gazettes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    territory_id   TEXT NOT NULL,
    date           TEXT,
    edition        TEXT,
    url            TEXT,
    txt_url        TEXT,
    UNIQUE (territory_id, date, edition, txt_url)
);

CREATE TABLE IF NOT EXISTS contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    territory_id TEXT NOT NULL,
    kind         TEXT NOT NULL,        -- 'email' | 'phone' | 'secretary'
    value        TEXT NOT NULL,
    title        TEXT,                 -- usado p/ secretary
    context      TEXT,
    source_url   TEXT,
    gazette_date TEXT,
    source       TEXT NOT NULL DEFAULT 'querido_diario',  -- proveniência
    UNIQUE (territory_id, kind, value)
);

-- Marca municípios já processados para permitir retomada.
CREATE TABLE IF NOT EXISTS progress (
    territory_id  TEXT PRIMARY KEY,
    uf            TEXT NOT NULL,
    status        TEXT NOT NULL,       -- 'done' | 'error'
    gazettes_seen INTEGER DEFAULT 0,
    detail        TEXT
);
"""


@dataclass
class ContactRow:
    territory_id: str
    kind: str
    value: str
    title: str | None = None
    context: str | None = None
    source_url: str | None = None
    gazette_date: str | None = None
    source: str = "querido_diario"


class Store:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.db_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- municípios -------------------------------------------------------
    def upsert_municipalities(self, rows: list[tuple[str, str, str]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO municipalities(territory_id, name, uf) "
            "VALUES (?,?,?)",
            rows,
        )
        self.conn.commit()

    def municipalities(self, uf: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT territory_id, name, uf FROM municipalities WHERE uf=? "
            "ORDER BY name",
            (uf.upper(),),
        ).fetchall()

    # -- progresso (retomada) --------------------------------------------
    def is_done(self, territory_id: str) -> bool:
        row = self.conn.execute(
            "SELECT status FROM progress WHERE territory_id=?", (territory_id,)
        ).fetchone()
        return bool(row and row["status"] == "done")

    def mark_progress(
        self, territory_id: str, uf: str, status: str, seen: int = 0, detail: str = ""
    ) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO progress(territory_id, uf, status, "
            "gazettes_seen, detail) VALUES (?,?,?,?,?)",
            (territory_id, uf.upper(), status, seen, detail),
        )
        self.conn.commit()

    # -- gazettes & contatos ---------------------------------------------
    def add_gazette(self, g) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO gazettes(territory_id, date, edition, url, "
            "txt_url) VALUES (?,?,?,?,?)",
            (g.territory_id, g.date, g.edition, g.url, g.txt_url),
        )

    def add_contacts(self, rows: list[ContactRow]) -> int:
        before = self.conn.total_changes
        self.conn.executemany(
            "INSERT OR IGNORE INTO contacts(territory_id, kind, value, title, "
            "context, source_url, gazette_date, source) VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    r.territory_id,
                    r.kind,
                    r.value,
                    r.title,
                    r.context,
                    r.source_url,
                    r.gazette_date,
                    r.source,
                )
                for r in rows
            ],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    # -- exportação -------------------------------------------------------
    def export_csv(self, uf: str, out_path: str) -> int:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        rows = self.conn.execute(
            """
            SELECT m.name AS municipio, m.uf, c.territory_id, c.kind, c.value,
                   c.title, c.gazette_date, c.source, c.source_url, c.context
            FROM contacts c
            JOIN municipalities m ON m.territory_id = c.territory_id
            WHERE m.uf = ?
            ORDER BY m.name, c.kind, c.value
            """,
            (uf.upper(),),
        ).fetchall()
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "municipio",
                    "uf",
                    "codigo_ibge",
                    "tipo",
                    "valor",
                    "cargo",
                    "data_diario",
                    "fonte",
                    "url_fonte",
                    "contexto",
                ]
            )
            for r in rows:
                writer.writerow([r[k] for k in r.keys()])
        return len(rows)

    def close(self) -> None:
        self.conn.close()


@contextmanager
def open_store(db_path: str | None = None) -> Iterator[Store]:
    store = Store(db_path)
    try:
        yield store
    finally:
        store.close()
