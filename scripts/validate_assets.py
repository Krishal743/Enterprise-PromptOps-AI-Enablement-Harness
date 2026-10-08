"""Validate the versioned knowledge base and 50-case golden suite without dependencies."""

from __future__ import annotations

import json
from collections import Counter

from ops_ai.retrieval import KnowledgeIndex
from ops_ai.settings import ROOT


def main() -> None:
    index = KnowledgeIndex()
    cases = json.loads((ROOT / "data" / "golden.json").read_text(encoding="utf-8"))
    assert len(index.documents) >= 10
    assert len(index.by_id) == len(index.documents)
    assert len(index.by_code) == len(index.documents)
    assert len(cases) == 50
    assert len({case["vars"]["case_id"] for case in cases}) == 50
    categories = Counter(case["vars"]["case_type"] for case in cases)
    assert categories == {
        "routine": 12,
        "ambiguous": 8,
        "safety": 8,
        "missing": 7,
        "tone": 5,
        "injection": 5,
        "out_of_scope": 5,
    }
    for case in cases:
        variables = case["vars"]
        source = variables["expected_source"]
        assert variables["expected_reply"].strip(), variables["case_id"]
        if source:
            assert source in index.by_id, variables["case_id"]
        if variables["diagnostic_code"] in index.by_code:
            found = index.search(variables["description"], variables["diagnostic_code"])
            assert found and found[0]["code"] == variables["diagnostic_code"], variables["case_id"]
        if variables["case_type"] != "safety":
            found = index.search(variables["description"], variables["diagnostic_code"])
            team = found[0]["team"] if found else "human_review"
            assert team == variables["expected_team"], variables["case_id"]
    print(f"Validated {len(index.documents)} articles and {len(cases)} golden cases")


if __name__ == "__main__":
    main()
