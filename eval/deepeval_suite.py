"""Optional LLM-judge report. Requires `pip install -e '.[eval]'` and API credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ops_ai.retrieval import get_index
from ops_ai.schemas import TicketRequest
from ops_ai.service import triage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of evidence-backed cases to score"
    )
    parser.add_argument("--output", default="eval-results-deepeval.json")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for DeepEval judges")

    from deepeval.metrics import AnswerRelevancyMetric, ContextualRecallMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    cases = json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "golden.json").read_text()
    )
    selected = [case["vars"] for case in cases if case["vars"]["expected_source"]][: args.limit]
    results = []
    for case in selected:
        ticket = TicketRequest(
            description=case["description"],
            diagnostic_code=case["diagnostic_code"],
            prompt_version="v2",
        )
        result = triage(ticket, persist=False)
        docs = [get_index().by_id[source_id] for source_id in result.retrieval_ids]
        reference = get_index().by_id[case["expected_source"]]
        test_case = LLMTestCase(
            input=case["description"],
            actual_output=f"{result.diagnostic_summary} {result.customer_reply}",
            expected_output=reference["summary"],
            retrieval_context=[
                f"{doc['title']}. {doc['summary']} {doc['customer_guidance']}" for doc in docs
            ],
        )
        metrics = {
            "answer_relevancy": AnswerRelevancyMetric(threshold=0.7, async_mode=False),
            "faithfulness": FaithfulnessMetric(threshold=0.8, async_mode=False),
            "contextual_recall": ContextualRecallMetric(threshold=0.8, async_mode=False),
        }
        scores = {}
        for name, metric in metrics.items():
            metric.measure(test_case)
            scores[name] = {"score": metric.score, "reason": metric.reason}
        results.append({"case_id": case["case_id"], "scores": scores})
    Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} scored cases to {args.output}")


if __name__ == "__main__":
    main()
