import pytest
from backend.app.rag.vector_store import (
    BaseVectorStore,
    InMemoryVectorStore,
    PGVectorStore,
    get_vector_store,
    policy_store
)


def test_vector_store_abstraction_instances():
    """Verify VectorStore inheritance and factory mechanics."""
    in_memory = InMemoryVectorStore()
    assert isinstance(in_memory, BaseVectorStore)

    pg_store = PGVectorStore()
    assert isinstance(pg_store, BaseVectorStore)

    current_store = get_vector_store()
    assert isinstance(current_store, BaseVectorStore)


def test_vector_store_indexing_and_search():
    """Verify document chunking, indexing, and semantic retrieval."""
    store = InMemoryVectorStore()
    store.index_documents()
    assert len(store.chunks) > 0
    assert store.is_indexed is True

    # Search for refund policy
    results = store.search("I want a refund for damaged item", top_k=2)
    assert len(results) > 0
    first = results[0]
    assert "refund" in first["source"].lower() or "refund" in first["title"].lower()
    assert first["confidence"] >= 0.50
    assert "policy_version" in first
    assert "effective_date" in first


def test_vector_store_tenant_isolation():
    """Verify that queries for a different tenant do NOT return foreign tenant documents."""
    store = InMemoryVectorStore()
    store.index_documents()

    # Default tenant has documents
    results_novacart = store.search("shipping delivery delay", top_k=3, tenant_id="ORG-NOVACART")
    assert len(results_novacart) > 0

    # Foreign tenant must return empty (isolated)
    results_foreign = store.search("shipping delivery delay", top_k=3, tenant_id="ORG-COMPETITOR-INC")
    assert len(results_foreign) == 0


def test_vector_store_metadata_filtering():
    """Verify metadata filtering by category or version."""
    store = InMemoryVectorStore()
    store.index_documents()

    # Filter strictly for Shipping category
    results = store.search("delay", top_k=5, metadata_filter={"category": "Shipping"})
    for r in results:
        assert r["category"] == "Shipping"
