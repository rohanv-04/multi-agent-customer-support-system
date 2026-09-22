from typing import TypedDict, List, Dict, Any, Optional

class AgenticSupportState(TypedDict):
    task_id: str
    customer_id: str
    conversation_id: str
    user_goal: str
    messages: List[Dict[str, Any]]
    case_id: Optional[str]  # SupportOS AI Central Support Case ID
    
    # Customer 360 & Intake
    customer_360: Optional[Dict[str, Any]]
    intent: Dict[str, Any]
    
    # Investigation
    investigation_result: Optional[Dict[str, Any]]
    
    # Policy Intelligence, Decision & Risk (Sprint 3)
    policy_evaluation: Optional[Dict[str, Any]]
    decision_result: Optional[Dict[str, Any]]
    risk_evaluation: Optional[Dict[str, Any]]
    
    # Planning & progression
    plan: List[str]
    completed_steps: List[str]
    pending_steps: List[str]
    
    # Execution telemetry
    agent_outputs: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    retrieved_docs: List[Dict[str, Any]]
    
    # Decision controls
    confidence: float
    status: str
    requires_escalation: bool
    replan_count: int
    iteration_count: int
    critic_result: Dict[str, Any]
    escalation_dossier: Optional[Dict[str, Any]]
    
    # Final resolution
    final_response: str
    execution_trace: List[Dict[str, Any]]
