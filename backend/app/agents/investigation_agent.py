import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..database.models import SupportCase, get_utc_now
from ..schemas.customer import Customer360Response
from ..schemas.intake import IntakeExtractionResult
from ..schemas.investigation import (
    InvestigationFinding,
    InvestigationEvidence,
    InvestigationResult
)
from ..services.case_service import CaseService
from ..tools.order_tool import get_order_status
from ..tools.eligibility_tool import check_refund_eligibility
from ..rag.vector_store import policy_store


def run_investigation_agent(
    db: Session,
    case: SupportCase,
    customer_360: Customer360Response,
    intake: IntakeExtractionResult,
    task_id: Optional[str] = None
) -> InvestigationResult:
    """Agent: Investigation Agent.

    Conducts a multi-source diagnostic investigation combining SupportCase, Customer 360,
    live database tools, shipping tracking, product knowledge, and policy knowledge to assemble
    verified factual evidence for resolution.
    """
    case_id = case.id
    effective_task_id = task_id or case_id
    now_str = get_utc_now().strftime("%Y-%m-%d %H:%M:%S")

    findings: List[InvestigationFinding] = []
    evidence: List[InvestigationEvidence] = []
    data_sources: List[str] = ["customer.profile", "customer.360"]
    unresolved_questions: List[str] = []

    # 1. Customer Context & VIP Assessment from Customer 360
    loyalty = customer_360.loyalty
    if loyalty.is_vip:
        findings.append(InvestigationFinding(
            category="customer_status",
            observation=f"Customer is a verified {loyalty.tier} VIP with ${loyalty.lifetime_spend:.2f} lifetime spend across {loyalty.order_count} orders.",
            impact="positive",
            confidence=1.0
        ))
        evidence.append(InvestigationEvidence(
            source="customer.loyalty",
            fact=f"VIP status active. Tenure: {loyalty.tenure_days} days. Eligible perks: {', '.join(loyalty.perks[:2])}.",
            verified=True,
            timestamp=now_str
        ))
    else:
        findings.append(InvestigationFinding(
            category="customer_status",
            observation=f"Customer account status: {customer_360.account_status} ({loyalty.tier} tier, {loyalty.order_count} past orders).",
            impact="neutral",
            confidence=0.98
        ))

    # Review past complaints / open escalations
    if customer_360.escalations:
        open_esc = [e for e in customer_360.escalations if e.status == "open"]
        if open_esc:
            data_sources.append("customer.escalations")
            findings.append(InvestigationFinding(
                category="customer_status",
                observation=f"Customer has {len(open_esc)} unresolved escalation ticket(s) on file.",
                impact="risk",
                confidence=0.95
            ))
            evidence.append(InvestigationEvidence(
                source="customer.escalations",
                fact=f"Active ticket #{open_esc[0].ticket_id} ({open_esc[0].priority} priority): {open_esc[0].reason}",
                verified=True,
                timestamp=now_str
            ))

    # 2. Correlate or Detect Order ID & Missing Information
    target_order_id = intake.order_id
    if not target_order_id and customer_360.orders and intake.intent in ["refund_request", "order_status_inquiry", "cancellation_request"]:
        # Only auto-correlate if there is an unambiguously delayed or currently processing order
        delayed_candidates = [o for o in customer_360.orders if o.status in ["Delayed", "Processing"]]
        if delayed_candidates and ("delay" in intake.sub_intent or "delayed" in intake.relevant_entities.get("raw_text", "").lower()):
            target_order_id = delayed_candidates[0].order_id
            findings.append(InvestigationFinding(
                category="order",
                observation=f"No order ID explicitly supplied in prompt; automatically correlated with active delayed order {target_order_id}.",
                impact="neutral",
                confidence=0.88
            ))
            evidence.append(InvestigationEvidence(
                source="customer.orders",
                fact=f"Correlated candidate active order {target_order_id} ({delayed_candidates[0].status}).",
                verified=True,
                timestamp=now_str
            ))

    order_data: Optional[Dict[str, Any]] = None

    if target_order_id:
        data_sources.append("database.orders")
        data_sources.append("carrier.tracking")

        # Query Order Tool & Log AgentAction + CaseEvent
        order_res = get_order_status(order_id=target_order_id)
        order_found = order_res.get("success", False) or order_res.get("found", False)

        CaseService.record_agent_action(
            db=db,
            case_id=case_id,
            agent_name="Investigation Agent",
            action_type="get_order_status",
            task_id=effective_task_id,
            status="completed" if order_found else "failed",
            input_summary=f"Investigate status for order {target_order_id}",
            output_summary=f"Status: {order_res.get('status')}, Carrier: {order_res.get('carrier')}, Tracking: {order_res.get('tracking_number')}",
            input_metadata={"order_id": target_order_id},
            result_metadata=order_res,
            confidence=0.99,
            duration_ms=45
        )

        if order_found:
            order_data = order_res
            is_delayed = order_res.get("status") == "Delayed"
            findings.append(InvestigationFinding(
                category="shipment",
                observation=f"Order {target_order_id} is '{order_res.get('status')}'. Carrier: {order_res.get('carrier')} ({order_res.get('tracking_number')}).",
                impact="risk" if is_delayed else "neutral",
                confidence=0.99
            ))
            if order_res.get("delay_reason"):
                findings.append(InvestigationFinding(
                    category="shipment",
                    observation=f"Carrier transit notice: {order_res.get('delay_reason')}",
                    impact="risk",
                    confidence=0.99
                ))

            item_names = [i.get('name', '') for i in order_res.get('items', [])]
            evidence.append(InvestigationEvidence(
                source="database.orders",
                fact=f"Order {target_order_id}: Total ${order_res.get('total_amount', 0.0):.2f}, Items: {', '.join(item_names)}.",
                verified=True,
                timestamp=now_str
            ))
            evidence.append(InvestigationEvidence(
                source="carrier.tracking",
                fact=f"Tracking {order_res.get('tracking_number')} with {order_res.get('carrier')}: Status is {order_res.get('status')}.",
                verified=True,
                timestamp=now_str
            ))

            # Payment evidence
            order_payments = [p for p in customer_360.payments if p.order_id == target_order_id]
            if order_payments:
                data_sources.append("database.payments")
                evidence.append(InvestigationEvidence(
                    source="database.payments",
                    fact=f"Payment {order_payments[0].payment_id} is verified '{order_payments[0].status.upper()}' for ${order_payments[0].amount:.2f}.",
                    verified=True,
                    timestamp=now_str
                ))
        else:
            findings.append(InvestigationFinding(
                category="order",
                observation=f"Target order {target_order_id} could not be located in business database.",
                impact="blocker",
                confidence=0.99
            ))
            unresolved_questions.append(f"Order ID '{target_order_id}' was not found in records. Customer verification required.")
    else:
        if intake.intent in ["refund_request", "order_status_inquiry", "cancellation_request"]:
            unresolved_questions.append("Specific order identifier is required to proceed with investigation and resolution.")

    # 3. Policy & Eligibility Diagnostic (Knowledge Base & Rules Engine)
    if intake.intent == "refund_request" and target_order_id and order_data and (order_data.get("success") or order_data.get("found")):
        data_sources.append("rag.policies")
        eligibility_res = check_refund_eligibility(order_id=target_order_id, customer_id=case.customer_id)

        CaseService.record_agent_action(
            db=db,
            case_id=case_id,
            agent_name="Investigation Agent",
            action_type="check_refund_eligibility",
            task_id=effective_task_id,
            status="completed",
            input_summary=f"Audit refund policy compliance for order {target_order_id}",
            output_summary=f"Eligible: {eligibility_res.get('eligible')}, Amount: ${eligibility_res.get('refund_amount', 0.0):.2f}. Basis: {eligibility_res.get('policy_basis')}",
            input_metadata={"order_id": target_order_id, "customer_id": case.customer_id},
            result_metadata=eligibility_res,
            confidence=0.98,
            duration_ms=60
        )

        is_eligible = eligibility_res.get("eligible", False)
        findings.append(InvestigationFinding(
            category="policy",
            observation=f"Refund eligibility evaluated: {'APPROVED' if is_eligible else 'REJECTED'}. Basis: {eligibility_res.get('policy_basis')}",
            impact="positive" if is_eligible else "blocker",
            confidence=0.98
        ))
        evidence.append(InvestigationEvidence(
            source="rag.policies",
            fact=f"Policy Evaluation: Eligible={is_eligible}, Authorized Amount=${eligibility_res.get('refund_amount', 0.0):.2f}. Clause: {eligibility_res.get('policy_clause', 'General')}.",
            verified=True,
            timestamp=now_str
        ))
    elif intake.intent == "policy_inquiry":
        data_sources.append("rag.policies")
        query = intake.sub_intent or case.subject or "return refund warranty shipping policy"
        retrieved_docs = policy_store.search(query=query, top_k=2)
        if retrieved_docs:
            top_doc = retrieved_docs[0]
            evidence.append(InvestigationEvidence(
                source="rag.policies",
                fact=f"KB Policy Match: {top_doc.get('title')} ({top_doc.get('section', 'General')})",
                verified=True,
                timestamp=now_str
            ))

    # 4. Formulate Recommendation
    if intake.intent == "human_escalation":
        recommended_next_step = "Route structured investigation evidence dossier to Human Support Desk for immediate agent assignment."
        status_flag = "escalate"
    elif unresolved_questions:
        recommended_next_step = f"Request missing data from customer: {unresolved_questions[0]}"
        status_flag = "needs_customer_input"
    elif intake.intent == "refund_request" and any(f.observation.startswith("Refund eligibility evaluated: APPROVED") for f in findings):
        recommended_next_step = "Authorize and execute financial refund transaction via Action Gateway and issue customer confirmation."
        status_flag = "complete"
    elif intake.intent == "policy_inquiry":
        recommended_next_step = "Synthesize verified policy documentation citations and deliver comprehensive response."
        status_flag = "complete"
    elif intake.intent == "order_status_inquiry" and order_data and (order_data.get("success") or order_data.get("found")):
        recommended_next_step = f"Communicate current delivery status ({order_data.get('status')}) and transit timeline to customer."
        status_flag = "complete"
    else:
        recommended_next_step = "Proceed to planner agent with assembled Customer 360 investigation evidence."
        status_flag = "complete"

    # Log Investigation Summary CaseEvent
    CaseService.record_case_event(
        db=db,
        case_id=case_id,
        event_type="investigation_completed",
        actor="Investigation Agent",
        summary=f"Investigation completed: {len(findings)} findings, {len(evidence)} evidence points across {len(data_sources)} data sources.",
        details={"status": status_flag, "recommendation": recommended_next_step}
    )

    return InvestigationResult(
        case_id=case_id,
        findings=findings,
        evidence=evidence,
        data_sources=data_sources,
        unresolved_questions=unresolved_questions,
        recommended_next_step=recommended_next_step,
        investigation_status=status_flag
    )
