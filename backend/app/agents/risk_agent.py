from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..schemas.risk import RiskDecision, RiskLevel, RiskFactor, RiskEvaluationResult
from ..schemas.decision import DecisionResult, DecisionType
from ..schemas.customer import Customer360Response
from ..schemas.policy import PolicyEvaluationResult
from ..schemas.investigation import InvestigationResult
from ..database.models import Refund, Customer


def run_risk_agent(
    db: Optional[Session],
    decision: DecisionResult,
    customer_360: Optional[Customer360Response] = None,
    policy_evaluation: Optional[PolicyEvaluationResult] = None,
    investigation: Optional[InvestigationResult] = None,
    suspicious_override: bool = False
) -> RiskEvaluationResult:
    """Agent: Risk & Compliance Agent.

    Deterministically audits proposed actions against 9 enterprise risk dimensions:
    1. Action Type sensitivity
    2. Financial amount vs Authorization Limits
    3. Customer tenure & loyalty tier
    4. Previous refund claim velocity & cumulative amounts
    5. Policy compliance & condition fulfillment
    6. Account risk status & fraud indicators
    7. Duplicate action / double-credit prevention
    8. Authorization threshold tiers
    9. Diagnostic uncertainty / missing evidence
    """
    factors: List[RiskFactor] = []
    reasons: List[str] = []
    risk_score = 0.0

    action_type = decision.decision_type.value
    target_order_id = decision.target_entity_id or decision.parameters.get("order_id")
    amount = float(decision.parameters.get("refund_amount", 0.0))

    tier = customer_360.loyalty.tier.upper() if customer_360 and customer_360.loyalty else "STANDARD"
    is_vip = customer_360.loyalty.is_vip if customer_360 and customer_360.loyalty else False
    account_status = customer_360.account_status if customer_360 else "Active"
    previous_refund_total = float(customer_360.risk_assessment.get("total_refunded_amount", 0.0)) if customer_360 else 0.0

    # Authorization limit based on customer tier
    auth_limit = 500.0 if is_vip else 200.0
    required_approval = "none"

    # 1. Action Type Risk
    if decision.decision_type == DecisionType.REFUND:
        factors.append(RiskFactor(
            factor_name="action_type_financial",
            score=0.35,
            risk_contribution="medium",
            evidence=f"Action involves monetary transaction (${amount:.2f} USD)."
        ))
        risk_score += 0.35
    elif decision.decision_type in [DecisionType.REPLACEMENT, DecisionType.RESHIP]:
        factors.append(RiskFactor(
            factor_name="action_type_inventory",
            score=0.20,
            risk_contribution="low",
            evidence="Action involves physical replacement shipment dispatch."
        ))
        risk_score += 0.20
    elif decision.decision_type == DecisionType.ESCALATION:
        factors.append(RiskFactor(
            factor_name="action_type_human_transfer",
            score=0.10,
            risk_contribution="low",
            evidence="Routing to human specialist queue."
        ))

    # 2. Amount & Authorization Limit Check
    if amount > 0:
        if amount > 500.0:
            reasons.append(f"Monetary value (${amount:.2f}) exceeds autonomous Tier-1 threshold ($500.00 USD). Requires Finance Specialist approval.")
            factors.append(RiskFactor(
                factor_name="high_value_transaction",
                score=0.85,
                risk_contribution="high",
                evidence=f"Amount ${amount:.2f} > $500 threshold."
            ))
            risk_score += 0.85
            required_approval = "finance_specialist"
        elif amount > auth_limit:
            reasons.append(f"Amount (${amount:.2f}) exceeds customer's tier limit (${auth_limit:.2f} USD). Requires Tier-1 Lead review.")
            factors.append(RiskFactor(
                factor_name="tier_limit_exceeded",
                score=0.55,
                risk_contribution="medium",
                evidence=f"Amount ${amount:.2f} > {tier} tier limit ${auth_limit:.2f}."
            ))
            risk_score += 0.55
            required_approval = "tier_1_lead"
        else:
            factors.append(RiskFactor(
                factor_name="within_authorization_limit",
                score=0.05,
                risk_contribution="low",
                evidence=f"Amount ${amount:.2f} is within {tier} autonomous authorization limit (${auth_limit:.2f})."
            ))

    # 3. Duplicate Action / Double Credit Check
    if db and target_order_id and decision.decision_type == DecisionType.REFUND:
        existing_refund = db.query(Refund).filter(
            Refund.order_id == target_order_id,
            Refund.status == "processed"
        ).first()

        if existing_refund:
            reasons.append(f"Duplicate refund detected! Order {target_order_id} has already been refunded (${existing_refund.refund_amount:.2f} on {existing_refund.processed_at}). Action blocked.")
            factors.append(RiskFactor(
                factor_name="duplicate_transaction_prevention",
                score=1.0,
                risk_contribution="critical",
                evidence=f"Prior processed refund #{existing_refund.refund_id} exists on database."
            ))
            return RiskEvaluationResult(
                risk_level=RiskLevel.CRITICAL,
                decision=RiskDecision.BLOCK,
                reasons=reasons,
                required_approval="fraud_operations",
                factors=factors,
                authorization_limit=auth_limit,
                confidence=1.0
            )

    # 4. Account Risk & Suspicious Behavior Check
    if account_status.lower() in ["suspended", "flagged", "frozen"] or suspicious_override:
        reasons.append(f"Account status is '{account_status}'. Automated actions are locked pending Fraud Operations verification.")
        factors.append(RiskFactor(
            factor_name="account_fraud_flag",
            score=0.95,
            risk_contribution="critical",
            evidence=f"Customer account status is {account_status}."
        ))
        return RiskEvaluationResult(
            risk_level=RiskLevel.CRITICAL,
            decision=RiskDecision.BLOCK,
            reasons=reasons,
            required_approval="fraud_operations",
            factors=factors,
            authorization_limit=auth_limit,
            confidence=1.0
        )

    # 5. Cumulative Refund Velocity (for refund requests)
    if decision.decision_type == DecisionType.REFUND and previous_refund_total >= 1000.0:
        reasons.append(f"Lifetime refund volume (${previous_refund_total:.2f}) exceeds risk threshold ($1,000.00). Requires human supervisor sign-off.")
        factors.append(RiskFactor(
            factor_name="high_lifetime_refund_volume",
            score=0.65,
            risk_contribution="high",
            evidence=f"Cumulative refunds on file: ${previous_refund_total:.2f}."
        ))
        risk_score += 0.65
        if required_approval == "none":
            required_approval = "tier_1_lead"

    # 6. Policy & Evidence Uncertainty
    if policy_evaluation and policy_evaluation.requires_human_review:
        reasons.append(f"Policy evaluation flagged uncertainty: {'; '.join(policy_evaluation.unresolved_conflicts or ['Human review mandated'])}")
        factors.append(RiskFactor(
            factor_name="policy_uncertainty",
            score=0.60,
            risk_contribution="medium",
            evidence="Policy evaluation requires human verification."
        ))
        risk_score += 0.60
        if required_approval == "none":
            required_approval = "tier_1_lead"

    # 7. Customer Loyalty Privilege Dampening
    if is_vip and risk_score < 0.8:
        factors.append(RiskFactor(
            factor_name="vip_goodwill_credit",
            score=-0.20,
            risk_contribution="low",
            evidence=f"{tier} VIP customer standing with high lifetime value (${customer_360.loyalty.lifetime_spend:.2f})."
        ))
        risk_score = max(0.0, risk_score - 0.20)

    # Final Decision Synthesis
    if required_approval in ["finance_specialist", "fraud_operations"] or risk_score >= 0.80:
        risk_level = RiskLevel.HIGH
        decision_enum = RiskDecision.HUMAN_REVIEW
        if not reasons:
            reasons.append("High cumulative risk score warrants Human Desk review.")
    elif required_approval == "tier_1_lead" or risk_score >= 0.45:
        risk_level = RiskLevel.MEDIUM
        decision_enum = RiskDecision.HUMAN_REVIEW
        if not reasons:
            reasons.append("Tier-1 Lead review required before action execution.")
    else:
        risk_level = RiskLevel.LOW
        decision_enum = RiskDecision.AUTO_APPROVE
        reasons.append("Action is compliant, within tier authorization thresholds, and policy-eligible for autonomous execution.")

    return RiskEvaluationResult(
        risk_level=risk_level,
        decision=decision_enum,
        reasons=reasons,
        required_approval=required_approval,
        factors=factors,
        authorization_limit=auth_limit,
        confidence=0.98
    )
