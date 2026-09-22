from fastapi import APIRouter

router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENTS_REGISTRY = [
    {
        "id": "supervisor",
        "name": "Supervisor Agent",
        "role": "Master Orchestrator & State Evaluator",
        "status": "active",
        "confidence_avg": 0.96,
        "purpose": "Decides workflows, breaks complex goals into subtasks, coordinates specialist nodes, manages replanning cycles, and crafts final response.",
        "tools_accessible": ["All Tools", "Specialist Agents", "Database Transaction Layer"]
    },
    {
        "id": "intent",
        "name": "Intent & Goal Agent",
        "role": "Semantic Goal Classifier & Entity Extractor",
        "status": "active",
        "confidence_avg": 0.95,
        "purpose": "Parses customer prompts, extracts Order and Customer IDs, detects urgency, flags missing attributes, and categorizes intent.",
        "tools_accessible": ["Regex Parser", "Entity Normalizer"]
    },
    {
        "id": "planner",
        "name": "Planning Agent",
        "role": "Dynamic Step Architect",
        "status": "active",
        "confidence_avg": 0.93,
        "purpose": "Constructs structured DAG execution plans based on extracted entities and corporate business rules.",
        "tools_accessible": ["Task State Graph"]
    },
    {
        "id": "retrieval",
        "name": "Knowledge Retrieval Agent",
        "role": "Corporate RAG Grounding Specialist",
        "status": "active",
        "confidence_avg": 0.94,
        "purpose": "Performs semantic vector search across indexed NovaCart corporate policies (Refund, Return, Shipping, Warranty).",
        "tools_accessible": ["PolicyVectorStore", "TF-IDF Embedder", "Document Chunker"]
    },
    {
        "id": "resolution",
        "name": "Resolution / Action Agent",
        "role": "Autonomous Tool Operator & Subtask Solver",
        "status": "active",
        "confidence_avg": 0.91,
        "purpose": "Invokes database tools safely, evaluates refund eligibility, analyzes tracking telemetry, and executes controlled financial refunds.",
        "tools_accessible": ["get_order_status", "get_customer_info", "check_refund_eligibility", "process_refund"]
    },
    {
        "id": "critic",
        "name": "Critic / Validation Agent",
        "role": "Quality Gatekeeper & Compliance Auditor",
        "status": "active",
        "confidence_avg": 0.95,
        "purpose": "Audits tool execution results, verifies policy grounding, guards against hallucinated refunds, and routes to replan or escalation if issues emerge.",
        "tools_accessible": ["Policy Compliance Engine", "Confidence Evaluator"]
    },
    {
        "id": "escalation",
        "name": "Escalation Agent",
        "role": "Human Support Handoff Dossier Compiler",
        "status": "active",
        "confidence_avg": 0.98,
        "purpose": "Generates prioritized human support tickets with full execution audit trails, customer tier context, and actionable recommendations.",
        "tools_accessible": ["EscalationTicket DB", "Dossier Generator"]
    }
]

@router.get("")
def list_agents():
    return {"agents": AGENTS_REGISTRY}
