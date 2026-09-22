import json
import hashlib
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import (
    SupportCase,
    CaseDNARecord,
    Customer,
    Order,
    get_utc_now
)
from ..schemas.differentiation import CaseDNA
from ..schemas.intake import IntakeExtractionResult
from ..schemas.customer import Customer360Response


class CaseDNAService:
    """Case DNA Intelligence Service.
    
    Generates a structured, multidimensional fingerprint for each SupportCase.
    Enables capability-based dynamic agent orchestration:
    - High complexity/risk cases activate swarm investigation, policy intelligence, and risk engines.
    - Low complexity inquiries (e.g. basic tracking, FAQ) use fast, lightweight pathways.
    """

    @staticmethod
    def generate_case_dna(
        db: Session,
        case: SupportCase,
        intake: IntakeExtractionResult,
        c360: Optional[Customer360Response] = None
    ) -> CaseDNA:
        now = get_utc_now()
        intent = (intake.intent or case.intent or "general_support").lower()
        sub_intent = intake.sub_intent
        sentiment = (intake.sentiment or case.sentiment or "neutral").lower()
        urgency = (intake.urgency or case.priority or "medium").lower()

        # Customer value
        tier = "Standard"
        is_vip = False
        if c360:
            if hasattr(c360, "loyalty") and c360.loyalty:
                tier = c360.loyalty.tier
                is_vip = c360.loyalty.is_vip or "vip" in tier.lower() or "gold" in tier.lower() or "platinum" in tier.lower()
            elif isinstance(c360, dict):
                loyalty_dict = c360.get("loyalty", {})
                tier = loyalty_dict.get("tier", "Standard")
                is_vip = loyalty_dict.get("is_vip", False)

        # Determine affected business area
        if any(w in intent for w in ["delay", "track", "ship", "deliver", "lost", "transit"]):
            business_area = "logistics"
        elif any(w in intent for w in ["refund", "charge", "billing", "payment", "invoice", "double"]):
            business_area = "billing"
        elif any(w in intent for w in ["broken", "damaged", "warranty", "defective", "hardware", "replace"]):
            business_area = "hardware"
        elif any(w in intent for w in ["policy", "terms", "conflict", "dispute"]):
            business_area = "policy"
        elif any(w in intent for w in ["fraud", "hacked", "unauthorized", "stolen"]):
            business_area = "security"
        else:
            business_area = "general"

        # Policy complexity
        if business_area in ["policy", "security"] or "conflict" in intent:
            policy_complexity = "complex"
        elif business_area in ["billing", "hardware"] or "refund" in intent:
            policy_complexity = "standard"
        elif "alien" in intent or "crypto" in intent:
            policy_complexity = "ambiguous"
        else:
            policy_complexity = "simple"

        # Severity
        if sentiment == "frustrated" or urgency == "urgent" or business_area == "security":
            severity = "critical" if is_vip else "high"
        elif sentiment == "negative" or urgency == "high":
            severity = "high"
        elif urgency == "low":
            severity = "low"
        else:
            severity = "medium"

        # Operational risk
        if business_area in ["security", "billing"] and (is_vip or severity in ["high", "critical"]):
            operational_risk = "high"
        elif "refund" in intent or "replacement" in intent:
            operational_risk = "medium"
        else:
            operational_risk = "low"

        # SLA Risk
        sla_risk = "low"
        if case.sla_deadline:
            remaining = (case.sla_deadline - now).total_seconds() / 3600.0
            if remaining < 0:
                sla_risk = "breached"
            elif remaining < 2.0:
                sla_risk = "high"
            elif remaining < 6.0:
                sla_risk = "elevated"

        # Required Capabilities formulation
        required_caps: List[str] = ["intake_analysis", "customer_360"]

        if business_area in ["logistics", "billing", "hardware"] or "order" in intent:
            required_caps.append("investigation_engine")
            if severity in ["high", "critical"] or operational_risk in ["medium", "high"]:
                required_caps.append("swarm_investigation")

        if policy_complexity in ["standard", "complex", "ambiguous"] or "refund" in intent or "cancel" in intent:
            required_caps.append("policy_intelligence")

        if operational_risk in ["medium", "high"] or "refund" in intent or is_vip:
            required_caps.append("risk_guardrails")

        if any(c in required_caps for c in ["policy_intelligence", "risk_guardrails", "investigation_engine"]):
            required_caps.append("next_best_action")
            required_caps.append("decision_matrix")
            required_caps.append("action_gateway")
            required_caps.append("verification_engine")

        required_caps.append("conversation_integrity_guard")

        # Fingerprint hash for clustering & similarity search
        fingerprint_raw = f"{intent}:{sub_intent}:{business_area}:{severity}:{policy_complexity}:{tier}"
        fingerprint_hash = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()[:16]

        dna = CaseDNA(
            case_id=case.id,
            intent=intent,
            sub_intent=sub_intent,
            severity=severity,
            urgency=urgency,
            customer_value=tier,
            operational_risk=operational_risk,
            policy_complexity=policy_complexity,
            sla_risk=sla_risk,
            fraud_risk_score=0.15 if business_area == "billing" else 0.0,
            channel=case.channel or "web_chat",
            affected_business_area=business_area,
            required_capabilities=required_caps,
            fingerprint_hash=fingerprint_hash,
            created_at=now
        )

        # Persist to database
        try:
            record = db.query(CaseDNARecord).filter(CaseDNARecord.case_id == case.id).first()
            if not record:
                record = CaseDNARecord(
                    case_id=case.id,
                    organization_id=case.organization_id or "ORG-NOVACART",
                    intent=intent,
                    sub_intent=sub_intent,
                    severity=severity,
                    urgency=urgency,
                    customer_value=tier,
                    operational_risk=operational_risk,
                    policy_complexity=policy_complexity,
                    sla_risk=sla_risk,
                    fraud_risk_score=dna.fraud_risk_score,
                    channel=dna.channel,
                    affected_business_area=business_area,
                    required_capabilities_json=json.dumps(required_caps),
                    fingerprint_hash=fingerprint_hash,
                    created_at=now
                )
                db.add(record)
            else:
                record.intent = intent
                record.sub_intent = sub_intent
                record.severity = severity
                record.urgency = urgency
                record.customer_value = tier
                record.operational_risk = operational_risk
                record.policy_complexity = policy_complexity
                record.sla_risk = sla_risk
                record.required_capabilities_json = json.dumps(required_caps)
                record.fingerprint_hash = fingerprint_hash
            db.commit()
        except Exception:
            db.rollback()

        return dna

    @staticmethod
    def is_capability_required(dna: CaseDNA, capability: str) -> bool:
        """Determines whether a specialist agent/tool should execute for this case."""
        return capability.lower() in [c.lower() for c in dna.required_capabilities]
