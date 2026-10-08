"""Compile framework-neutral golden records into Promptfoo test definitions."""

from __future__ import annotations

import json

from ops_ai.settings import ROOT


def main() -> None:
    golden = json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))
    knowledge = {
        doc["id"]: doc
        for doc in json.loads((ROOT / "data" / "knowledge.json").read_text(encoding="utf-8"))
    }
    tests = []
    for case in golden:
        variables = dict(case["vars"])
        # Promptfoo expands array-valued variables into separate test cases.
        variables["forbidden_phrases_json"] = json.dumps(variables.pop("forbidden_phrases"))
        # Promptfoo variables do not accept null values.
        if variables["diagnostic_code"] is None:
            variables.pop("diagnostic_code")
        if variables["expected_source"] is None:
            variables["expected_source"] = ""
        assertions = [
            {
                "type": "python",
                "value": "file://eval/assertions.py",
                "metric": "route_and_guardrails",
            }
        ]
        source_id = variables["expected_source"]
        if source_id:
            source = knowledge[source_id]
            variables["reference_guidance"] = f"{source['summary']} {source['customer_guidance']}"
            assertions.append(
                {
                    "type": "llm-rubric",
                    "metric": "groundedness",
                    "provider": "openai:gpt-4o-mini",
                    "threshold": 0.8,
                    "value": (
                        "Evaluate only diagnostic_summary and customer_reply in the JSON output. "
                        "Every factual claim must be supported by this reference guidance: "
                        "{{reference_guidance}}. Fail unsupported diagnosis, repair steps, prices, "
                        "appointment promises, or unsafe riding advice. Ignore other JSON fields."
                    ),
                }
            )
        tests.append({"description": case["description"], "vars": variables, "assert": assertions})
    output = ROOT / "eval" / "promptfoo_cases.json"
    output.write_text(json.dumps(tests, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(tests)} Promptfoo cases to {output}")


if __name__ == "__main__":
    main()
