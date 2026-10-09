"""Measure live triage recommendation latency on the versioned golden cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from ops_ai.schemas import TicketRequest
from ops_ai.service import triage
from ops_ai.settings import ROOT, provider_name, tracing_enabled


def repository_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else os.getenv("OPS_REVISION", "unknown")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("At least one duration is required")
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def measure(case: dict, prompt_version: str) -> dict:
    expected = case["vars"]
    request = TicketRequest(
        description=expected["description"],
        diagnostic_code=expected["diagnostic_code"],
        prompt_version=prompt_version,
        session_id=f"routing-benchmark-{expected['case_id']}",
    )
    started = time.perf_counter()
    result = triage(request, persist=False)
    duration_ms = (time.perf_counter() - started) * 1000
    return {
        "case_id": expected["case_id"],
        "case_type": expected["case_type"],
        "duration_ms": round(duration_ms, 1),
        "expected_team": expected["expected_team"],
        "actual_team": result.recommended_team.value,
        "expected_priority": expected["expected_priority"],
        "actual_priority": result.priority.value,
        "expected_review": expected["must_review"],
        "actual_review": result.review_required,
        "team_correct": result.recommended_team.value == expected["expected_team"],
        "priority_correct": result.priority.value == expected["expected_priority"],
        "review_correct": result.review_required == expected["must_review"],
    }


def summarize(rows: list[dict]) -> dict:
    durations = [row["duration_ms"] for row in rows]
    by_route = {}
    for route, matches in (
        ("field_team", lambda row: row["actual_team"] != "human_review"),
        ("human_review", lambda row: row["actual_team"] == "human_review"),
    ):
        group = [row["duration_ms"] for row in rows if matches(row)]
        if group:
            by_route[route] = {
                "case_count": len(group),
                "median_ms": round(statistics.median(group), 1),
                "p95_ms": round(percentile(group, 0.95), 1),
            }
    by_case_type = {}
    for case_type in sorted({row["case_type"] for row in rows}):
        group = [row["duration_ms"] for row in rows if row["case_type"] == case_type]
        by_case_type[case_type] = {
            "case_count": len(group),
            "median_ms": round(statistics.median(group), 1),
            "p95_ms": round(percentile(group, 0.95), 1),
        }
    return {
        "case_count": len(rows),
        "median_ms": round(statistics.median(durations), 1),
        "p95_ms": round(percentile(durations, 0.95), 1),
        "mean_ms": round(statistics.mean(durations), 1),
        "min_ms": round(min(durations), 1),
        "max_ms": round(max(durations), 1),
        "team_correct": sum(row["team_correct"] for row in rows),
        "priority_correct": sum(row["priority_correct"] for row in rows),
        "review_correct": sum(row["review_correct"] for row in rows),
        "all_three_correct": sum(
            row["team_correct"] and row["priority_correct"] and row["review_correct"]
            for row in rows
        ),
        "human_review_routes": sum(row["actual_team"] == "human_review" for row in rows),
        "by_route": by_route,
        "by_case_type": by_case_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".data/routing-benchmark.json"))
    parser.add_argument("--prompt-version", default="v2")
    args = parser.parse_args()
    if provider_name() == "mock":
        parser.error("Set OPS_LLM_PROVIDER=ollama or openai for a live timing measurement")
    cases = json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))
    print("Warming the model; warm-up is excluded from the report.", flush=True)
    measure(cases[0], args.prompt_version)
    rows = []
    for index, case in enumerate(cases, start=1):
        row = measure(case, args.prompt_version)
        rows.append(row)
        print(
            f"{index:02d}/{len(cases)} {row['case_id']} {row['duration_ms']:.1f} ms "
            f"route={'ok' if row['team_correct'] else 'mismatch'}",
            flush=True,
        )
    report = {
        "schema_version": 1,
        "measurement": "service_recommendation_wall_time",
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "provider": provider_name(),
        "model": os.getenv("OPS_MODEL", "qwen3:4b"),
        "prompt_version": args.prompt_version,
        "service_revision": repository_revision(),
        "golden_sha256": hashlib.sha256((ROOT / "data" / "golden.json").read_bytes()).hexdigest(),
        "knowledge_sha256": hashlib.sha256(
            (ROOT / "data" / "knowledge.json").read_bytes()
        ).hexdigest(),
        "prompt_sha256": hashlib.sha256(
            (ROOT / "prompts" / f"triage_{args.prompt_version}.txt").read_bytes()
        ).hexdigest(),
        "tracing_enabled": tracing_enabled(),
        "host": {"architecture": platform.machine(), "logical_cpus": os.cpu_count()},
        "warmup_cases": 1,
        "summary": summarize(rows),
        "cases": rows,
        "limitations": [
            "Synthetic tickets and one local host; no human routing time is measured here.",
            "Wall time includes retrieval, model generation, validation, and tracing, but excludes HTTP and UI rendering.",
            "This report does not establish a percentage reduction in manual routing time.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} measured cases to {args.output}", flush=True)


if __name__ == "__main__":
    main()
