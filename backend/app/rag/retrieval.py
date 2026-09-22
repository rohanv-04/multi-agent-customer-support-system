from typing import List, Dict, Any
from .vector_store import policy_store

def retrieve_policy_knowledge(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Retrieve relevant policies and return structured context with citations and confidence."""
    matches = policy_store.query(query, top_k=top_k)
    if not matches:
        return {
            "found": False,
            "query": query,
            "citations": [],
            "combined_context": "No specific policy document directly matched the query.",
            "confidence": 0.50
        }

    combined_context = "\n\n---\n\n".join([
        f"[{m['category']} Policy - {m['header']}]\n{m['content']}"
        for m in matches
    ])

    avg_confidence = round(sum(m["confidence"] for m in matches) / len(matches), 2)

    return {
        "found": True,
        "query": query,
        "citations": [
            {
                "document": m["source"],
                "category": m["category"],
                "section": m["header"],
                "confidence": m["confidence"]
            }
            for m in matches
        ],
        "combined_context": combined_context,
        "confidence": avg_confidence
    }

__all__ = ["retrieve_policy_knowledge", "policy_store"]
