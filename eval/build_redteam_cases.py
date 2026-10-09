"""Compile the separate red-team dataset into Promptfoo cases."""

from __future__ import annotations

import json

from ops_ai.settings import ROOT


def main() -> None:
    cases = json.loads((ROOT / "data" / "redteam.json").read_text(encoding="utf-8"))
    tests = []
    for case in cases:
        variables = dict(case["vars"])
        variables["forbidden_phrases_json"] = json.dumps(variables.pop("forbidden_phrases"))
        variables["required_reply_phrases_json"] = json.dumps(
            variables.pop("required_reply_phrases", [])
        )
        if variables["diagnostic_code"] is None:
            variables.pop("diagnostic_code")
        tests.append(
            {
                "description": case["description"],
                "vars": variables,
                "assert": [
                    {
                        "type": "python",
                        "value": "file://eval/redteam_assertions.py",
                        "metric": "red_team_guardrails",
                    }
                ],
            }
        )
    output = ROOT / "eval" / "redteam_promptfoo_cases.json"
    output.write_text(json.dumps(tests, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(tests)} red-team cases to {output}")


if __name__ == "__main__":
    main()
