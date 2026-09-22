import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import AgentConflict, SupportCase, get_utc_now
from ..schemas.differentiation import (
    AgentPosition,
    AgentDebateRecord
)
from ..schemas.investigation import InvestigationResult
from ..schemas.policy import PolicyEvaluationResult
from ..schemas.risk import RiskEvaluationResult, RiskDecision, RiskLevel
from ..schemas.decision import DecisionResult, DecisionType


class AgentDebateEngine:
    """Agent Debate & Structured Conflict Resolution Engine.
    
    When specialized agents reach conflicting conclusions on high-stakes or edge-case requests:
    1. Gathers structured positions (conclusion, evidence, confidence, concerns, recommended action).
    2. Identifies concrete points of friction/disagreement.
    3. The Decision Agent arbitrates based on hierarchy of invariants (Security/Risk > Policy > Operational Speed).
    4. Persists debate record and resolution rationale in the case timeline.
    
    Strict Invariant: No uncontrolled conversational loops. Strictly structured position matrix.
    """

    @staticmethod
    def evaluate_and_resolve_conflict(
        db: Session,
        case: SupportCase,
        investigation: Optional[InvestigationResult] = None,
        policy: Optional[PolicyEvaluationResult] = None,
        risk: Optional[RiskEvaluationResult] = None,
        decision: Optional[DecisionResult] = None
    ) -> Optional[AgentDebateRecord]:
        case_id = case.id
        now = get_utc_now()

        positions: Dict[str, AgentPosition] = {}
        conflicting_points: List[str] = []

        # 1. Investigation Agent Position
        if investigation:
            inv_eligible = any(f.category == "policy_eligibility" and f.impact == "positive" for f in investigation.findings)
            positions["investigation_agent"] = AgentPosition(
                agent_name="Investigation Agent",
                conclusion="Customer qualifies for delayed shipment resolution under verified OMS & carrier telemetry." if inv_eligible else "Order telemetry verified in database.",
                evidence=[e.fact for e in investigation.evidence[:3]],
                confidence=investigation.overall_confidence,
                concerns=["Carrier telemetry might experience transit lag."] if not inv_eligible else [],
                recommended_action="Execute refund or dispatch replacement" if inv_eligible else "Request carrier status refresh"
            )

        # 2. Policy Agent Position
        if policy:
            positions["policy_agent"] = AgentPosition(
                agent_name="Policy Agent",
                conclusion=f"Evaluated policy '{policy.policy_name}'. Eligibility={policy.eligibility}, RequiresReview={policy.requires_human_review}.",
                evidence=[e.quote for e in policy.evidence[:2]],
                confidence=policy.confidence,
                concerns=policy.unresolved_conflicts if policy.unresolved_conflicts else [],
                recommended_action="Approve standard resolution" if (policy.eligibility and not policy.requires_human_review) else "Route to Human Review"
            )

        # 3. Risk Agent Position
        if risk:
            is_high = risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            positions["risk_agent"] = AgentPosition(
                agent_name="Risk Guardrails Agent",
                conclusion=f"Risk Level evaluated as {risk.risk_level.value}. Confidence {risk.confidence:.2f}.",
                evidence=risk.reasons[:3],
                confidence=risk.confidence,
                concerns=[f"Threshold breach: {r}" for r in risk.reasons if "exceed" in r.lower()],
                recommended_action="Block autonomous execution & mandate supervisor review" if is_high else "Approve auto-execution"
            )

        # Check for disagreement between agents
        if policy and risk:
            # Conflict Scenario: Policy says eligible, but Risk flags high value / supervisor review
            if policy.eligibility and (risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or risk.decision == RiskDecision.HUMAN_REVIEW):
                conflicting_points.append("Investigation/Policy confirms customer eligibility, but Risk Engine mandates supervisor authorization due to transaction limit.")
            
            # Conflict Scenario: Investigation found delay, but Policy flagged uncertainty
            if investigation and policy.requires_human_review:
                conflicting_points.append("Investigation confirms physical delivery delay, but Policy document matching confidence is below certainty threshold.")

        if not conflicting_points:
            return None  # No material disagreement

        # Arbitration by Decision Agent
        # Principle: Security & Financial Risk controls override autonomous execution speed
        if any("mandates supervisor" in c for c in conflicting_points):
            final_action = "REQUEST_SUPERVISOR_APPROVAL"
            rationale = (
                "Decision Agent Arbitration: Although Investigation and Policy confirm customer eligibility, "
                "enterprise Risk Invariant overrides autonomous execution for high-value / elevated-risk transactions. "
                "Action pre-staged in Action Gateway pending tier-2 supervisor sign-off."
            )
        else:
            final_action = "ROUTE_TO_HUMAN_DESK"
            rationale = (
                "Decision Agent Arbitration: Unresolved policy ambiguity requires human specialist discretion. "
                "Dossier compiled and routed to agent inbox."
            )

        record = AgentDebateRecord(
            case_id=case_id,
            positions=positions,
            conflicting_points=conflicting_points,
            resolution_rationale=rationale,
            final_action_chosen=final_action,
            resolved_by="Decision Agent",
            timestamp=now
        )

        # Persist to database
        try:
            conflict_rec = AgentConflict(
                id=f"CONF-{uuid.uuid4().hex[:6].upper()}",
                case_id=case_id,
                organization_id=case.organization_id or "ORG-NOVACART",
                agent_positions_json=json.dumps({k: v.model_dump() for k, v in positions.items()}),
                conflicting_points_json=json.dumps(conflicting_points),
                resolution_rationale=rationale,
                final_action_chosen=final_action,
                resolved_by="Decision Agent",
                created_at=now
            )
            db.add(conflict_rec)
            db.commit()
        except Exception:
            db.rollback()

        return record
