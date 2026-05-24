from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists kv_store (
                    key text primary key,
                    value_json text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists reconciliation_runs (
                    run_id text primary key,
                    created_at text not null,
                    payload_json text not null
                )
                """
            )

    def set_json(self, key: str, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        with self._connect() as conn:
            conn.execute(
                "insert into kv_store(key, value_json) values(?, ?) on conflict(key) do update set value_json=excluded.value_json",
                (key, payload),
            )

    def get_json(self, key: str) -> object | None:
        with self._connect() as conn:
            row = conn.execute("select value_json from kv_store where key = ?", (key,)).fetchone()
        return None if row is None else json.loads(row[0])

    def record_reconciliation(self, run_id: str, created_at: str, payload: object) -> None:
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
        with self._connect() as conn:
            conn.execute(
                "insert or replace into reconciliation_runs(run_id, created_at, payload_json) values(?, ?, ?)",
                (run_id, created_at, serialized),
            )

    def latest_reconciliation(self) -> object | None:
        with self._connect() as conn:
            row = conn.execute(
                "select payload_json from reconciliation_runs order by created_at desc limit 1"
            ).fetchone()
        return None if row is None else json.loads(row[0])
