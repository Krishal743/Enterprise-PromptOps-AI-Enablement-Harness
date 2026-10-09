from __future__ import annotations

from collections import Counter
from uuid import uuid4

import pytest

from ops_ai.study import CASE_PAIRS, StudyStore, assignments, golden_cases
from scripts.benchmark_routing import percentile, summarize


def test_assignments_balance_conditions_and_hide_expected_labels(tmp_path):
    study_id = str(uuid4())
    planned = assignments(study_id)
    assert len(planned) == 14
    for pair in CASE_PAIRS.values():
        assert Counter(condition for case_id, condition in planned if case_id in pair) == {
            "manual": 1,
            "assisted": 1,
        }
    opposite = dict(assignments(study_id, arm=1))
    assert all(opposite[case_id] != condition for case_id, condition in planned)
    store = StudyStore(tmp_path / "study.db")
    study_id = store.start("field_supervisor")
    task = store.next_task(study_id)
    assert "expected_team" not in task
    assert "expected_priority" not in task
    assert "must_review" not in task


def test_completed_session_records_times_and_feedback_once(tmp_path, monkeypatch):
    store = StudyStore(tmp_path / "study.db")
    study_id = store.start("service_operations")
    cases = golden_cases()
    now = [1_000_000_000_000]
    monkeypatch.setattr("ops_ai.study.time.time_ns", lambda: now[0])
    first_sequence = None
    for _ in range(14):
        task = store.next_task(study_id)
        if first_sequence is None:
            first_sequence = task["sequence"]
        gold = cases[task["case_id"]]
        if task["condition"] == "assisted":
            store.attach_ai(
                study_id,
                task["sequence"],
                250.0,
                {"recommended_team": gold["expected_team"]},
            )
        store.mark_shown(study_id, task["sequence"])
        now[0] += 1_000_000_000 if task["condition"] == "manual" else 2_000_000_000
        store.submit(
            study_id,
            task["sequence"],
            team=gold["expected_team"],
            priority=gold["expected_priority"],
            review=gold["must_review"],
            confidence=4,
            usefulness=5 if task["condition"] == "assisted" else None,
            comment="fictional task",
        )
        now[0] += 1_000_000

    assert store.progress(study_id) == (14, 14)
    assert store.next_task(study_id) is None
    with pytest.raises(ValueError, match="not active"):
        store.submit(
            study_id,
            first_sequence,
            team="battery",
            priority="routine",
            review=False,
            confidence=3,
            usefulness=None,
            comment="",
        )
    report = store.report()
    assert report["completed_sessions"] == 1
    assert report["completed_relevant_operator_sessions"] == 1
    assert report["conditions"]["manual"]["decisions"] == 7
    assert report["conditions"]["assisted"]["decisions"] == 7
    assert report["conditions"]["manual"]["team_correct"] == 7
    assert report["conditions"]["assisted"]["team_correct"] == 7
    assert report["conditions"]["assisted"]["median_usefulness"] == 5
    assert report["resume_claim_ready"] is False


def test_empty_study_report_cannot_support_impact_claim(tmp_path):
    report = StudyStore(tmp_path / "study.db").report()
    assert report["status"] == "awaiting_completed_sessions"
    assert report["conditions"] == {"manual": None, "assisted": None}
    assert report["exploratory_total_time_change_pct"] is None
    assert report["resume_claim_ready"] is False


def test_benchmark_percentile_and_correctness_summary():
    rows = [
        {
            "duration_ms": duration,
            "case_type": "routine",
            "team_correct": True,
            "priority_correct": True,
            "review_correct": duration != 30,
            "actual_team": "charging" if duration != 30 else "human_review",
        }
        for duration in (10, 20, 30)
    ]
    assert percentile([10, 20, 30], 0.95) == 29
    summary = summarize(rows)
    assert summary["median_ms"] == 20
    assert summary["all_three_correct"] == 2
    assert summary["human_review_routes"] == 1
    assert summary["by_route"]["field_team"]["case_count"] == 2
    assert summary["by_case_type"]["routine"]["median_ms"] == 20
