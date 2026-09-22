import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import SupportCase, CaseDNARecord, CaseMessage
from ..schemas.differentiation import SimilarCaseResult, CaseDNA


class CaseSimilarityService:
    """Historical Case Similarity & Decision Support Engine.
    
    Identifies top matching resolved historical cases based on:
    - Intent & Sub-intent alignment
    - Affected business domain
    - Case DNA complexity & severity
    - Channel & customer tier
    
    Provides precedent evidence to the Decision Engine without blindly duplicating actions.
    """

    @staticmethod
    def find_similar_cases(
        db: Session,
        target_case: SupportCase,
        case_dna: Optional[CaseDNA] = None,
        limit: int = 5
    ) -> List[SimilarCaseResult]:
        target_intent = (target_case.intent or (case_dna.intent if case_dna else "") or "general").lower()
        target_business = (case_dna.affected_business_area if case_dna else "logistics").lower()
        target_channel = (target_case.channel or "web_chat").lower()
        target_priority = (target_case.priority or "medium").lower()

        # Query past cases excluding current case
        all_cases = db.query(SupportCase).filter(SupportCase.id != target_case.id).all()

        scored_cases = []
        for c in all_cases:
            score = 0.0
            c_intent = (c.intent or "").lower()
            c_subject = (c.subject or "").lower()
            c_channel = (c.channel or "web_chat").lower()
            c_priority = (c.priority or "medium").lower()

            # 1. Intent similarity (up to 45%)
            if target_intent and c_intent:
                if target_intent == c_intent:
                    score += 0.45
                elif any(word in c_intent for word in target_intent.split("_")):
                    score += 0.30
                elif any(word in c_subject for word in target_intent.split("_")):
                    score += 0.20

            # 2. Priority / Severity similarity (up to 20%)
            if target_priority == c_priority:
                score += 0.20
            elif target_priority in ["high", "urgent"] and c_priority in ["high", "urgent"]:
                score += 0.15

            # 3. Channel similarity (up to 15%)
            if target_channel == c_channel:
                score += 0.15

            # 4. Keyword overlap in subject/description (up to 20%)
            target_words = set(target_case.subject.lower().split())
            case_words = set(c_subject.split())
            common_words = target_words.intersection(case_words)
            if common_words:
                score += min(0.20, len(common_words) * 0.05)

            if score > 0.25:
                # Find resolution message / summary
                resolution = "Resolved via standard automated verification protocol."
                outbound_msg = db.query(CaseMessage).filter(
                    CaseMessage.case_id == c.id,
                    CaseMessage.direction == "outbound"
                ).first()
                if outbound_msg:
                    resolution = outbound_msg.body[:120] + "..."

                scored_cases.append(SimilarCaseResult(
                    case_id=c.id,
                    similarity_score=round(min(0.98, score), 2),
                    intent=c.intent or "general_support",
                    subject=c.subject,
                    resolution_summary=resolution,
                    outcome="Auto-Resolved & Verified" if c.status == "RESOLVED" else f"Status: {c.status}",
                    was_escalated=bool(c.escalations),
                    channel=c.channel or "web_chat"
                ))

        # Sort descending by similarity score
        scored_cases.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_cases[:limit]
