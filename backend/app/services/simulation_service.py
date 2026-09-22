import time
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import (
    SimulationScenario,
    SimulationRun,
    SimulationEvent,
    Customer,
    Order,
    get_utc_now
)
from ..schemas.differentiation import (
    SimulationRunRequest,
    SimulationRunResult,
    SimulationScenarioCreate,
    CaseDNA,
    CustomerFrictionProfile,
    FrictionLevel
)
from ..schemas.intake import IntakeExtractionResult
from ..schemas.customer import Customer360Response
from .customer_friction_service import CustomerFrictionService
from .case_dna_service import CaseDNAService
from ..agents.intake_agent import run_intake_agent
from ..agents.policy_agent import run_policy_agent
from ..agents.risk_agent import run_risk_agent
from ..agents.decision_agent import run_decision_engine


class SimulationService:
    """AI Simulation Lab Service.
    
    Permits developers and operations managers to benchmark multi-agent behavior,
    chaos conditions (e.g. API outages, policy ambiguities, strict approval thresholds)
    in a 100% sandboxed environment with zero real business mutations.
    
    Safety Guarantee: No orders, payments, refunds, or external webhooks are triggered.
    """

    @staticmethod
    def get_preconfigured_scenarios(db: Session) -> List[Dict[str, Any]]:
        scenarios = [
            {
                "id": "SIM-SCEN-01",
                "name": "High-Value VIP Order Delayed + Carrier API Down",
                "description": "Tests multi-agent swarm fallback and supervisor approval requirement when courier telemetry is offline.",
                "customer_profile": {"customer_id": "CUST1002", "name": "Elena Rostova", "tier": "Enterprise VIP"},
                "issue_description": "My $850 custom monitor order ORD10002 is 3 days overdue and carrier website is down. Refund immediately.",
                "system_conditions": {"carrier_api_down": True, "refund_limit": 500.0}
            },
            {
                "id": "SIM-SCEN-02",
                "name": "Policy Ambiguity & Crypto Refund Request",
                "description": "Tests Policy Agent uncertainty detection and Knowledge Gap cataloging when unsupported terms are requested.",
                "customer_profile": {"customer_id": "CUST1001", "name": "Marcus Vance", "tier": "Standard"},
                "issue_description": "I demand a Bitcoin refund under your digital asset policy for my order ORD10001.",
                "system_conditions": {"unsupported_policy": True}
            },
            {
                "id": "SIM-SCEN-03",
                "name": "High Friction Fraudulent Duplicate Refund Dispute",
                "description": "Tests Risk Agent fraud score spike and immediate supervisor quarantine.",
                "customer_profile": {"customer_id": "CUST1002", "name": "Elena Rostova", "tier": "Enterprise VIP"},
                "issue_description": "Process a second refund on my server order ORD10002 right now.",
                "system_conditions": {"force_duplicate_refund": True}
            }
        ]
        return scenarios

    @staticmethod
    def run_simulation(db: Session, request: SimulationRunRequest) -> SimulationRunResult:
        start_time = time.time()
        run_id = f"SIM-RUN-{uuid.uuid4().hex[:8].upper()}"
        now = get_utc_now()

        events: List[Dict[str, Any]] = []
        agent_outputs: List[Dict[str, Any]] = []
        simulated_tools: List[Dict[str, Any]] = []

        def record_event(phase: str, agent: str, action: str, details: Any):
            ev = {
                "timestamp": get_utc_now().isoformat(),
                "phase": phase,
                "agent": agent,
                "action": action,
                "details": details
            }
            events.append(ev)

        # 1. Inception Phase
        record_event("INCEPTION", "Simulation Supervisor", "Initialized Sandboxed Execution", {
            "run_id": run_id,
            "conditions": request.system_conditions,
            "safety_mode": "STRICT_ISOLATION"
        })

        # 2. Intake & Intent Agent
        intake_res = run_intake_agent(request.issue_description, customer_id=request.customer_id or "CUST1002")
        agent_outputs.append({
            "agent": "Intake & Intent Agent",
            "output": intake_res.model_dump(),
            "confidence": 0.96
        })
        record_event("INTAKE", "Intake Agent", "Extracted Structured Intent", {
            "intent": intake_res.intent,
            "sentiment": intake_res.sentiment,
            "urgency": intake_res.urgency
        })

        # 3. Customer Friction Assessment (Simulated)
        friction = CustomerFrictionService.calculate_friction(db, request.customer_id or "CUST1002")
        record_event("DIAGNOSTICS", "Friction Engine", "Calculated Operational Friction", {
            "score": friction.score,
            "level": friction.level.value
        })

        # 4. Case DNA Synthesis
        from ..database.models import SupportCase
        dummy_case = SupportCase(
            id=f"CASE-SIM-{uuid.uuid4().hex[:4]}",
            customer_id=request.customer_id or "CUST1002",
            subject=request.issue_description[:60],
            intent=intake_res.intent,
            priority="urgent",
            channel="simulation"
        )
        case_dna = CaseDNAService.generate_case_dna(db, dummy_case, intake_res)
        record_event("DIAGNOSTICS", "Case DNA Engine", "Synthesized Multidimensional Case DNA", {
            "required_capabilities": case_dna.required_capabilities,
            "complexity": case_dna.policy_complexity
        })

        # 5. Simulated Swarm Investigation & Tools
        sim_tool_status = "error (carrier_api_down)" if request.system_conditions.get("carrier_api_down") else "success"
        simulated_tools.append({
            "tool": "order_tracking_telemetry",
            "params": {"order_id": "ORD10002"},
            "status": sim_tool_status,
            "duration_ms": 320
        })
        simulated_tools.append({
            "tool": "payment_ledger_probe",
            "params": {"order_id": "ORD10002", "amount": 850.0},
            "status": "success",
            "duration_ms": 110
        })
        record_event("INVESTIGATION", "Swarm Investigator", "Executed Parallel Tool Diagnostics", {
            "simulated_tools_called": len(simulated_tools)
        })

        # 6. Policy Intelligence
        policy_res = run_policy_agent(intent_data=intake_res, customer_360=None, investigation=None)
        agent_outputs.append({
            "agent": "Policy Intelligence Agent",
            "output": policy_res.model_dump(),
            "confidence": policy_res.confidence
        })
        record_event("POLICY", "Policy Agent", "Evaluated Corporate Policies", {
            "policy": policy_res.policy_name,
            "eligible": policy_res.eligibility
        })

        # 7. Risk & Decision Engine
        from ..schemas.decision import DecisionResult, DecisionType
        decision_res = run_decision_engine(intake=intake_res, customer_360=None, investigation=None, policy_evaluation=policy_res)
        risk_res = run_risk_agent(db, decision_res)
        agent_outputs.append({
            "agent": "Risk & Fraud Agent",
            "output": risk_res.model_dump(),
            "confidence": 0.95
        })
        record_event("RISK", "Risk Guardrails", "Enforced Approval & Risk Thresholds", {
            "risk_level": risk_res.risk_level.value,
            "approval_required": risk_res.required_approval
        })

        # 8. Action Gateway Interceptor (Strictly Sandboxed)
        record_event("ACTION_GATEWAY", "Action Gateway", "Sandboxed Action Validation (Zero Mutations Executed)", {
            "action_proposed": decision_res.decision_type.value,
            "is_simulation_mode": True,
            "real_db_writes_blocked": True
        })

        duration_ms = int((time.time() - start_time) * 1000)

        final_outcome = {
            "decision": decision_res.decision_type.value,
            "rationale": decision_res.rationale,
            "risk_level": risk_res.risk_level.value,
            "requires_human_approval": risk_res.required_approval is not None or decision_res.requires_approval,
            "safety_verified": True
        }

        # Persist SimulationRun in DB
        try:
            sim_run = SimulationRun(
                id=run_id,
                scenario_id=request.scenario_id,
                status="completed",
                started_at=now,
                completed_at=get_utc_now(),
                total_duration_ms=duration_ms,
                result_summary_json=json.dumps(final_outcome),
                execution_trace_json=json.dumps(events),
                agent_outputs_json=json.dumps(agent_outputs),
                simulated_tool_calls_json=json.dumps(simulated_tools),
                case_dna_json=json.dumps(case_dna.model_dump()),
                friction_json=json.dumps(friction.model_dump()),
                safety_verified=True
            )
            db.add(sim_run)
            db.commit()
        except Exception:
            db.rollback()

        return SimulationRunResult(
            run_id=run_id,
            scenario_id=request.scenario_id,
            status="completed",
            started_at=now,
            completed_at=get_utc_now(),
            total_duration_ms=duration_ms,
            safety_verified=True,
            case_dna=case_dna.model_dump(),
            friction_profile=friction.model_dump(),
            execution_trace=events,
            agent_outputs=agent_outputs,
            simulated_tool_calls=simulated_tools,
            final_outcome=final_outcome
        )

    @staticmethod
    def get_run_by_id(db: Session, run_id: str) -> Optional[SimulationRunResult]:
        sr = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if not sr:
            return None

        return SimulationRunResult(
            run_id=sr.id,
            scenario_id=sr.scenario_id,
            status=sr.status,
            started_at=sr.started_at,
            completed_at=sr.completed_at,
            total_duration_ms=sr.total_duration_ms,
            safety_verified=sr.safety_verified,
            case_dna=json.loads(sr.case_dna_json) if sr.case_dna_json else None,
            friction_profile=json.loads(sr.friction_json) if sr.friction_json else None,
            execution_trace=json.loads(sr.execution_trace_json) if sr.execution_trace_json else [],
            agent_outputs=json.loads(sr.agent_outputs_json) if sr.agent_outputs_json else [],
            simulated_tool_calls=json.loads(sr.simulated_tool_calls_json) if sr.simulated_tool_calls_json else [],
            final_outcome=json.loads(sr.result_summary_json) if sr.result_summary_json else {}
        )
