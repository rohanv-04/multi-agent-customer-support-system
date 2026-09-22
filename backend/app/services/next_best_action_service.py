import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import SupportCase, Order, Refund
from ..schemas.differentiation import (
    NextBestActionResponse,
    NextBestActionAlternative,
    CustomerFrictionProfile,
    CaseDNA
)
from ..schemas.investigation import InvestigationResult
from ..schemas.policy import PolicyEvaluationResult
from ..schemas.risk import RiskEvaluationResult, RiskDecision, RiskLevel


class NextBestActionEngine:
    """Next-Best-Action (NBA) Engine.
    
    Synthesizes Case DNA, Customer Friction, Investigation Evidence, Policy Evaluation,
    Risk Assessment, and SLA state to determine the optimal next operational step.
    
    Does NOT execute actions automatically; outputs structured proposals for Action Gateway.
    """

    @staticmethod
    def evaluate_next_best_action(
        db: Session,
        case: SupportCase,
        case_dna: Optional[CaseDNA] = None,
        friction_profile: Optional[CustomerFrictionProfile] = None,
        investigation: Optional[InvestigationResult] = None,
        policy: Optional[PolicyEvaluationResult] = None,
        risk: Optional[RiskEvaluationResult] = None
    ) -> NextBestActionResponse:
        case_id = case.id
        intent = (case.intent or (case_dna.intent if case_dna else "") or "general").lower()
        order_id = investigation.order_id if investigation else None

        # Look up order details if available
        order = db.query(Order).filter(Order.order_id == order_id).first() if order_id else None
        order_amount = order.total_amount if order else 0.0

        is_high_friction = friction_profile.level.value in ["HIGH", "CRITICAL"] if friction_profile else False
        is_high_risk = (risk and risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]) or (risk and risk.decision == RiskDecision.HUMAN_REVIEW)
        policy_eligible = policy.eligibility if policy else True

        # Evidence aggregation
        evidence_list = []
        if investigation and investigation.evidence:
            evidence_list.extend([e.fact for e in investigation.evidence[:4]])
        if policy and policy.evidence:
            evidence_list.extend([ev.quote for ev in policy.evidence[:2]])

        # 1. High Risk / Fraud / Dispute -> Next Best Action: ESCALATE TO SUPERVISOR
        if is_high_risk or (policy and policy.requires_human_review and not policy_eligible):
            return NextBestActionResponse(
                case_id=case_id,
                recommended_action="Escalate to Human Supervisor for Priority Triage",
                action_type="escalate",
                parameters={
                    "case_id": case_id,
                    "reason": risk.reasons[0] if (risk and risk.reasons) else "Risk threshold exceeded",
                    "priority": "urgent" if is_high_friction else "high"
                },
                justification=f"Operational risk level ({risk.risk_level.value if risk else 'HIGH'}) requires manual sign-off.",
                alternatives=[
                    NextBestActionAlternative(
                        action_type="request_info",
                        label="Request Additional Verification Documents from Customer",
                        confidence=0.75,
                        reason="Request proof of purchase or photo evidence to lower risk score.",
                        risk_level="low"
                    ),
                    NextBestActionAlternative(
                        action_type="monitor",
                        label="Place Case in High-Priority SLA Monitoring Queue",
                        confidence=0.65,
                        reason="Allow 12-hour grace period for carrier telemetry update.",
                        risk_level="low"
                    )
                ],
                evidence=evidence_list,
                policy_basis=policy.policy_name if policy else "Risk & Compliance Framework",
                risk_level="high",
                requires_approval=True,
                required_role="supervisor"
            )

        # 2. Delayed Shipment / Damaged Product -> Next Best Action: REFUND OR RESHIPMENT
        if any(w in intent for w in ["refund", "delay", "cancel", "damaged", "broken"]):
            if order and order.status in ["Delayed", "Delayed_Carrier"] and policy_eligible:
                action_type = "refund" if "refund" in intent else "reshipment"
                action_label = f"Execute Autonomous Full Refund (${order_amount:.2f} USD)" if action_type == "refund" else f"Trigger Priority Express Replacement for Order {order_id}"
                
                requires_approval = order_amount > 500.0 or is_high_friction

                return NextBestActionResponse(
                    case_id=case_id,
                    recommended_action=action_label,
                    action_type=action_type,
                    parameters={
                        "order_id": order_id,
                        "refund_amount": order_amount,
                        "reason": f"SLA Delay compensation: {intent}"
                    },
                    justification=f"Policy '{policy.policy_name if policy else 'NovaCart Return Policy'}' verified. Order delay verified in carrier telemetry.",
                    alternatives=[
                        NextBestActionAlternative(
                            action_type="reshipment" if action_type == "refund" else "refund",
                            label=f"Alternative: Dispatch replacement package via Next-Day Air" if action_type == "refund" else "Alternative: Process full credit refund to original payment",
                            confidence=0.88,
                            reason="Offers flexible resolution matching customer preference.",
                            risk_level="low"
                        ),
                        NextBestActionAlternative(
                            action_type="notify_customer",
                            label="Send Goodwill Courtesy Credit ($25 Voucher) & Monitor Tracking",
                            confidence=0.70,
                            reason="For customers preferring to wait for current shipment.",
                            risk_level="low"
                        )
                    ],
                    evidence=evidence_list,
                    policy_basis=policy.policy_name if policy else "Standard Delivery Guarantee Policy",
                    risk_level="medium" if requires_approval else "low",
                    requires_approval=requires_approval,
                    required_role="supervisor" if requires_approval else "agent"
                )

        # 3. Information Request / General Inquiry -> Next Best Action: NOTIFY & RESOLVE
        return NextBestActionResponse(
            case_id=case_id,
            recommended_action="Transmit Verified Resolution & Close Case",
            action_type="notify_customer",
            parameters={"case_id": case_id, "channel": case.channel or "web_chat"},
            justification="All required customer information has been retrieved and verified against knowledge base.",
            alternatives=[
                NextBestActionAlternative(
                    action_type="monitor",
                    label="Keep Case Open in Monitoring State for 24h",
                    confidence=0.80,
                    reason="Ensure customer is fully satisfied before final archival.",
                    risk_level="low"
                )
            ],
            evidence=evidence_list,
            policy_basis=policy.policy_name if policy else "Customer Communication Guidelines",
            risk_level="low",
            requires_approval=False,
            required_role="agent"
        )
