import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..database.models import WorkflowHealingRecord, get_utc_now
from ..schemas.differentiation import SelfHealingReport


class SelfHealingEngine:
    """Self-Healing Workflow Recovery Subsystem.
    
    When an agent or tool fails:
    1. Analyzes the failure root cause.
    2. Classifies into Recoverable vs Non-recoverable.
    3. If Recoverable & within safe retry limits: Re-plans parameters, resets failed node, and retries.
    4. If Non-recoverable or retry limit exceeded: Gracefully halts and escalates to human desk.
    
    Strict invariant: Never create infinite recovery loops.
    """

    MAX_RETRIES = 2

    @staticmethod
    def handle_failure(
        db: Session,
        case_id: Optional[str],
        task_id: Optional[str],
        failure_type: str,
        error_message: str,
        current_retry_count: int = 0,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        clean_failure_type = failure_type.lower()
        now = get_utc_now()
        new_retry_count = current_retry_count + 1

        # 1. Determine Recoverability
        is_recoverable = False
        recommended_recovery = "escalate"
        disposition = "escalated"

        recoverable_types = [
            "timeout",
            "temporary_api_failure",
            "invalid_tool_input",
            "missing_data",
            "tool_failure",
            "llm_timeout"
        ]

        if any(r in clean_failure_type for r in recoverable_types):
            if new_retry_count <= SelfHealingEngine.MAX_RETRIES:
                is_recoverable = True
                recommended_recovery = "tool_retry" if "tool" in clean_failure_type or "api" in clean_failure_type else "replan"
                disposition = "recovered"
            else:
                is_recoverable = False
                recommended_recovery = "escalate_max_retries"
                disposition = "escalated"
        else:
            # Policy violations, security failures, verification mismatches -> immediate escalation
            is_recoverable = False
            recommended_recovery = "escalate"
            disposition = "escalated"

        # 2. Persist Healing Telemetry
        try:
            record = WorkflowHealingRecord(
                case_id=case_id,
                task_id=task_id,
                failure_type=failure_type,
                error_message=error_message[:500],
                recovery_attempted=recommended_recovery,
                retry_count=new_retry_count,
                recovery_successful=is_recoverable,
                final_disposition=disposition,
                details_json=json.dumps(context or {}),
                created_at=now
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()

        return {
            "is_recoverable": is_recoverable,
            "recovery_strategy": recommended_recovery,
            "retry_count": new_retry_count,
            "max_retries": SelfHealingEngine.MAX_RETRIES,
            "final_disposition": disposition,
            "error_message": error_message,
            "replan_suggested": recommended_recovery == "replan",
            "should_escalate": not is_recoverable
        }
