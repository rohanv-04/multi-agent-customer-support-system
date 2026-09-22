import uuid
import json
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..schemas.action_gateway import (
    ActionRequest,
    ActionResult,
    ActionStatus,
    VerificationResult
)
from ..schemas.risk import RiskDecision, RiskLevel, RiskEvaluationResult
from ..schemas.decision import DecisionResult, DecisionType
from ..schemas.case import CaseStatus, EventType
from ..agents.risk_agent import run_risk_agent
from ..agents.verification_agent import verify_action_execution
from ..services.case_service import CaseService
from ..tools import execute_tool
from ..database.models import (
    AuditLog,
    AgentAction,
    SupportCase,
    Refund,
    Order,
    Customer,
    get_utc_now
)
from ..database.database import SessionLocal


class ActionGateway:
    """Secure Action Gateway: Enterprise governance layer enforcing permission, policy, risk, human approval, tool execution, immutable audit ledgers, and database verification.
    
    No AI agent directly executes sensitive business operations without passing through this gateway.
    """

    ROLE_PERMISSIONS = {
        "agent": ["refund", "cancellation", "replacement", "reshipment", "ticket_update", "customer_update", "email", "whatsapp_message"],
        "supervisor": ["refund", "cancellation", "replacement", "reshipment", "ticket_update", "customer_update", "email", "whatsapp_message", "force_override"],
        "system": ["refund", "cancellation", "replacement", "reshipment", "ticket_update", "customer_update", "email", "whatsapp_message"],
        "customer": ["email", "whatsapp_message"]  # Customers cannot directly execute financial or inventory mutations
    }

    @classmethod
    def execute_action(
        cls,
        db: Session,
        request: ActionRequest,
        simulate_tool_failure: bool = False,
        simulate_state_mismatch: bool = False,
        max_retries: int = 2
    ) -> ActionResult:
        """Process an ActionRequest through the full 7-stage secure Action Gateway."""
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        now = get_utc_now()
        action_type = request.action_type.lower()
        case_id = request.case_id

        # -------------------------------------------------------------
        # Stage 1: Permission Check
        # -------------------------------------------------------------
        actor_role = (request.actor_role or "agent").lower()
        allowed_actions = cls.ROLE_PERMISSIONS.get(actor_role, [])
        if action_type not in allowed_actions:
            reason = f"Permission Denied: Actor role '{actor_role}' is not authorized to execute sensitive action '{action_type}'."
            cls._log_audit(
                db=db,
                case_id=case_id,
                entity_type="AgentAction",
                entity_id=action_id,
                action=f"{action_type.upper()}_PERMISSION_DENIED",
                actor=request.requested_by,
                details={"reason": reason, "parameters": request.parameters}
            )
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.BLOCKED.value,
                error=reason,
                result={"success": False, "reason": reason}
            )

        # -------------------------------------------------------------
        # Stage 2 & 3: Policy & Risk Evaluation Check
        # -------------------------------------------------------------
        risk_res = None
        if request.risk_result:
            try:
                risk_res = RiskEvaluationResult(**request.risk_result)
            except Exception:
                pass

        if not risk_res:
            # Dynamically run Risk Agent check with customer 360 context
            c360 = None
            cust_id = request.customer_id or request.parameters.get("customer_id")
            if cust_id:
                try:
                    from .customer_intelligence_service import CustomerIntelligenceService
                    c360 = CustomerIntelligenceService.get_customer_360(db, cust_id)
                except Exception:
                    pass

            decision_type_map = {
                "refund": DecisionType.REFUND,
                "cancellation": DecisionType.CANCELLATION,
                "replacement": DecisionType.REPLACEMENT,
                "reshipment": DecisionType.RESHIP
            }
            mapped_dec_type = decision_type_map.get(action_type, DecisionType.RESOLVE)
            synthetic_decision = DecisionResult(
                decision_type=mapped_dec_type,
                target_entity_id=request.parameters.get("order_id"),
                parameters=request.parameters,
                rationale=request.justification or "Action Gateway Evaluation",
                recommended_action_name=action_type
            )
            risk_res = run_risk_agent(db=db, decision=synthetic_decision, customer_360=c360)

        # -------------------------------------------------------------
        # Stage 4: Approval Check
        # -------------------------------------------------------------
        if risk_res.decision == RiskDecision.BLOCK:
            reason = f"Security Block: Action blocked by Risk & Compliance Engine: {'; '.join(risk_res.reasons)}"
            cls._log_audit(
                db=db,
                case_id=case_id,
                entity_type="AgentAction",
                entity_id=action_id,
                action=f"{action_type.upper()}_BLOCKED",
                actor=request.requested_by,
                details={"reasons": risk_res.reasons, "factors": [f.model_dump() for f in risk_res.factors]}
            )
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.BLOCKED.value,
                error=reason,
                result={"success": False, "reasons": risk_res.reasons}
            )

        if (risk_res.decision == RiskDecision.HUMAN_REVIEW or request.approval_required) and actor_role not in ["supervisor", "admin"]:
            # Action requires human review and sign-off
            if case_id:
                case = CaseService.get_case(db, case_id)
                if case and case.status != CaseStatus.HUMAN_REVIEW.value:
                    CaseService.transition_status(
                        db=db,
                        case=case,
                        new_status=CaseStatus.HUMAN_REVIEW.value,
                        actor="Action Gateway",
                        reason=f"Action '{action_type}' held pending {risk_res.required_approval} approval"
                    )

            cls._log_audit(
                db=db,
                case_id=case_id,
                entity_type="AgentAction",
                entity_id=action_id,
                action=f"{action_type.upper()}_APPROVAL_REQUIRED",
                actor=request.requested_by,
                details={
                    "required_approval": risk_res.required_approval,
                    "reasons": risk_res.reasons,
                    "parameters": request.parameters
                }
            )

            return ActionResult(
                action_id=action_id,
                status=ActionStatus.APPROVAL_PENDING.value,
                error=f"Action held pending human approval ({risk_res.required_approval}).",
                result={
                    "success": False,
                    "approval_pending": True,
                    "required_approval": risk_res.required_approval,
                    "reasons": risk_res.reasons
                }
            )

        # -------------------------------------------------------------
        # Stage 5: Execute Tool with Safe Retry Loop
        # -------------------------------------------------------------
        retry_count = 0
        execution_result = {}
        verification_result = None

        while retry_count <= max_retries:
            if simulate_tool_failure:
                execution_result = {
                    "success": False,
                    "error": "Simulated Gateway Tool/API Connection Failure (503 Service Unavailable)"
                }
            elif simulate_state_mismatch:
                # Falsify tool success without mutating the real database
                execution_result = {
                    "success": True,
                    "result": {"success": True, "message": "Falsified success without DB state change"}
                }
            else:
                execution_result = cls._dispatch_tool_execution(action_type, request.parameters, request.task_id or "gateway")

            # -------------------------------------------------------------
            # Stage 6: Independent Database Verification
            # -------------------------------------------------------------
            verification_result = verify_action_execution(
                db=db,
                request=request,
                execution_result=execution_result.get("result", execution_result),
                retry_count=retry_count,
                max_retries=max_retries
            )

            if verification_result.verified:
                break

            if verification_result.safe_to_retry and retry_count < max_retries:
                retry_count += 1
                cls._log_audit(
                    db=db,
                    case_id=case_id,
                    entity_type="AgentAction",
                    entity_id=action_id,
                    action=f"{action_type.upper()}_RETRY_ATTEMPT_{retry_count}",
                    actor="Verification Agent",
                    details={"error": verification_result.mismatch_details, "retry": retry_count}
                )
                continue
            else:
                break

        # -------------------------------------------------------------
        # Stage 7: Immutable Audit Logging & Case Lifecycle
        # -------------------------------------------------------------
        audit_status = "VERIFIED" if verification_result.verified else ("ESCALATED" if verification_result.should_escalate else "FAILED")

        audit_log = cls._log_audit(
            db=db,
            case_id=case_id,
            entity_type="AgentAction",
            entity_id=action_id,
            action=f"{action_type.upper()}_{audit_status}",
            actor=request.requested_by,
            details={
                "action_type": action_type,
                "parameters": request.parameters,
                "tool_result": execution_result,
                "verification": verification_result.model_dump(),
                "retries": retry_count
            }
        )

        if case_id:
            CaseService.record_agent_action(
                db=db,
                case_id=case_id,
                agent_name="Action Gateway",
                action_type=action_type,
                task_id=request.task_id,
                status="completed" if verification_result.verified else "failed",
                input_summary=f"Action Request: {action_type} for case {case_id}",
                output_summary=verification_result.verification_summary,
                result_metadata=execution_result,
                confidence=1.0 if verification_result.verified else 0.4
            )

            if verification_result.should_escalate:
                case = CaseService.get_case(db, case_id)
                if case and case.status != CaseStatus.ESCALATED.value:
                    CaseService.transition_status(
                        db=db,
                        case=case,
                        new_status=CaseStatus.ESCALATED.value,
                        actor="Verification Agent",
                        reason=f"Verification failed repeatedly after {retry_count} retries: {verification_result.mismatch_details}"
                    )

        final_status = ActionStatus.VERIFIED.value if verification_result.verified else ActionStatus.FAILED.value
        ext_ref = execution_result.get("result", {}).get("refund_id") or execution_result.get("result", {}).get("cancellation_id") or execution_result.get("result", {}).get("replacement_id") or execution_result.get("result", {}).get("tracking_number")

        return ActionResult(
            action_id=action_id,
            status=final_status,
            external_reference=ext_ref,
            result=execution_result.get("result", execution_result),
            error=verification_result.mismatch_details if not verification_result.verified else None,
            verification=verification_result,
            audit_id=audit_log.id if audit_log else None
        )

    @classmethod
    def approve_action(
        cls,
        db: Session,
        request: ActionRequest,
        approved_by: str = "Human Lead / Supervisor"
    ) -> ActionResult:
        """Explicitly approve and execute an action that was previously held in APPROVAL_PENDING."""
        request.approval_required = False
        request.actor_role = "supervisor"
        cls._log_audit(
            db=db,
            case_id=request.case_id,
            entity_type="AgentAction",
            entity_id=f"APP-{uuid.uuid4().hex[:6].upper()}",
            action=f"{request.action_type.upper()}_HUMAN_APPROVED",
            actor=approved_by,
            details={"approved_by": approved_by, "parameters": request.parameters}
        )
        return cls.execute_action(db=db, request=request)

    @classmethod
    def _dispatch_tool_execution(cls, action_type: str, params: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Route to appropriate registered executable tool."""
        tool_name_map = {
            "refund": "process_refund",
            "cancellation": "cancel_order",
            "replacement": "create_replacement",
            "reshipment": "reship_order",
            "email": "send_customer_email",
            "whatsapp_message": "send_whatsapp_message",
            "ticket_update": "update_support_ticket",
            "customer_update": "update_customer_profile"
        }
        tool_name = tool_name_map.get(action_type, action_type)
        return execute_tool(tool_name=tool_name, params=params, task_id=task_id)

    @classmethod
    def _log_audit(
        cls,
        db: Session,
        case_id: Optional[str],
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        details: Dict[str, Any]
    ) -> Optional[AuditLog]:
        """Record an immutable audit entry."""
        try:
            log = AuditLog(
                case_id=case_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_type="agent" if "agent" in actor.lower() else "user",
                actor_id=actor,
                details_json=json.dumps(details),
                created_at=get_utc_now()
            )
            db.add(log)
            db.commit()
            return log
        except Exception as e:
            db.rollback()
            print(f"[Audit Log Error]: {e}")
            return None


action_gateway = ActionGateway()
