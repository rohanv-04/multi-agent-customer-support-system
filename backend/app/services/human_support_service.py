import uuid
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session

from ..database.models import (
    HumanSupportAssignment,
    SupportCase,
    CaseEvent,
    Customer
)
from ..schemas.human_support import (
    RepresentativeInfo,
    HumanSupportAssignmentResponse,
    CallInitiatedResponse
)

import os
from ..providers.telephony import get_telephony_provider

# Centralized Support Team Configuration loaded from environment
def get_support_contacts() -> List[Dict[str, Any]]:
    return [
        {
            "id": "kavin",
            "name": "Kavin",
            "phone": os.getenv("AGENT_KAVIN_PHONE", "7200212576"),
            "available": True,
        },
        {
            "id": "rohan",
            "name": "Rohan",
            "phone": os.getenv("AGENT_ROHAN_PHONE", "8025136089"),
            "available": True,
        },
        {
            "id": "narahari",
            "name": "Narahari",
            "phone": os.getenv("AGENT_NARAHARI_PHONE", "7396892041"),
            "available": True,
        },
    ]

SUPPORT_CONTACTS: List[Dict[str, Any]] = get_support_contacts()


class HumanSupportService:
    """Service managing human support assignment, representative selection, and telephony dispatch."""

    def __init__(self, contacts: Optional[List[Dict[str, Any]]] = None):
        self._contacts = contacts or get_support_contacts()
        self.telephony_provider = get_telephony_provider()

    def get_configured_contacts(self) -> List[Dict[str, Any]]:
        """Return the list of configured support contacts."""
        return self._contacts

    def select_representative(
        self,
        random_provider: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Select ONE representative from available support team members.

        Accepts an optional random_provider function or seed for deterministic testing.
        """
        available_contacts = [c for c in self._contacts if c.get("available", True)]
        if not available_contacts:
            available_contacts = self._contacts

        if random_provider:
            return random_provider(available_contacts)

        if seed is not None:
            rng = random.Random(seed)
            return rng.choice(available_contacts)

        return random.choice(available_contacts)

    def assign_human_support(
        self,
        db: Session,
        case_id: str,
        customer_id: str,
        organization_id: str = "ORG-NOVACART",
        notes: Optional[str] = None,
        random_provider: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None,
        seed: Optional[int] = None,
    ) -> HumanSupportAssignmentResponse:
        """Assign a random human representative to a customer's support case and log lifecycle events."""
        now = datetime.now(timezone.utc)

        # 1. Ensure Case Exists or Create Case if needed
        case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
        if not case:
            # Check or create customer
            cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
            if not cust:
                cust = Customer(
                    customer_id=customer_id,
                    organization_id=organization_id,
                    name="Valued Customer",
                    email=f"{customer_id.lower()}@novacart.com",
                    tier="Standard",
                    created_at=now
                )
                db.add(cust)
                db.flush()

            case = SupportCase(
                id=case_id,
                organization_id=organization_id,
                customer_id=customer_id,
                subject="Human Support Assistance Request",
                description=notes or "Customer requested direct human agent support via voice handoff.",
                intent="human_escalation",
                priority="high",
                status="ESCALATED",
                created_at=now,
                updated_at=now
            )
            db.add(case)
            db.flush()
        else:
            if case.status in ["NEW", "TRIAGING", "INVESTIGATING", "DECISION_PENDING"]:
                case.status = "ESCALATED"
            case.updated_at = now

        # 2. Select ONE representative randomly
        selected_rep = self.select_representative(random_provider=random_provider, seed=seed)

        # 3. Create HumanSupportAssignment record
        assignment_id = f"HSA-{uuid.uuid4().hex[:8].upper()}"
        assignment = HumanSupportAssignment(
            id=assignment_id,
            case_id=case.id,
            customer_id=customer_id,
            representative_id=selected_rep["id"],
            representative_name=selected_rep["name"],
            phone=selected_rep["phone"],
            assignment_method="RANDOM",
            assigned_at=now,
            status="ASSIGNED",
            organization_id=organization_id,
            notes=notes
        )
        db.add(assignment)

        # 4. Log Case Events for timeline tracking
        # Event 1: HUMAN_CONTACT_REQUESTED
        event_requested = CaseEvent(
            case_id=case.id,
            event_type="HUMAN_CONTACT_REQUESTED",
            from_status=case.status,
            to_status="ESCALATED",
            actor="Customer",
            summary="Customer requested human support handoff",
            details_json=f'{{"requested_at": "{now.isoformat()}", "method": "chat_action"}}',
            created_at=now
        )
        db.add(event_requested)

        # Event 2: HUMAN_AGENT_ASSIGNED
        event_assigned = CaseEvent(
            case_id=case.id,
            event_type="HUMAN_AGENT_ASSIGNED",
            from_status="ESCALATED",
            to_status="ESCALATED",
            actor="System",
            summary=f"Human agent assigned: {selected_rep['name']}",
            details_json=f'{{"assignment_id": "{assignment_id}", "representative_id": "{selected_rep["id"]}", "representative_name": "{selected_rep["name"]}", "phone": "{selected_rep["phone"]}"}}',
            created_at=now
        )
        db.add(event_assigned)

        db.commit()
        db.refresh(assignment)

        return HumanSupportAssignmentResponse(
            assignment_id=assignment.id,
            case_id=assignment.case_id,
            customer_id=assignment.customer_id,
            representative=RepresentativeInfo(
                id=selected_rep["id"],
                name=selected_rep["name"],
                phone=selected_rep["phone"],
                available=selected_rep.get("available", True)
            ),
            assignment_method="RANDOM",
            status=assignment.status,
            assigned_at=assignment.assigned_at,
            tel_link=f"tel:{selected_rep['phone']}"
        )

    def record_call_initiated(
        self,
        db: Session,
        case_id: str,
        assignment_id: str,
        organization_id: str = "ORG-NOVACART"
    ) -> CallInitiatedResponse:
        """Record that the customer clicked 'Call Now' to trigger device dialer (tel: link).

        Note: Does NOT mark call as COMPLETED since telephony connection outcome is unverified.
        """
        now = datetime.now(timezone.utc)

        assignment = (
            db.query(HumanSupportAssignment)
            .filter(
                HumanSupportAssignment.id == assignment_id,
                HumanSupportAssignment.case_id == case_id
            )
            .first()
        )

        if not assignment:
            raise ValueError(f"Assignment '{assignment_id}' not found for case '{case_id}'")

        # Update assignment status to CALL_INITIATED
        assignment.status = "CALL_INITIATED"

        # Log CaseEvent: CALL_INITIATED
        event_call = CaseEvent(
            case_id=case_id,
            event_type="CALL_INITIATED",
            from_status="ESCALATED",
            to_status="ESCALATED",
            actor="Customer",
            summary=f"Customer selected Call Now (tel:{assignment.phone})",
            details_json=f'{{"assignment_id": "{assignment_id}", "initiated_at": "{now.isoformat()}", "representative": "{assignment.representative_name}", "phone": "{assignment.phone}"}}',
            created_at=now
        )
        db.add(event_call)
        db.commit()
        db.refresh(assignment)

        return CallInitiatedResponse(
            assignment_id=assignment.id,
            case_id=assignment.case_id,
            status="CALL_INITIATED",
            recorded_at=now,
            representative_name=assignment.representative_name,
            phone=assignment.phone,
            tel_link=f"tel:{assignment.phone}"
        )

    def get_assignment_for_case(
        self,
        db: Session,
        case_id: str
    ) -> Optional[HumanSupportAssignmentResponse]:
        """Fetch the latest active human support assignment for a case if one exists."""
        assignment = (
            db.query(HumanSupportAssignment)
            .filter(HumanSupportAssignment.case_id == case_id)
            .order_by(HumanSupportAssignment.assigned_at.desc())
            .first()
        )

        if not assignment:
            return None

        return HumanSupportAssignmentResponse(
            assignment_id=assignment.id,
            case_id=assignment.case_id,
            customer_id=assignment.customer_id,
            representative=RepresentativeInfo(
                id=assignment.representative_id,
                name=assignment.representative_name,
                phone=assignment.phone,
                available=True
            ),
            assignment_method=assignment.assignment_method,
            status=assignment.status,
            assigned_at=assignment.assigned_at,
            tel_link=f"tel:{assignment.phone}"
        )


human_support_service = HumanSupportService()
