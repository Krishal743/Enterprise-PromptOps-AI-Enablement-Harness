"""Local, pseudonymous study of manual and AI-assisted routing decisions."""

from __future__ import annotations

import json
import os
import random
import sqlite3
import statistics
import time
from pathlib import Path
from uuid import UUID, uuid4

from ops_ai.settings import ROOT

CASE_PAIRS = {
    "routine": ("G001", "G002"),
    "ambiguous": ("G013", "G014"),
    "safety": ("G021", "G025"),
    "missing": ("G029", "G030"),
    "tone": ("G036", "G037"),
    "injection": ("G041", "G042"),
    "out_of_scope": ("G046", "G047"),
}
ROLES = {"field_supervisor", "service_operations", "other"}


def golden_cases() -> dict[str, dict]:
    return {
        case["vars"]["case_id"]: case["vars"]
        for case in json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))
    }


def assignments(study_id: str, arm: int = 0) -> list[tuple[str, str]]:
    """Balance conditions by category and alternate case assignments across sessions."""
    if arm not in (0, 1):
        raise ValueError("Study arm must be 0 or 1")
    rng = random.Random(UUID(study_id).int)
    tasks = []
    for first, second in CASE_PAIRS.values():
        for index, case_id in enumerate((first, second)):
            tasks.append((case_id, "assisted" if index == arm else "manual"))
    rng.shuffle(tasks)
    return tasks


def study_database_path() -> Path:
    return Path(os.getenv("OPS_STUDY_DB_PATH", str(ROOT / ".data" / "operator-study.db")))


class StudyStore:
    def __init__(self, path: Path | None = None):
        self.path = path or study_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS study_sessions (
                study_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                created_at_ns INTEGER NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS study_tasks (
                study_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                case_id TEXT NOT NULL,
                condition TEXT NOT NULL,
                shown_at_ns INTEGER,
                completed_at_ns INTEGER,
                decision_ms REAL,
                ai_latency_ms REAL,
                ai_response_json TEXT,
                selected_team TEXT,
                selected_priority TEXT,
                selected_review INTEGER,
                confidence INTEGER,
                usefulness INTEGER,
                comment TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (study_id, sequence),
                FOREIGN KEY (study_id) REFERENCES study_sessions(study_id)
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def start(self, role: str) -> str:
        if role not in ROLES:
            raise ValueError("Choose a listed role")
        study_id = str(uuid4())
        with self._connect() as connection:
            arm = connection.execute("SELECT COUNT(*) FROM study_sessions").fetchone()[0] % 2
            connection.execute(
                "INSERT INTO study_sessions (study_id, role, created_at_ns) VALUES (?, ?, ?)",
                (study_id, role, time.time_ns()),
            )
            connection.executemany(
                "INSERT INTO study_tasks (study_id, sequence, case_id, condition) VALUES (?, ?, ?, ?)",
                [
                    (study_id, sequence, case_id, condition)
                    for sequence, (case_id, condition) in enumerate(assignments(study_id, arm), 1)
                ],
            )
        return study_id

    def session(self, study_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT study_id, role FROM study_sessions WHERE study_id = ?", (study_id,)
            ).fetchone()
        return dict(row) if row else None

    def progress(self, study_id: str) -> tuple[int, int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total, COUNT(completed_at_ns) AS completed "
                "FROM study_tasks WHERE study_id = ?",
                (study_id,),
            ).fetchone()
        return row["completed"], row["total"]

    def next_task(self, study_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM study_tasks WHERE study_id = ? AND completed_at_ns IS NULL "
                "ORDER BY sequence LIMIT 1",
                (study_id,),
            ).fetchone()
        if row is None:
            return None
        case = golden_cases()[row["case_id"]]
        return {
            "sequence": row["sequence"],
            "case_id": row["case_id"],
            "condition": row["condition"],
            "description": case["description"],
            "diagnostic_code": case["diagnostic_code"],
            "shown_at_ns": row["shown_at_ns"],
            "ai_latency_ms": row["ai_latency_ms"],
            "ai_response": json.loads(row["ai_response_json"]) if row["ai_response_json"] else None,
        }

    def attach_ai(self, study_id: str, sequence: int, latency_ms: float, response: dict) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE study_tasks SET ai_latency_ms = ?, ai_response_json = ? "
                "WHERE study_id = ? AND sequence = ? AND condition = 'assisted' "
                "AND ai_response_json IS NULL AND shown_at_ns IS NULL",
                (round(latency_ms, 1), json.dumps(response), study_id, sequence),
            )
        if updated.rowcount != 1:
            raise ValueError("AI recommendation is already prepared or task is unavailable")

    def mark_shown(self, study_id: str, sequence: int) -> int:
        with self._connect() as connection:
            connection.execute(
                "UPDATE study_tasks SET shown_at_ns = ? WHERE study_id = ? AND sequence = ? "
                "AND shown_at_ns IS NULL AND completed_at_ns IS NULL "
                "AND (condition = 'manual' OR ai_response_json IS NOT NULL)",
                (time.time_ns(), study_id, sequence),
            )
            row = connection.execute(
                "SELECT shown_at_ns FROM study_tasks WHERE study_id = ? AND sequence = ?",
                (study_id, sequence),
            ).fetchone()
        if row is None or row["shown_at_ns"] is None:
            raise ValueError("Prepare the task before showing it")
        return row["shown_at_ns"]

    def submit(
        self,
        study_id: str,
        sequence: int,
        *,
        team: str,
        priority: str,
        review: bool,
        confidence: int,
        usefulness: int | None,
        comment: str,
    ) -> float:
        if team not in {
            "battery",
            "charging",
            "drivetrain",
            "braking",
            "connectivity",
            "general_service",
            "human_review",
        } or priority not in {"routine", "urgent", "critical"}:
            raise ValueError("Choose a listed team and priority")
        if not 1 <= confidence <= 5 or (usefulness is not None and not 1 <= usefulness <= 5):
            raise ValueError("Scores must be between 1 and 5")
        if len(comment) > 1000:
            raise ValueError("Comment is too long")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT shown_at_ns, completed_at_ns, condition FROM study_tasks "
                "WHERE study_id = ? AND sequence = ?",
                (study_id, sequence),
            ).fetchone()
            if row is None or row["shown_at_ns"] is None or row["completed_at_ns"] is not None:
                raise ValueError("Task is not active")
            if (row["condition"] == "assisted") != (usefulness is not None):
                raise ValueError("Usefulness is required only for assisted tasks")
            completed_at_ns = time.time_ns()
            elapsed_ms = (completed_at_ns - row["shown_at_ns"]) / 1_000_000
            if elapsed_ms < 0:
                raise ValueError("System clock changed during the task")
            updated = connection.execute(
                "UPDATE study_tasks SET completed_at_ns = ?, decision_ms = ?, "
                "selected_team = ?, selected_priority = ?, selected_review = ?, "
                "confidence = ?, usefulness = ?, comment = ? "
                "WHERE study_id = ? AND sequence = ? AND completed_at_ns IS NULL",
                (
                    completed_at_ns,
                    round(elapsed_ms, 1),
                    team,
                    priority,
                    int(review),
                    confidence,
                    usefulness,
                    comment.strip(),
                    study_id,
                    sequence,
                ),
            )
        if updated.rowcount != 1:
            raise ValueError("Task was already submitted")
        return round(elapsed_ms, 1)

    def report(self) -> dict:
        with self._connect() as connection:
            sessions = [
                dict(row)
                for row in connection.execute(
                    "SELECT s.study_id, s.role, COUNT(t.sequence) AS total, "
                    "COUNT(t.completed_at_ns) AS completed FROM study_sessions s "
                    "LEFT JOIN study_tasks t ON s.study_id = t.study_id "
                    "GROUP BY s.study_id"
                )
            ]
            complete_ids = [
                s["study_id"] for s in sessions if s["total"] and s["total"] == s["completed"]
            ]
            rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM study_tasks WHERE completed_at_ns IS NOT NULL"
                )
            ]
        cases = golden_cases()
        complete_rows = [row for row in rows if row["study_id"] in complete_ids]
        by_condition = {}
        for condition in ("manual", "assisted"):
            selected = [row for row in complete_rows if row["condition"] == condition]
            if not selected:
                by_condition[condition] = None
                continue
            by_condition[condition] = {
                "decisions": len(selected),
                "median_decision_ms": round(
                    statistics.median(row["decision_ms"] for row in selected), 1
                ),
                "median_total_ms": round(
                    statistics.median(
                        row["decision_ms"] + (row["ai_latency_ms"] or 0) for row in selected
                    ),
                    1,
                ),
                "team_correct": sum(
                    row["selected_team"] == cases[row["case_id"]]["expected_team"]
                    for row in selected
                ),
                "priority_correct": sum(
                    row["selected_priority"] == cases[row["case_id"]]["expected_priority"]
                    for row in selected
                ),
                "review_correct": sum(
                    bool(row["selected_review"]) == cases[row["case_id"]]["must_review"]
                    for row in selected
                ),
                "median_confidence": statistics.median(row["confidence"] for row in selected),
                "timings_over_5_minutes": sum(row["decision_ms"] > 300_000 for row in selected),
            }
            if condition == "assisted":
                by_condition[condition]["median_model_ms"] = round(
                    statistics.median(row["ai_latency_ms"] for row in selected), 1
                )
                by_condition[condition]["median_usefulness"] = statistics.median(
                    row["usefulness"] for row in selected
                )
                by_condition[condition]["team_corrections"] = sum(
                    row["selected_team"] != json.loads(row["ai_response_json"])["recommended_team"]
                    for row in selected
                )
        roles = {
            role: sum(s["role"] == role and s["study_id"] in complete_ids for s in sessions)
            for role in sorted(ROLES)
        }
        relevant = roles["field_supervisor"] + roles["service_operations"]
        manual = by_condition["manual"]
        assisted = by_condition["assisted"]
        reduction = None
        if manual and assisted and manual["median_decision_ms"] > 0:
            reduction = round(
                100 * (1 - assisted["median_total_ms"] / manual["median_decision_ms"]), 1
            )
        return {
            "schema_version": 1,
            "measurement": "paired_category_operator_study",
            "status": "awaiting_completed_sessions"
            if not complete_ids
            else "descriptive_results_available",
            "started_sessions": len(sessions),
            "completed_sessions": len(complete_ids),
            "completed_relevant_operator_sessions": relevant,
            "completed_session_roles": roles,
            "submitted_tasks_including_incomplete_sessions": len(rows),
            "conditions": by_condition,
            "exploratory_total_time_change_pct": reduction,
            "resume_claim_ready": False,
            "claim_note": (
                "No completed human session is available. Do not claim time saved or operator adoption."
                if not complete_ids
                else "Descriptive comparison only. Review case mix, learning effects, timing outliers, and uncertainty; the study owner must confirm at least five distinct relevant operators before considering an impact claim."
            ),
        }
