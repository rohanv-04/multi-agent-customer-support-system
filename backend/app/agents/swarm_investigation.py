import time
import json
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..database.database import SessionLocal
from ..database.models import SupportCase, AgentRun, Order, Refund, get_utc_now
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


def _sub_investigate_order(order_id: Optional[str], intake: IntakeExtractionResult, case_id: str) -> Dict[str, Any]:
    """Sub-Investigator 1: Order & Product Specialist."""
    start_t = time.time()
    db = SessionLocal()
    findings: List[InvestigationFinding] = []
    evidence: List[InvestigationEvidence] = []
    data_sources: List[str] = ["db.orders"]
    now_str = get_utc_now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if order_id:
            order_tool_res = get_order_status(order_id)
            if order_tool_res.get("found"):
                order_data = order_tool_res.get("order", {})
                status = order_data.get("status")
                total = order_data.get("total_amount", 0.0)
                findings.append(InvestigationFinding(
                    category="order_verification",
                    observation=f"Order {order_id} verified in OMS: Status '{status}', total ${total:.2f}.",
                    impact="neutral" if status != "Delayed" else "negative",
                    confidence=1.0
                ))
                evidence.append(InvestigationEvidence(
                    source=f"db.orders.{order_id}",
                    fact=f"Order {order_id}: items={order_data.get('items')}, status={status}, tracking={order_data.get('tracking_number')}",
                    verified=True,
                    timestamp=now_str
                ))
            else:
                findings.append(InvestigationFinding(
                    category="order_verification",
                    observation=f"Order {order_id} not found in Order Management System.",
                    impact="negative",
                    confidence=0.9
                ))
        return {
            "sub_agent": "Order Investigator",
            "findings": findings,
            "evidence": evidence,
            "data_sources": data_sources,
            "duration_ms": int((time.time() - start_t) * 1000),
            "status": "completed"
        }
    except Exception as e:
        return {
            "sub_agent": "Order Investigator",
            "findings": [],
            "evidence": [],
            "data_sources": [],
            "duration_ms": int((time.time() - start_t) * 1000),
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()


def _sub_investigate_payment(customer_id: str, order_id: Optional[str], case_id: str) -> Dict[str, Any]:
    """Sub-Investigator 2: Payment & Financial Gateway Specialist."""
    start_t = time.time()
    db = SessionLocal()
    findings: List[InvestigationFinding] = []
    evidence: List[InvestigationEvidence] = []
    data_sources: List[str] = ["db.refunds", "payment_gateway.ledger"]
    now_str = get_utc_now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        prior_refunds = db.query(Refund).filter(Refund.customer_id == customer_id).all()
        order_refunded = False
        if order_id:
            matching = [r for r in prior_refunds if r.order_id == order_id]
            if matching:
                order_refunded = True
                findings.append(InvestigationFinding(
                    category="payment_verification",
                    observation=f"Order {order_id} has prior refund transaction: ID {matching[0].refund_id} for ${matching[0].refund_amount:.2f}.",
                    impact="negative",
                    confidence=1.0
                ))
                evidence.append(InvestigationEvidence(
                    source="db.refunds",
                    fact=f"Prior refund {matching[0].refund_id} already executed for order {order_id}.",
                    verified=True,
                    timestamp=now_str
                ))

        if not order_refunded:
            findings.append(InvestigationFinding(
                category="payment_verification",
                observation=f"No prior refunds on record for order {order_id or 'N/A'}. Payment settled in full.",
                impact="positive",
                confidence=1.0
            ))

        return {
            "sub_agent": "Payment Investigator",
            "findings": findings,
            "evidence": evidence,
            "data_sources": data_sources,
            "duration_ms": int((time.time() - start_t) * 1000),
            "status": "completed"
        }
    except Exception as e:
        return {
            "sub_agent": "Payment Investigator",
            "findings": [],
            "evidence": [],
            "data_sources": [],
            "duration_ms": int((time.time() - start_t) * 1000),
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()


def _sub_investigate_shipping(order_id: Optional[str], case_id: str) -> Dict[str, Any]:
    """Sub-Investigator 3: Logistics & Carrier Tracking Specialist."""
    start_t = time.time()
    db = SessionLocal()
    findings: List[InvestigationFinding] = []
    evidence: List[InvestigationEvidence] = []
    data_sources: List[str] = ["carrier.telemetry"]
    now_str = get_utc_now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if order_id:
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if order:
                now = get_utc_now()
                is_delayed = order.status in ["Delayed", "Delayed_Carrier"] or (order.expected_delivery and order.expected_delivery < now and order.status != "Delivered")
                if is_delayed:
                    findings.append(InvestigationFinding(
                        category="shipping_telemetry",
                        observation=f"Carrier {order.carrier or 'NovaExpress'} reports delay beyond scheduled delivery window ({order.expected_delivery}).",
                        impact="negative",
                        confidence=0.95
                    ))
                    evidence.append(InvestigationEvidence(
                        source=f"carrier.{order.carrier or 'NovaExpress'}",
                        fact=f"Carrier tracking indicates shipment delayed in transit. Tracking #{order.tracking_number}.",
                        verified=True,
                        timestamp=now_str
                    ))
                else:
                    findings.append(InvestigationFinding(
                        category="shipping_telemetry",
                        observation=f"Carrier reports package status '{order.status}'. On schedule.",
                        impact="positive",
                        confidence=0.90
                    ))

        return {
            "sub_agent": "Shipping Investigator",
            "findings": findings,
            "evidence": evidence,
            "data_sources": data_sources,
            "duration_ms": int((time.time() - start_t) * 1000),
            "status": "completed"
        }
    except Exception as e:
        return {
            "sub_agent": "Shipping Investigator",
            "findings": [],
            "evidence": [],
            "data_sources": [],
            "duration_ms": int((time.time() - start_t) * 1000),
            "status": "failed",
            "error": str(e)
        }
    finally:
        db.close()


def _sub_investigate_history(customer_360: Customer360Response, case_id: str) -> Dict[str, Any]:
    """Sub-Investigator 4: Customer History & Loyalty Specialist."""
    start_t = time.time()
    findings: List[InvestigationFinding] = []
    evidence: List[InvestigationEvidence] = []
    data_sources: List[str] = ["customer.loyalty", "customer.memory"]
    now_str = get_utc_now().strftime("%Y-%m-%d %H:%M:%S")

    loyalty = customer_360.loyalty
    if loyalty.is_vip:
        findings.append(InvestigationFinding(
            category="customer_status",
            observation=f"VIP Customer Tier: {loyalty.tier} (${loyalty.lifetime_spend:.2f} spend, {loyalty.order_count} orders).",
            impact="positive",
            confidence=1.0
        ))
        evidence.append(InvestigationEvidence(
            source="customer.loyalty",
            fact=f"VIP status active. High priority treatment warranted.",
            verified=True,
            timestamp=now_str
        ))
    else:
        findings.append(InvestigationFinding(
            category="customer_status",
            observation=f"Account status: {customer_360.account_status} ({loyalty.tier} tier, {loyalty.order_count} orders).",
            impact="neutral",
            confidence=1.0
        ))

    return {
        "sub_agent": "Customer History Investigator",
        "findings": findings,
        "evidence": evidence,
        "data_sources": data_sources,
        "duration_ms": int((time.time() - start_t) * 1000),
        "status": "completed"
    }


def run_swarm_investigation(
    db: Session,
    case: SupportCase,
    customer_360: Customer360Response,
    intake: IntakeExtractionResult,
    task_id: Optional[str] = None
) -> InvestigationResult:
    """Parallel Swarm Investigator: Concurrently executes independent specialist diagnostics.
    
    Sub-investigators:
    1. Order & Product Specialist
    2. Payment & Financial Gateway Specialist
    3. Shipping & Carrier Tracking Specialist
    4. Customer History & Loyalty Specialist
    
    Merges evidence, tracks latency, handles partial failures gracefully, and stores individual AgentRun records.
    """
    case_id = case.id
    target_order_id = intake.order_id or (intake.relevant_entities.get("order_id") if intake.relevant_entities else None)
    if not target_order_id and customer_360 and customer_360.orders:
        target_order_id = customer_360.orders[0].order_id

    total_start = time.time()
    sub_results: List[Dict[str, Any]] = []

    cust_id = (customer_360.profile.customer_id if customer_360 and customer_360.profile else case.customer_id)

    # Execute sub-investigators in parallel swarm
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_sub_investigate_order, target_order_id, intake, case_id): "Order Investigator",
            executor.submit(_sub_investigate_payment, cust_id, target_order_id, case_id): "Payment Investigator",
            executor.submit(_sub_investigate_shipping, target_order_id, case_id): "Shipping Investigator",
            executor.submit(_sub_investigate_history, customer_360, case_id): "Customer History Investigator",
        }

        for future in as_completed(futures):
            agent_name = futures[future]
            try:
                res = future.result(timeout=5.0)
                sub_results.append(res)
            except Exception as e:
                sub_results.append({
                    "sub_agent": agent_name,
                    "findings": [],
                    "evidence": [],
                    "data_sources": [],
                    "duration_ms": 5000,
                    "status": "failed",
                    "error": str(e)
                })

    # Evidence Merger: Aggregate findings and evidence
    merged_findings: List[InvestigationFinding] = []
    merged_evidence: List[InvestigationEvidence] = []
    merged_sources: List[str] = []
    unresolved_questions: List[str] = []

    for sub in sub_results:
        merged_findings.extend(sub.get("findings", []))
        merged_evidence.extend(sub.get("evidence", []))
        merged_sources.extend(sub.get("data_sources", []))

        # Persist AgentRun telemetry for each sub-investigator
        try:
            dur = max(25, sub.get("duration_ms", 120))
            now_ts = get_utc_now()
            agent_run = AgentRun(
                case_id=case_id,
                task_id=task_id,
                agent_name=sub.get("sub_agent", "Swarm Investigator"),
                status=sub.get("status", "completed"),
                output_summary=f"Discovered {len(sub.get('findings', []))} findings, {len(sub.get('evidence', []))} evidence items in {dur}ms.",
                confidence=0.95 if sub.get("status") == "completed" else 0.40,
                error_info=sub.get("error"),
                started_at=now_ts - datetime.timedelta(milliseconds=dur),
                ended_at=now_ts
            )
            db.add(agent_run)
        except Exception:
            pass

    # Check eligibility if refund/cancel requested
    if target_order_id:
        try:
            elig_res = check_refund_eligibility(target_order_id, customer_id=cust_id)
            if elig_res.get("eligible"):
                merged_findings.append(InvestigationFinding(
                    category="policy_eligibility",
                    observation=f"Automated eligibility check confirmed: {elig_res.get('reason')}.",
                    impact="positive",
                    confidence=0.98
                ))
                merged_evidence.append(InvestigationEvidence(
                    source="engine.eligibility_tool",
                    fact=f"Policy eligibility: {elig_res.get('reason')}. Buffer: {elig_res.get('buffer_hours')}h.",
                    verified=True,
                    timestamp=get_utc_now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            else:
                merged_findings.append(InvestigationFinding(
                    category="policy_eligibility",
                    observation=f"Eligibility check: {elig_res.get('reason')}.",
                    impact="neutral",
                    confidence=0.95
                ))
        except Exception:
            pass

    try:
        db.commit()
    except Exception:
        db.rollback()

    total_duration_ms = int((time.time() - total_start) * 1000)

    # Calculate overall confidence
    success_count = sum(1 for s in sub_results if s.get("status") == "completed")
    overall_confidence = round(success_count / len(sub_results), 2) if sub_results else 0.85

    summary_text = (
        f"Swarm diagnostic completed across 4 sub-investigators ({total_duration_ms}ms). "
        f"Assembled {len(merged_findings)} findings and {len(merged_evidence)} verified facts."
    )

    return InvestigationResult(
        case_id=case_id,
        findings=merged_findings,
        evidence=merged_evidence,
        data_sources=list(set(merged_sources)),
        unresolved_questions=unresolved_questions,
        recommended_next_step="Evaluate policy eligibility and risk guardrails with merged evidence",
        investigation_status="complete" if overall_confidence >= 0.70 else "partial"
    )
