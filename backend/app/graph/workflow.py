import datetime
from typing import Dict, Any, List, Literal, Optional
from langgraph.graph import StateGraph, END
from .state import AgenticSupportState
from ..agents import (
    run_intake_agent,
    run_intent_agent,
    run_investigation_agent,
    run_policy_agent,
    run_decision_engine,
    run_risk_agent,
    run_planner_agent,
    run_retrieval_agent,
    run_resolution_agent,
    run_critic_agent,
    run_escalation_agent,
    format_final_customer_response
)
from ..database.database import SessionLocal
from ..database.models import (
    Task,
    TaskStep,
    AgentAction,
    CustomerMemory,
    EscalationTicket,
    SupportCase,
    get_utc_now
)
from ..services.case_service import CaseService
from ..services.customer_intelligence_service import CustomerIntelligenceService
from ..services.customer_friction_service import CustomerFrictionService
from ..services.case_dna_service import CaseDNAService
from ..agents.swarm_investigation import run_swarm_investigation
from ..agents.conversation_integrity_guard import ConversationIntegrityGuard
from ..schemas.case import (
    CaseCreate,
    CaseStatus,
    CasePriority,
    CaseMessageCreate,
    EventType
)
from ..schemas.intake import IntakeExtractionResult
from ..schemas.customer import Customer360Response
from ..schemas.investigation import InvestigationResult
from ..schemas.policy import PolicyEvaluationResult
from ..schemas.decision import DecisionResult, DecisionType
from ..schemas.risk import RiskEvaluationResult, RiskDecision


def add_trace(state: AgenticSupportState, agent: str, action: str, details: Any = None, status: str = "completed") -> Dict[str, Any]:
    now = get_utc_now()
    trace_event = {
        "timestamp": now.strftime("%H:%M:%S"),
        "iso_time": now.isoformat(),
        "agent": agent,
        "action": action,
        "details": details,
        "status": status
    }
    state["execution_trace"].append(trace_event)
    return trace_event


# ----------------- NODE DEFINITIONS -----------------

def supervisor_init_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Initialize workflow state, task record in SQLite, ensure SupportCase exists, and log trace."""
    now = get_utc_now()
    db = SessionLocal()
    case_id = state.get("case_id")

    try:
        # 1. Maintain backward-compatible Task entity
        existing_task = db.query(Task).filter(Task.task_id == state["task_id"]).first()
        if not existing_task:
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

        # 2. SupportCase Inception & Transition to TRIAGING
        if not case_id:
            case = CaseService.create_case(
                db=db,
                data=CaseCreate(
                    customer_id=state.get("customer_id", "CUST1002"),
                    subject=state["user_goal"][:80],
                    description=state["user_goal"],
                    channel="web_chat",
                    priority="medium",
                    conversation_id=state.get("conversation_id"),
                    initial_message=state["user_goal"]
                )
            )
            case_id = case.id
        else:
            case = CaseService.get_case(db, case_id)

        if case:
            if case.status == CaseStatus.NEW.value:
                CaseService.transition_status(db, case, CaseStatus.TRIAGING.value, actor="Supervisor Agent")
            CaseService.start_agent_run(db, case_id=case_id, agent_name="Supervisor Agent", task_id=state["task_id"])

    except Exception as e:
        db.rollback()
        print(f"[DB Task/Case Init Error]: {e}")
    finally:
        db.close()

    state["case_id"] = case_id
    add_trace(state, "Supervisor Agent", "Task initiated & case workspace created", {"goal": state["user_goal"], "case_id": case_id})
    return {
        "status": "in_progress",
        "iteration_count": state.get("iteration_count", 0) + 1,
        "case_id": case_id
    }


def intent_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 1 — Intake & Intent Agent."""
    history = state.get("messages", [])
    intake_res = run_intake_agent(
        user_goal=state["user_goal"],
        customer_id=state.get("customer_id", "CUST1002"),
        conversation_history=history
    )
    intent_data = run_intent_agent(
        user_goal=state["user_goal"],
        customer_id=state.get("customer_id", "CUST1002"),
        conversation_history=history
    )
    case_id = state.get("case_id")

    if case_id:
        db = SessionLocal()
        try:
            case = CaseService.get_case(db, case_id)
            if case:
                urgency = (intake_res.urgency or "medium").lower()
                priority_map = {"low": "low", "medium": "medium", "high": "high", "urgent": "urgent"}
                case.priority = priority_map.get(urgency, "medium")
                case.intent = intake_res.intent
                case.sentiment = intake_res.sentiment
                db.commit()

                # Transition lifecycle state
                if intake_res.intent == "human_escalation":
                    CaseService.transition_status(
                        db, case, CaseStatus.ESCALATED.value,
                        actor="Intake Agent",
                        reason="Direct human agent requested by customer"
                    )
                else:
                    CaseService.transition_status(
                        db, case, CaseStatus.INVESTIGATING.value,
                        actor="Intake Agent",
                        reason=f"Identified intent: {case.intent}"
                    )

                run = CaseService.start_agent_run(db, case_id, "Intake Agent", task_id=state["task_id"])
                CaseService.complete_agent_run(
                    db, run.id,
                    status="completed",
                    output_summary=f"Intent: {case.intent}, Sub-Intent: {intake_res.sub_intent}, Urgency: {case.priority}",
                    confidence=intake_res.confidence
                )
        except Exception as e:
            db.rollback()
            print(f"[DB Intent Case Error]: {e}")
        finally:
            db.close()

    add_trace(
        state,
        "Intake Agent",
        f"Goal identified: '{intake_res.intent}' ({intake_res.sub_intent or 'standard'})",
        {
            "intent": intake_res.intent,
            "sub_intent": intake_res.sub_intent,
            "entities": intake_res.relevant_entities,
            "urgency": intake_res.urgency,
            "sentiment": intake_res.sentiment,
            "confidence": intake_res.confidence
        }
    )
    return {
        "intent": intent_data,
        "confidence": intake_res.confidence
    }


def investigation_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 2 — Investigation Agent: Ingests SupportCase & Customer 360, queries tools, and collects evidence."""
    case_id = state.get("case_id")
    customer_id = state.get("customer_id", "CUST1002")
    intake_data = state["intent"].get("_intake_model")
    if intake_data:
        intake = IntakeExtractionResult(**intake_data)
    else:
        intake = run_intake_agent(user_goal=state["user_goal"], customer_id=customer_id)

    db = SessionLocal()
    investigation_result_dict = {}
    customer_360_dict = {}

    try:
        customer_360 = CustomerIntelligenceService.get_customer_360(db, customer_id)
        if customer_360:
            customer_360_dict = customer_360.model_dump(mode="json")

        case = CaseService.get_case(db, case_id) if case_id else None
        if not case and case_id:
            case = db.query(SupportCase).filter(SupportCase.id == case_id).first()

        if case and customer_360:
            # SupportOS AI V2: Calculate Case DNA and Customer Friction
            case_dna = CaseDNAService.generate_case_dna(db, case, intake, customer_360)
            friction = CustomerFrictionService.calculate_friction(db, customer_id)

            run = CaseService.start_agent_run(db, case_id, "Swarm Investigation Engine", task_id=state["task_id"])
            inv_res = run_swarm_investigation(
                db=db,
                case=case,
                customer_360=customer_360,
                intake=intake,
                task_id=state["task_id"]
            )
            investigation_result_dict = inv_res.model_dump(mode="json")
            CaseService.complete_agent_run(
                db, run.id,
                status="completed",
                output_summary=f"Swarm diagnostic assembled {len(inv_res.findings)} findings & {len(inv_res.evidence)} verified facts across {len(inv_res.data_sources)} data sources",
                confidence=0.98
            )

            add_trace(
                state,
                "Investigation Agent",
                f"Completed parallel swarm diagnostics ({len(inv_res.findings)} findings, {len(inv_res.evidence)} facts)",
                {
                    "findings_count": len(inv_res.findings),
                    "evidence_count": len(inv_res.evidence),
                    "data_sources": inv_res.data_sources
                }
            )
    except Exception as e:
        print(f"[DB Investigation Error]: {e}")
    finally:
        db.close()

    return {
        "customer_360": customer_360_dict,
        "investigation_result": investigation_result_dict
    }


def policy_intelligence_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 3 — Policy Intelligence Agent: Evaluates conditions, exceptions, and evidence citations."""
    case_id = state.get("case_id")
    customer_id = state.get("customer_id", "CUST1002")

    intake_data = state["intent"].get("_intake_model")
    intake = IntakeExtractionResult(**intake_data) if intake_data else run_intake_agent(state["user_goal"], customer_id)
    c360_data = state.get("customer_360")
    c360 = Customer360Response(**c360_data) if c360_data else None
    inv_data = state.get("investigation_result")
    inv = InvestigationResult(**inv_data) if inv_data else None

    policy_res = run_policy_agent(
        intent_data=intake,
        customer_360=c360,
        investigation=inv
    )

    if case_id:
        db = SessionLocal()
        try:
            run = CaseService.start_agent_run(db, case_id, "Policy Intelligence Agent", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed" if not policy_res.requires_human_review else "completed_with_review_flag",
                output_summary=f"Policy: {policy_res.policy_name} | Eligible: {policy_res.eligibility} | Human Review Required: {policy_res.requires_human_review}",
                confidence=policy_res.confidence
            )
        except Exception as e:
            print(f"[DB Policy Run Error]: {e}")
        finally:
            db.close()

    add_trace(
        state,
        "Policy Intelligence Agent",
        f"Evaluated policy '{policy_res.policy_name}': Eligible={policy_res.eligibility}",
        {
            "conditions_count": len(policy_res.conditions),
            "exceptions_count": len(policy_res.exceptions),
            "requires_human_review": policy_res.requires_human_review,
            "confidence": policy_res.confidence
        }
    )

    return {
        "policy_evaluation": policy_res.model_dump(mode="json"),
        "confidence": min(state["confidence"], policy_res.confidence)
    }


def decision_engine_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 4 — Decision Engine: Decouples WHAT SHOULD HAPPEN from execution."""
    case_id = state.get("case_id")
    customer_id = state.get("customer_id", "CUST1002")

    intake_data = state["intent"].get("_intake_model")
    intake = IntakeExtractionResult(**intake_data) if intake_data else run_intake_agent(state["user_goal"], customer_id)
    c360_data = state.get("customer_360")
    c360 = Customer360Response(**c360_data) if c360_data else None
    inv_data = state.get("investigation_result")
    inv = InvestigationResult(**inv_data) if inv_data else None
    pol_data = state.get("policy_evaluation")
    pol = PolicyEvaluationResult(**pol_data) if pol_data else None

    decision_res = run_decision_engine(
        intake=intake,
        customer_360=c360,
        investigation=inv,
        policy_evaluation=pol
    )

    if case_id:
        db = SessionLocal()
        try:
            case = CaseService.get_case(db, case_id)
            if case and case.status == CaseStatus.INVESTIGATING.value:
                CaseService.transition_status(db, case, CaseStatus.DECISION_PENDING.value, actor="Decision Engine")

            run = CaseService.start_agent_run(db, case_id, "Decision Engine", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed",
                output_summary=f"Decision: {decision_res.decision_type.value.upper()} | Action: {decision_res.recommended_action_name}",
                confidence=decision_res.confidence
            )
        except Exception as e:
            print(f"[DB Decision Run Error]: {e}")
        finally:
            db.close()

    add_trace(
        state,
        "Decision Engine",
        f"Determination synthesized: {decision_res.decision_type.value.upper()}",
        {
            "action": decision_res.recommended_action_name,
            "parameters": decision_res.parameters,
            "rationale": decision_res.rationale
        }
    )

    return {
        "decision_result": decision_res.model_dump(mode="json")
    }


def risk_engine_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 5 — Risk & Compliance Agent: 9-factor evaluation for AUTO_APPROVE, HUMAN_REVIEW, or BLOCK."""
    case_id = state.get("case_id")
    customer_id = state.get("customer_id", "CUST1002")

    dec_data = state.get("decision_result")
    decision = DecisionResult(**dec_data) if dec_data else None
    c360_data = state.get("customer_360")
    c360 = Customer360Response(**c360_data) if c360_data else None
    pol_data = state.get("policy_evaluation")
    pol = PolicyEvaluationResult(**pol_data) if pol_data else None
    inv_data = state.get("investigation_result")
    inv = InvestigationResult(**inv_data) if inv_data else None

    db = SessionLocal()
    try:
        risk_res = run_risk_agent(
            db=db,
            decision=decision,
            customer_360=c360,
            policy_evaluation=pol,
            investigation=inv
        )

        if case_id:
            case = CaseService.get_case(db, case_id)
            if case:
                if risk_res.decision == RiskDecision.AUTO_APPROVE:
                    if case.status == CaseStatus.DECISION_PENDING.value:
                        CaseService.transition_status(db, case, CaseStatus.ACTION_PENDING.value, actor="Risk Engine", reason="Risk audited: AUTO_APPROVE")
                elif risk_res.decision in [RiskDecision.HUMAN_REVIEW, RiskDecision.BLOCK]:
                    if case.status in [CaseStatus.DECISION_PENDING.value, CaseStatus.INVESTIGATING.value]:
                        CaseService.transition_status(db, case, CaseStatus.HUMAN_REVIEW.value, actor="Risk Engine", reason=f"Risk audited: {risk_res.decision.value} ({risk_res.required_approval})")

            run = CaseService.start_agent_run(db, case_id, "Risk & Compliance Agent", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed",
                output_summary=f"Risk Level: {risk_res.risk_level.value} | Decision: {risk_res.decision.value} | Approval: {risk_res.required_approval}",
                confidence=risk_res.confidence
            )
    finally:
        db.close()

    add_trace(
        state,
        "Risk & Compliance Agent",
        f"Compliance Audit: {risk_res.decision.value} (Risk Level: {risk_res.risk_level.value})",
        {
            "decision": risk_res.decision.value,
            "risk_level": risk_res.risk_level.value,
            "required_approval": risk_res.required_approval,
            "factors_count": len(risk_res.factors),
            "reasons": risk_res.reasons
        }
    )

    return {
        "risk_evaluation": risk_res.model_dump(mode="json")
    }


def planner_node(state: AgenticSupportState) -> Dict[str, Any]:
    """Agent 6 — Dynamic Planning."""
    plan_data = run_planner_agent(
        user_goal=state["user_goal"],
        intent_data=state["intent"]
    )
    steps = plan_data.get("steps", [])
    case_id = state.get("case_id")

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

        if case_id:
            run = CaseService.start_agent_run(db, case_id, "Planning Agent", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed",
                output_summary=f"Execution plan created ({len(steps)} steps)",
                confidence=plan_data.get("confidence", 0.93)
            )
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
    """Agent 7 — Knowledge Retrieval (RAG)."""
    intent_str = state["intent"].get("intent", "")
    query = state["user_goal"]
    if "refund" in intent_str:
        query = f"refund policy delayed shipping {state['user_goal']}"
    elif "status" in intent_str:
        query = "shipping transit delivery times tracking"

    rag_result = run_retrieval_agent(query=query, top_k=2)
    state["retrieved_docs"].append(rag_result)

    case_id = state.get("case_id")
    if case_id:
        db = SessionLocal()
        try:
            citations_str = ", ".join([f"{c['category']}" for c in rag_result.get("citations", [])])
            run = CaseService.start_agent_run(db, case_id, "Knowledge Retrieval Agent", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed",
                output_summary=f"Retrieved policy citations: {citations_str}",
                confidence=rag_result.get("confidence", 0.90)
            )
        except Exception as e:
            print(f"[DB RAG Run Error]: {e}")
        finally:
            db.close()

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
    """Agent 8 — Resolution / Action Gateway Agent. Executes subtasks & tools."""
    pending = list(state.get("pending_steps", []))
    completed = list(state.get("completed_steps", []))
    observations = list(state.get("observations", []))
    tool_calls = list(state.get("tool_calls", []))
    case_id = state.get("case_id")

    order_data = {}
    eligibility_data = {}

    if case_id:
        db = SessionLocal()
        try:
            case = CaseService.get_case(db, case_id)
            if case and case.status in [CaseStatus.INVESTIGATING.value, CaseStatus.DECISION_PENDING.value]:
                CaseService.transition_status(db, case, CaseStatus.ACTION_PENDING.value, actor="Resolution Agent")
        except Exception as e:
            print(f"[DB Case Action Status Error]: {e}")
        finally:
            db.close()

    # Execute all actionable pending steps
    while pending:
        step = pending.pop(0)
        res = run_resolution_agent(
            current_step=step,
            task_id=state["task_id"],
            intent_data=state["intent"],
            order_data=order_data,
            eligibility_data=eligibility_data,
            policy_context=state["retrieved_docs"][-1]["context"] if state.get("retrieved_docs") else "",
            case_id=case_id,
            risk_evaluation=state.get("risk_evaluation")
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

            if case_id:
                db = SessionLocal()
                try:
                    CaseService.record_agent_action(
                        db=db,
                        case_id=case_id,
                        agent_name="Resolution Agent",
                        action_type=res["tool_used"],
                        task_id=state["task_id"],
                        status="completed" if res["success"] else "failed",
                        input_summary=step,
                        output_summary=res["observation"],
                        result_metadata=res.get("tool_output") if isinstance(res.get("tool_output"), dict) else {"output": str(res.get("tool_output"))},
                        confidence=1.0,
                        duration_ms=res.get("duration_ms", 120)
                    )
                except Exception as e:
                    print(f"[DB Record Agent Action Error]: {e}")
                finally:
                    db.close()

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
    """Agent 9 — Critic / Validation Agent."""
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
    case_id = state.get("case_id")

    if case_id:
        db = SessionLocal()
        try:
            case = CaseService.get_case(db, case_id)
            if case and case.status in [CaseStatus.ACTION_PENDING.value, CaseStatus.INVESTIGATING.value]:
                CaseService.transition_status(db, case, CaseStatus.VERIFYING.value, actor="Critic Agent")
            run = CaseService.start_agent_run(db, case_id, "Critic / Validator Agent", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed" if critic_res.get("valid") else "failed",
                output_summary=critic_res.get("audit_summary"),
                confidence=critic_res.get("confidence", 0.95),
                error_info="; ".join(critic_res.get("issues", [])) if critic_res.get("issues") else None
            )
        except Exception as e:
            print(f"[DB Critic Case Error]: {e}")
        finally:
            db.close()

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
    case_id = state.get("case_id")

    if case_id:
        db = SessionLocal()
        try:
            CaseService.record_case_event(
                db=db,
                case_id=case_id,
                event_type=EventType.FAILURE.value,
                actor="Critic Agent",
                summary=f"Re-planning loop triggered (Iteration {current_replan}/5)",
                details={"reason": state["critic_result"].get("issues")}
            )
        except Exception as e:
            print(f"[DB Replan Case Event Error]: {e}")
        finally:
            db.close()

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
    """Agent 10 — Escalation Agent."""
    reason = "Customer requested human support"
    if state.get("risk_evaluation") and state["risk_evaluation"].get("reasons"):
        reason = "; ".join(state["risk_evaluation"]["reasons"])
    elif state.get("critic_result") and state["critic_result"].get("issues"):
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
    case_id = state.get("case_id")

    if case_id:
        db = SessionLocal()
        try:
            case = CaseService.get_case(db, case_id)
            if case and case.status not in [CaseStatus.ESCALATED.value, CaseStatus.HUMAN_REVIEW.value]:
                target_st = CaseStatus.HUMAN_REVIEW.value if state.get("risk_evaluation", {}).get("decision") == "HUMAN_REVIEW" else CaseStatus.ESCALATED.value
                CaseService.transition_status(db, case, target_st, actor="Escalation Agent", reason=reason)

            # Link escalation ticket to case_id
            esc = db.query(EscalationTicket).filter(EscalationTicket.ticket_id == dossier["ticket_id"]).first()
            if esc:
                esc.case_id = case_id
                db.commit()

            run = CaseService.start_agent_run(db, case_id, "Escalation Agent", task_id=state["task_id"])
            CaseService.complete_agent_run(
                db, run.id,
                status="completed",
                output_summary=f"Escalation ticket #{dossier['ticket_id']} assigned to Human Desk",
                confidence=1.0
            )
        except Exception as e:
            print(f"[DB Escalation Case Link Error]: {e}")
        finally:
            db.close()

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
    """Synthesize final customer response, record memory, and mark task/case completed."""
    final_text = format_final_customer_response(
        intent_data=state.get("intent", {}),
        observations=state.get("observations", []),
        tool_calls=state.get("tool_calls", []),
        rag_data=state["retrieved_docs"][-1] if state.get("retrieved_docs") else None,
        escalation_dossier=state.get("escalation_dossier")
    )
    case_id = state.get("case_id")

    # SupportOS AI V2: Conversation Integrity Guard validation
    db_guard = SessionLocal()
    try:
        case_obj = db_guard.query(SupportCase).filter(SupportCase.id == case_id).first() if case_id else None
        integrity_check = ConversationIntegrityGuard.audit_and_verify(
            db=db_guard,
            draft_response=final_text,
            case=case_obj,
            action_executed={"status": "completed"} if not state.get("requires_escalation") else None
        )
        if not integrity_check.is_approved and integrity_check.revised_content:
            final_text = integrity_check.revised_content
    finally:
        db_guard.close()

    # Update database Task & Memory
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == state["task_id"]).first()
        if task:
            task.status = "escalated" if state.get("requires_escalation") else "completed"
            task.completed_at = get_utc_now()
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

        # Update SupportCase lifecycle and append final response message
        if case_id:
            case = CaseService.get_case(db, case_id)
            if case:
                if not state.get("requires_escalation") and case.status not in [CaseStatus.RESOLVED.value, CaseStatus.HUMAN_REVIEW.value]:
                    CaseService.transition_status(
                        db, case, CaseStatus.RESOLVED.value,
                        actor="Supervisor Agent",
                        reason="Autonomous workflow concluded successfully"
                    )

                # Add final outbound message
                CaseService.add_case_message(
                    db=db,
                    case_id=case_id,
                    msg_data=CaseMessageCreate(
                        body=final_text,
                        direction="outbound",
                        channel=case.channel,
                        sender_type="agent",
                        sender_id="Supervisor Agent"
                    )
                )
    except Exception as e:
        db.rollback()
        print(f"[DB Finalize Task/Case Error]: {e}")
    finally:
        db.close()

    add_trace(
        state,
        "Supervisor Agent",
        "Task workflow successfully concluded",
        {"status": "completed" if not state.get("requires_escalation") else "escalated"}
    )

    return {
        "final_response": final_text,
        "status": "completed" if not state.get("requires_escalation") else "escalated",
        "case_id": case_id
    }


# ----------------- CONDITIONAL ROUTING -----------------

def route_after_intent(state: AgenticSupportState) -> Literal["escalation", "investigation"]:
    if state.get("intent", {}).get("intent") == "human_escalation":
        return "escalation"
    return "investigation"


def route_after_risk(state: AgenticSupportState) -> Literal["escalation", "planner"]:
    risk_data = state.get("risk_evaluation", {})
    decision = risk_data.get("decision", "AUTO_APPROVE")
    pol_data = state.get("policy_evaluation", {})

    if decision in ["BLOCK", "HUMAN_REVIEW"] or pol_data.get("requires_human_review"):
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
    builder.add_node("investigation", investigation_node)
    builder.add_node("policy_intelligence", policy_intelligence_node)
    builder.add_node("decision_engine", decision_engine_node)
    builder.add_node("risk_engine", risk_engine_node)
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
            "investigation": "investigation"
        }
    )

    builder.add_edge("investigation", "policy_intelligence")
    builder.add_edge("policy_intelligence", "decision_engine")
    builder.add_edge("decision_engine", "risk_engine")

    builder.add_conditional_edges(
        "risk_engine",
        route_after_risk,
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
