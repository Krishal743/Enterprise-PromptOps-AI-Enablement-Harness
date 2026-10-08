from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ops_ai.settings import database_path


class TicketStore:
    def __init__(self, path: Path | None = None):
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                trace_id TEXT,
                status TEXT NOT NULL DEFAULT 'awaiting_review',
                approved_team TEXT,
                approval_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(ticket_id) REFERENCES tickets(ticket_id)
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def save(self, ticket_id: str, request: dict, response: dict, trace_id: str | None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO tickets (ticket_id, request_json, response_json, trace_id) VALUES (?, ?, ?, ?)",
                (ticket_id, json.dumps(request), json.dumps(response), trace_id),
            )

    def get(self, ticket_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["request"] = json.loads(data.pop("request_json"))
        data["response"] = json.loads(data.pop("response_json"))
        return data

    def add_feedback(self, ticket_id: str, score: int, comment: str) -> bool:
        if self.get(ticket_id) is None:
            return False
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO feedback (ticket_id, score, comment) VALUES (?, ?, ?)",
                (ticket_id, score, comment),
            )
        return True

    def list_work_orders(self, team: str | None = None) -> list[dict]:
        query = "SELECT ticket_id, approved_team, approval_note, created_at, request_json, response_json FROM tickets WHERE status = 'dispatched_simulated'"
        params: tuple = ()
        if team:
            query += " AND approved_team = ?"
            params = (team,)
        query += " ORDER BY created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        orders = []
        for row in rows:
            request = json.loads(row["request_json"])
            response = json.loads(row["response_json"])
            orders.append(
                {
                    "ticket_id": row["ticket_id"],
                    "field_team": row["approved_team"],
                    "priority": response["priority"],
                    "description": request["description"],
                    "diagnostic_code": request.get("diagnostic_code"),
                    "diagnostic_summary": response["diagnostic_summary"],
                    "evidence": response["evidence"],
                    "supervisor_note": row["approval_note"],
                    "created_at": row["created_at"],
                }
            )
        return orders

    def review(self, ticket_id: str, approved: bool, team: str | None, note: str) -> dict | None:
        status = "dispatched_simulated" if approved else "returned_for_review"
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE tickets SET status = ?, approved_team = ?, approval_note = ? WHERE ticket_id = ? AND status = 'awaiting_review'",
                (status, team if approved else None, note, ticket_id),
            )
            if updated.rowcount == 0:
                if self.get(ticket_id) is None:
                    return None
                raise ValueError("Ticket has already been reviewed")
        return self.get(ticket_id)
