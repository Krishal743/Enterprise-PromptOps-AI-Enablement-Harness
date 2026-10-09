"""Export aggregate operator-study results without participant comments or IDs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ops_ai.study import StudyStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".data/operator-study-report.json"))
    parser.add_argument("--stdout", action="store_true", help="Print JSON for Docker export")
    args = parser.parse_args()
    report = StudyStore().report()
    if args.stdout:
        print(json.dumps(report, indent=2))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{report['completed_sessions']} completed sessions; "
        f"status={report['status']}; wrote {args.output}"
    )


if __name__ == "__main__":
    main()
