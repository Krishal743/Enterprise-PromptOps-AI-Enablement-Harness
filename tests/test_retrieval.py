from ops_ai.retrieval import KnowledgeIndex


def test_exact_code_outweighs_similar_symptoms():
    index = KnowledgeIndex()
    results = index.search("The dashboard has a charging warning", "S-CON-502")
    assert results[0]["id"] == "KB-CON-502"


def test_unknown_or_out_of_scope_request_has_no_evidence():
    index = KnowledgeIndex()
    assert index.search("Unknown warning code X-999 appeared with no symptoms", "X-999") == []
    assert index.search("What is the company's quarterly revenue?") == []


def test_symptom_vector_search():
    index = KnowledgeIndex()
    assert index.search("bluetooth app pairing failed")[0]["id"] == "KB-CON-501"
