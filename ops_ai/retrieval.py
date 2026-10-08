"""Small local TF-IDF vector index plus exact diagnostic-code lookup.

The corpus is intentionally small and versioned. The vector calculation is kept local so
the application and regression tests can run without a hosted embedding service.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from ops_ai.settings import KB_PATH

STOP = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "but",
    "code",
    "did",
    "error",
    "for",
    "from",
    "happened",
    "has",
    "i",
    "in",
    "is",
    "issue",
    "it",
    "my",
    "normal",
    "not",
    "of",
    "on",
    "or",
    "please",
    "problem",
    "record",
    "scooter",
    "service",
    "sometimes",
    "the",
    "think",
    "to",
    "today",
    "vehicle",
    "warning",
    "with",
}


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP]


class KnowledgeIndex:
    def __init__(self, path: Path = KB_PATH):
        self.documents: list[dict] = json.loads(path.read_text(encoding="utf-8"))
        self.by_code = {doc["code"].upper(): doc for doc in self.documents}
        self.by_id = {doc["id"]: doc for doc in self.documents}
        self.counts = [
            Counter(tokens(" ".join(str(doc[key]) for key in ("title", "symptoms"))))
            for doc in self.documents
        ]
        df = Counter(word for counts in self.counts for word in counts)
        self.idf = {
            word: math.log((len(self.documents) + 1) / (frequency + 1)) + 1
            for word, frequency in df.items()
        }
        self.vectors = [self._vector(counts) for counts in self.counts]

    def _vector(self, counts: Counter[str]) -> dict[str, float]:
        values = {
            word: (1 + math.log(count)) * self.idf.get(word, 0.0) for word, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in values.values())) or 1.0
        return {word: value / norm for word, value in values.items()}

    def search(
        self, description: str, diagnostic_code: str | None = None, limit: int = 3
    ) -> list[dict]:
        query_counts = Counter(tokens(description))
        query = self._vector(query_counts)
        ranked = []
        for doc, vector in zip(self.documents, self.vectors, strict=True):
            score = sum(weight * vector.get(word, 0.0) for word, weight in query.items())
            exact_code = bool(diagnostic_code and doc["code"] == diagnostic_code.upper().strip())
            if exact_code:
                score += 2.0
            overlap = len(set(query) & set(vector))
            if exact_code or (overlap >= 2 and score >= 0.18):
                ranked.append((score, doc))
        ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [doc for _, doc in ranked[:limit]]


@lru_cache(maxsize=1)
def get_index() -> KnowledgeIndex:
    return KnowledgeIndex()
