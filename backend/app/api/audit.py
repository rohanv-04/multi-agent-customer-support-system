import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..schemas.observability import AuditLogFilter
from ..services.observability_service import observability_service

from ..core.security import get_current_user, require_permission
from ..database.models import User
from ..schemas.auth import Permission, UserRole

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs")
def get_audit_logs(
    case_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    actor_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission(Permission.VIEW_AUDIT_LOGS.value)),
    db: Session = Depends(get_db)
):
    """
    Searchable & filterable Enterprise Audit Log Explorer with RBAC and Tenancy Isolation.
    Guarantees complete 5W1H traceability for every sensitive action:
    Who, What, When, Why, and Result.
    """
    filter_params = AuditLogFilter(
        organization_id=current_user.organization_id if current_user.role != UserRole.ADMIN.value else None,
        case_id=case_id,
        entity_type=entity_type,
        action=action,
        actor_type=actor_type,
        search=search,
        limit=limit,
        offset=offset
    )
    try:
        logs = observability_service.search_audit_logs(db, filter_params)
        return {
            "total_returned": len(logs),
            "limit": limit,
            "offset": offset,
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query audit logs: {str(e)}")
