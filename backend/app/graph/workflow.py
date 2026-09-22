import datetime
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END
from .state import AgenticSupportState
from ..agents import (
    run_intent_agent,
    run_planner_agent,
    run_retrieval_agent,
    run_resolution_agent,
    run_critic_agent,
    run_escalation_agent,
    format_final_customer_response
)
from ..database.database import SessionLocal
from ..database.models import Task, TaskStep, AgentAction, CustomerMemory

def add_trace(state: AgenticSupportState, agent: str, action: str, details: Any = None, status: str = "completed") -> Dict[str, Any]:
    trace_event = {
        "timestamp": datetime.datetime.utcnow().strftime("%H:%M:%S"),
        "iso_time": datetime.datetime.utcnow().isoformat(),
        "agent": agent,
        "action": action,
        "details": details,
        "status": status
    }
    state["execution_trace"].append(trace_event)
    return trace_event

# ----------------- NODE DEFINITIONS -----------------

def supervisor_init_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Initialize workflow state, task record in SQLite, and trace log."""
    now = datetime.datetime.utcnow()
    db = SessionLocal()
    try:
        task = Task(
            task_id=state["task_id"],
            conversation_id=state.get("conversation_id"),
            customer_id=state.get("customer_id"),
            user_goal=state["user_goal"],
            status="in_progress",
            created_at=now
        )
        db.add(task)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB Task Init Error]: {e}")
    finally:
        db.close()

    add_trace(state, "Supervisor Agent", "Task initiated & state workspace created", {"goal": state["user_goal"]})
    return {
        "status": "in_progress",
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def intent_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 1 — Intent & Goal Extraction."""
    intent_data = run_intent_agent(
        user_goal=state["user_goal"],
        customer_id=state.get("customer_id", "CUST1002")
    )
    add_trace(
        state,
        "Intent & Goal Agent",
        f"Goal identified: '{intent_data.get('intent')}'",
        {
            "entities": intent_data.get("entities"),
            "urgency": intent_data.get("urgency"),
            "confidence": intent_data.get("confidence")
        }
    )
    return {
        "intent": intent_data,
        "confidence": intent_data.get("confidence", 0.95)
    }

def planner_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 2 — Dynamic Planning."""
    plan_data = run_planner_agent(
        user_goal=state["user_goal"],
        intent_data=state["intent"]
    )
    steps = plan_data.get("steps", [])

    # Persist steps in database
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == state["task_id"]).first()
        if task:
            task.intent = state["intent"].get("intent")
            task.confidence = plan_data.get("confidence", 0.93)
        for idx, step_desc in enumerate(steps, 1):
            db.add(TaskStep(
                task_id=state["task_id"],
                step_number=idx,
                description=step_desc,
                status="pending"
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB Plan Steps Error]: {e}")
    finally:
        db.close()

    add_trace(
        state,
        "Planning Agent",
        f"{len(steps)}-step execution plan created",
        {"steps": steps, "confidence": plan_data.get("confidence")}
    )

    return {
        "plan": steps,
        "pending_steps": list(steps),
        "completed_steps": [],
        "confidence": plan_data.get("confidence", 0.93)
    }

def retrieval_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 3 — Knowledge Retrieval (RAG)."""
    intent_str = state["intent"].get("intent", "")
    query = state["user_goal"]
    if "refund" in intent_str:
        query = f"refund policy delayed shipping {state['user_goal']}"
    elif "status" in intent_str:
        query = "shipping transit delivery times tracking"

    rag_result = run_retrieval_agent(query=query, top_k=2)
    state["retrieved_docs"].append(rag_result)

    citations = [f"{c['category']} ({c['section']})" for c in rag_result.get("citations", [])]
    add_trace(
        state,
        "Knowledge Retrieval Agent",
        f"Retrieved policy knowledge ({len(citations)} citations)",
        {"citations": citations, "confidence": rag_result.get("confidence")}
    )

    return {
        "retrieved_docs": state["retrieved_docs"],
        "confidence": max(state["confidence"], rag_result.get("confidence", 0.90))
    }

def resolution_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 4 — Resolution / Action Agent. Executes subtasks & tools."""
    pending = list(state.get("pending_steps", []))
    completed = list(state.get("completed_steps", []))
    observations = list(state.get("observations", []))
    tool_calls = list(state.get("tool_calls", []))

    order_data = {}
    eligibility_data = {}

    # Execute all actionable pending steps
    while pending:
        step = pending.pop(0)
        res = run_resolution_agent(
            current_step=step,
            task_id=state["task_id"],
            intent_data=state["intent"],
            order_data=order_data,
            eligibility_data=eligibility_data,
            policy_context=state["retrieved_docs"][-1]["context"] if state.get("retrieved_docs") else ""
        )

        completed.append(step)
        observations.append(res)

        if res.get("tool_used"):
            tool_call_summary = {
                "tool_name": res["tool_used"],
                "result": res["tool_output"],
                "status": "success" if res["success"] else "failure"
            }
            tool_calls.append(tool_call_summary)

            add_trace(
                state,
                f"{res['tool_used'].replace('_', ' ').title()}",
                res["observation"],
                {"tool": res["tool_used"], "output": res["tool_output"]}
            )

            # Keep track for subsequent steps
            if res["tool_used"] == "get_order_status" and res["tool_output"]:
                order_data = res["tool_output"]
            elif res["tool_used"] == "check_refund_eligibility" and res["tool_output"]:
                eligibility_data = res["tool_output"]
        else:
            add_trace(
                state,
                "Resolution Agent",
                res["observation"],
                {"step": step}
            )

    return {
        "completed_steps": completed,
        "pending_steps": [],
        "observations": observations,
        "tool_calls": tool_calls
    }

def critic_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 5 — Critic / Validation Agent."""
    critic_res = run_critic_agent(
        task_goal=state["user_goal"],
        intent_data=state["intent"],
        plan=state["plan"],
        completed_steps=state["completed_steps"],
        observations=state["observations"],
        tool_calls=state["tool_calls"],
        rag_data=state["retrieved_docs"][-1] if state.get("retrieved_docs") else None,
        replan_count=state.get("replan_count", 0)
    )

    add_trace(
        state,
        "Critic Agent",
        critic_res.get("audit_summary"),
        {
            "valid": critic_res.get("valid"),
            "confidence": critic_res.get("confidence"),
            "recommended_action": critic_res.get("recommended_action")
        }
    )

    return {
        "critic_result": critic_res,
        "confidence": critic_res.get("confidence", state["confidence"])
    }

def replanning_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Handles replanning loop when Critic flags issues (max 5 iterations)."""
    current_replan = state.get("replan_count", 0) + 1
    add_trace(
        state,
        "Supervisor Agent",
        f"Re-planning loop triggered (Iteration {current_replan}/5)",
        {"reason": state["critic_result"].get("issues")},
        status="warning"
    )

    # Insert corrective step
    corrective_step = "Retry alternative verification and validate customer profile"
    new_pending = [corrective_step]

    return {
        "replan_count": current_replan,
        "pending_steps": new_pending,
        "status": "replanning"
    }

def escalation_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 6 — Escalation Agent."""
    reason = "Customer requested human support"
    if state.get("critic_result") and state["critic_result"].get("issues"):
        reason = "; ".join(state["critic_result"]["issues"])

    dossier = run_escalation_agent(
        task_id=state["task_id"],
        customer_id=state.get("customer_id", "CUST1002"),
        user_goal=state["user_goal"],
        intent_data=state.get("intent", {}),
        plan=state.get("plan", []),
        completed_steps=state.get("completed_steps", []),
        tool_calls=state.get("tool_calls", []),
        observations=state.get("observations", []),
        reason=reason
    )

    add_trace(
        state,
        "Escalation Agent",
        f"Escalation ticket #{dossier['ticket_id']} created for Human Support Desk",
        {"ticket": dossier},
        status="warning"
    )

    return {
        "escalation_dossier": dossier,
        "requires_escalation": True,
        "status": "escalated"
    }

def complete_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Synthesize final customer response, record memory, and mark task completed."""
    final_text = format_final_customer_response(
        intent_data=state.get("intent", {}),
        observations=state.get("observations", []),
        tool_calls=state.get("tool_calls", []),
        rag_data=state["retrieved_docs"][-1] if state.get("retrieved_docs") else None,
        escalation_dossier=state.get("escalation_dossier")
    )

    # Update database Task & Memory
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == state["task_id"]).first()
        if task:
            task.status = "escalated" if state.get("requires_escalation") else "completed"
            task.completed_at = datetime.datetime.utcnow()
            task.confidence = state.get("confidence", 0.95)
            task.replan_count = state.get("replan_count", 0)

        # Update customer memory if refund or inquiry occurred
        intent_name = state.get("intent", {}).get("intent")
        if intent_name == "refund_request":
            mem = CustomerMemory(
                customer_id=state.get("customer_id", "CUST1002"),
                memory_type="order_issue",
                key=f"refund_{state['task_id'][:8]}",
                value=f"Processed refund inquiry for order {state.get('intent', {}).get('entities', {}).get('order_id')}."
            )
            db.add(mem)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB Finalize Task Error]: {e}")
    finally:
        db.close()

    add_trace(
        state,
        "Supervisor Agent",
        "Task workflow successfully concluded",
        {"status": "completed"}
    )

    return {
        "final_response": final_text,
        "status": "completed" if not state.get("requires_escalation") else "escalated"
    }

# ----------------- CONDITIONAL ROUTING -----------------

def route_after_intent(state: AgenticSupportState) -> Literal["escalation", "planner"]:
    if state.get("intent", {}).get("intent") == "human_escalation":
        return "escalation"
    return "planner"

def route_after_critic(state: AgenticSupportState) -> Literal["escalation", "replanning", "complete"]:
    rec = state.get("critic_result", {}).get("recommended_action", "complete")
    replan_count = state.get("replan_count", 0)

    if rec == "escalate":
        return "escalation"
    elif rec == "replan" and replan_count < 5:
        return "replanning"
    else:
        return "complete"

# ----------------- BUILD LANGGRAPH -----------------

def build_support_graph():
    builder = StateGraph(AgenticSupportState)

    # Add nodes
    builder.add_node("supervisor_init", supervisor_init_node)
    builder.add_node("intent", intent_node)
    builder.add_node("planner", planner_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("resolution", resolution_node)
    builder.add_node("critic", critic_node)
    builder.add_node("replanning", replanning_node)
    builder.add_node("escalation", escalation_node)
    builder.add_node("complete", complete_node)

    # Set entry point
    builder.set_entry_point("supervisor_init")

    # Transitions
    builder.add_edge("supervisor_init", "intent")

    builder.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "escalation": "escalation",
            "planner": "planner"
        }
    )

    builder.add_edge("planner", "retrieval")
    builder.add_edge("retrieval", "resolution")
    builder.add_edge("resolution", "critic")

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "escalation": "escalation",
            "replanning": "replanning",
            "complete": "complete"
        }
    )

    builder.add_edge("replanning", "resolution")
    builder.add_edge("escalation", "complete")
    builder.add_edge("complete", END)

    return builder.compile()

support_graph = build_support_graph()
