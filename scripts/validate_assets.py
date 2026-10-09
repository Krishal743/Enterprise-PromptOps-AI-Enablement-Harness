"""Validate the versioned knowledge base and 50-case golden suite without dependencies."""

from __future__ import annotations

import json
import re
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

    redteam = json.loads((ROOT / "data" / "redteam.json").read_text(encoding="utf-8"))
    assert len(redteam) >= 8
    ids = [case["vars"]["case_id"] for case in redteam]
    assert len(ids) == len(set(ids))
    assert all(case_id.startswith("RT") for case_id in ids)
    for case in redteam:
        variables = case["vars"]
        source = variables["expected_source"]
        assert variables["forbidden_phrases"], variables["case_id"]
        assert source == "" or source in index.by_id, variables["case_id"]
        found = index.search(variables["description"], variables["diagnostic_code"])
        assert (source in [doc["id"] for doc in found]) if source else not found, variables[
            "case_id"
        ]

    template_root = ROOT / "prompts" / "templates"
    manifest = json.loads((template_root / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 3
    assert len({entry["id"] for entry in manifest}) == len(manifest)
    for entry in manifest:
        assert entry["file"] == f"{entry['id']}.md"
        template = (template_root / entry["file"]).read_text(encoding="utf-8")
        prompt_body = template.split("```text\n", 1)[1].split("```", 1)[0]
        placeholders = set(re.findall(r"\{([a-z_]+)\}", prompt_body))
        assert placeholders == set(entry["parameters"]), entry["id"]
        assert entry["purpose"] and entry["review_check"]
    print(
        f"Validated {len(index.documents)} articles, {len(cases)} golden cases, "
        f"{len(redteam)} red-team cases, and {len(manifest)} reusable templates"
    )


if __name__ == "__main__":
    main()
