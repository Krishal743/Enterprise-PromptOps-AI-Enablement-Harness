"""Compile framework-neutral golden records into Promptfoo test definitions."""

from __future__ import annotations

import argparse
import json
import os

from ops_ai.settings import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "structural"], default="full")
    parser.add_argument("--sample-per-type", type=int, default=0)
    args = parser.parse_args()
    if args.sample_per_type < 0:
        parser.error("--sample-per-type must be nonnegative")
    golden = json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))
    knowledge = {
        doc["id"]: doc
        for doc in json.loads((ROOT / "data" / "knowledge.json").read_text(encoding="utf-8"))
    }
    tests = []
    counts: dict[str, int] = {}
    for case in golden:
        variables = dict(case["vars"])
        case_type = variables["case_type"]
        if args.sample_per_type and counts.get(case_type, 0) >= args.sample_per_type:
            continue
        counts[case_type] = counts.get(case_type, 0) + 1
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
        if source_id and args.mode == "full":
            source = knowledge[source_id]
            variables["reference_guidance"] = f"{source['summary']} {source['customer_guidance']}"
            judge_id = os.getenv("OPS_EVAL_JUDGE", "ollama:chat:qwen3:4b")
            judge = (
                {
                    "id": judge_id,
                    "config": {
                        "think": False,
                        "showThinking": False,
                        "temperature": 0,
                        "num_predict": 512,
                        "format": {
                            "type": "object",
                            "properties": {
                                "pass": {"type": "boolean"},
                                "score": {"type": "number"},
                                "reason": {"type": "string"},
                            },
                            "required": ["pass", "score", "reason"],
                        },
                    },
                }
                if judge_id.startswith("ollama:")
                else judge_id
            )
            assertions.append(
                {
                    "type": "llm-rubric",
                    "metric": "groundedness",
                    "provider": judge,
                    "threshold": 0.8,
                    "value": (
                        "Check whether diagnostic_summary and customer_reply contain factual claims "
                        "unsupported by this reference guidance: {{reference_guidance}}. "
                        "Omitting details from the reference is allowed; the reply need not repeat every "
                        "step. Pass when the output is a supported subset of the reference. Fail only "
                        "for unsupported diagnoses, repair steps, prices, contact or appointment "
                        "promises, or unsafe riding advice. Ignore other JSON fields."
                    ),
                }
            )
        tests.append({"description": case["description"], "vars": variables, "assert": assertions})
    output = ROOT / "eval" / "promptfoo_cases.json"
    output.write_text(json.dumps(tests, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(tests)} Promptfoo cases to {output}")


if __name__ == "__main__":
    main()
