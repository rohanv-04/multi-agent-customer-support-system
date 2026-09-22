from typing import Dict, Any
from ..rag.retrieval import retrieve_policy_knowledge

def run_retrieval_agent(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Agent 3 — Knowledge Retrieval Agent (RAG).

    Queries indexed NovaCart corporate policies (Refund, Return, Shipping, Warranty, Cancellation, Escalation)
    and returns semantically relevant excerpts with document citations and confidence scores.
    """
    rag_result = retrieve_policy_knowledge(query=query, top_k=top_k)
    return {
        "agent": "Knowledge Retrieval Agent",
        "query": query,
        "found": rag_result["found"],
        "citations": rag_result["citations"],
        "context": rag_result["combined_context"],
        "confidence": rag_result["confidence"]
    }
