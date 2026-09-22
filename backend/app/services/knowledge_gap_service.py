import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import KnowledgeGap, SupportCase, get_utc_now
from ..schemas.differentiation import KnowledgeGapResponse


class KnowledgeGapService:
    """Knowledge Gap Intelligence Subsystem.
    
    Identifies blindspots in corporate documentation:
    - Queries returning zero relevant policy chunks (low cosine similarity)
    - Ambiguous edge-case clauses resulting in frequent human escalation
    - Unaddressed customer queries (e.g. international customs, battery disposal, b2b tax exemptions)
    
    Strict Invariant: Never invent policies automatically. Catalog structured gaps for human authoring.
    """

    @staticmethod
    def get_all(db: Session, organization_id: str = "ORG-NOVACART") -> List[KnowledgeGapResponse]:
        now = get_utc_now()
        gaps = db.query(KnowledgeGap).filter(KnowledgeGap.organization_id == organization_id).all()

        # Seed initial knowledge gaps if none exist
        if not gaps:
            seeds = [
                {
                    "id": "KG-INTL-001",
                    "topic": "International Customs Duties & Cross-Border VAT Refund Policy",
                    "occurrences": 6,
                    "affected_cases": ["CASE-1008", "CASE-1012"],
                    "evidence": ["Customer inquiries regarding EU VAT import fees lack matching section in standard return policy."],
                    "severity": "high",
                    "suggested_topic": "Cross-Border Shipping & Import Duty Reconciliation Guidelines"
                },
                {
                    "id": "KG-TRADEIN-002",
                    "topic": "Refurbished Hardware Trade-In Valuation & Credit Limits",
                    "occurrences": 4,
                    "affected_cases": ["CASE-1019"],
                    "evidence": ["Policy store contains rules for retail purchase returns, but trade-in equipment valuation is undefined."],
                    "severity": "medium",
                    "suggested_topic": "Trade-In & Equipment Buyback Policy Addendum"
                },
                {
                    "id": "KG-GIFT-003",
                    "topic": "Third-Party Digital Gift Card Redemption Exceptions",
                    "occurrences": 3,
                    "affected_cases": ["CASE-1025"],
                    "evidence": ["Low vector retrieval score (0.42) for gift card refund disputes when original purchaser is unknown."],
                    "severity": "low",
                    "suggested_topic": "Promotional Voucher & Gift Card Refund Protocol"
                }
            ]

            for s in seeds:
                g = KnowledgeGap(
                    id=s["id"],
                    organization_id=organization_id,
                    topic=s["topic"],
                    occurrences=s["occurrences"],
                    affected_cases_json=json.dumps(s["affected_cases"]),
                    evidence_json=json.dumps(s["evidence"]),
                    severity=s["severity"],
                    status="OPEN",
                    suggested_documentation_topic=s["suggested_topic"],
                    detected_at=now - datetime.timedelta(days=2)
                )
                db.add(g)
            try:
                db.commit()
                gaps = db.query(KnowledgeGap).filter(KnowledgeGap.organization_id == organization_id).all()
            except Exception:
                db.rollback()

        return [
            KnowledgeGapResponse(
                id=g.id,
                topic=g.topic,
                occurrences=g.occurrences,
                affected_cases=json.loads(g.affected_cases_json) if g.affected_cases_json else [],
                evidence=json.loads(g.evidence_json) if g.evidence_json else [],
                severity=g.severity,
                status=g.status,
                suggested_documentation_topic=g.suggested_documentation_topic,
                detected_at=g.detected_at
            ) for g in gaps
        ]

    @staticmethod
    def record_knowledge_gap(
        db: Session,
        topic: str,
        case_id: str,
        evidence: str,
        severity: str = "medium",
        organization_id: str = "ORG-NOVACART"
    ) -> KnowledgeGapResponse:
        now = get_utc_now()
        existing = db.query(KnowledgeGap).filter(
            KnowledgeGap.organization_id == organization_id,
            KnowledgeGap.topic.ilike(f"%{topic[:30]}%")
        ).first()

        if existing:
            existing.occurrences += 1
            existing.last_detected = now
            cases = json.loads(existing.affected_cases_json) if existing.affected_cases_json else []
            if case_id not in cases:
                cases.append(case_id)
            existing.affected_cases_json = json.dumps(cases)
            db.commit()
            target = existing
        else:
            gap_id = f"KG-AUTO-{uuid.uuid4().hex[:6].upper()}"
            target = KnowledgeGap(
                id=gap_id,
                organization_id=organization_id,
                topic=topic,
                occurrences=1,
                affected_cases_json=json.dumps([case_id]),
                evidence_json=json.dumps([evidence]),
                severity=severity,
                status="OPEN",
                suggested_documentation_topic=f"Guidance on {topic}",
                detected_at=now
            )
            db.add(target)
            db.commit()

        return KnowledgeGapResponse(
            id=target.id,
            topic=target.topic,
            occurrences=target.occurrences,
            affected_cases=json.loads(target.affected_cases_json) if target.affected_cases_json else [],
            evidence=json.loads(target.evidence_json) if target.evidence_json else [],
            severity=target.severity,
            status=target.status,
            suggested_documentation_topic=target.suggested_documentation_topic,
            detected_at=target.detected_at
        )
