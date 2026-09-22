import uuid
import pytest
import datetime
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.database import SessionLocal, init_db
from backend.app.database.models import (
    Customer,
    SupportCase,
    AgentRun,
    ToolCall,
    AuditLog,
    get_utc_now
)
from backend.app.schemas.case import CaseCreate, CaseStatus
from backend.app.schemas.observability import AuditLogFilter
from backend.app.services.case_service import CaseService
from backend.app.services.observability_service import observability_service
from backend.app.services.evaluation_engine import evaluation_engine
from backend.app.services.evaluation_dataset import get_benchmarks, BENCHMARK_DATASET
from backend.app.graph.workflow import support_graph


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# 1. TEST CASE EXECUTION TRACE GENERATION (NO CHAIN-OF-THOUGHT)
# =========================================================================

def test_hierarchical_case_execution_trace_and_no_cot():
    db = SessionLocal()
    try:
        now = get_utc_now()
        case_id = f"CASE-TRACE-{uuid.uuid4().hex[:6]}"
        case = SupportCase(
            id=case_id,
            customer_id="CUST1002",
            channel="web_chat",
            subject="Damaged Package Replacement Trace Test",
            description="My item arrived broken. Please replace it.",
            priority="high",
            status=CaseStatus.INVESTIGATING.value,
            conversation_id=f"conv-{case_id}",
            created_at=now
        )
        db.add(case)
        db.commit()

        # Add an investigation agent run with tool calls
        run1 = AgentRun(
            case_id=case_id,
            agent_name="Investigation Specialist",
            started_at=now,
            ended_at=now + datetime.timedelta(milliseconds=250),
            status="completed",
            output_summary="Verified order ORD-2024-9001 delivery delay. Eligible for replacement.",
            confidence=0.96
        )
        db.add(run1)

        # Add tool call associated with this conversation
        tc = ToolCall(
            task_id=case.conversation_id,
            tool_name="order_lookup",
            input_params_json='{"order_id": "ORD-2024-9001"}',
            output_result_json='{"status": "Shipped", "item": "Sony WH-1000XM5"}',
            status="success",
            duration_ms=42,
            created_at=now
        )
        db.add(tc)
        db.commit()

        trace = observability_service.get_case_execution_trace(db, case_id)
        assert trace.case_id == case_id
        assert trace.customer_id == "CUST1002"
        assert len(trace.tree_nodes) > 0
        assert trace.total_latency_ms > 0
        assert trace.total_cost_usd > 0

        # Verify no chain of thought in evidence summaries
        for node in trace.tree_nodes:
            if node.evidence_summary:
                assert "CoT:" not in node.evidence_summary
                assert "THINKING:" not in node.evidence_summary

        # Verify tool call was attached to investigation run
        inv_node = next((n for n in trace.tree_nodes if "investigation" in n.agent_name.lower()), None)
        assert inv_node is not None
        assert len(inv_node.tool_calls) == 1
        assert inv_node.tool_calls[0].tool_name == "order_lookup"
        assert inv_node.tool_calls[0].duration_ms == 42
    finally:
        db.close()


# =========================================================================
# 2. TEST EVALUATION LAB BENCHMARKS & 9 METRIC CALCULATIONS
# =========================================================================

def test_evaluation_benchmark_dataset_coverage():
    benchmarks = get_benchmarks()
    assert len(benchmarks) >= 8

    categories = {b.category.value for b in benchmarks}
    expected_categories = {
        "delivery_issues",
        "refunds",
        "cancellations",
        "billing",
        "policy_questions",
        "escalation",
        "tool_failures",
        "ambiguous_requests"
    }
    assert expected_categories.issubset(categories)


def test_evaluation_suite_run_and_metrics_calculation():
    # Run a targeted evaluation run on 3 categories for rapid CI execution
    run_result = evaluation_engine.run_suite(
        name="CI Validation Suite",
        categories=["delivery_issues", "refunds", "cancellations"],
        max_cases=3
    )
    assert run_result.status == "completed"
    assert run_result.total_cases == 3
    assert run_result.pass_rate >= 60.0

    metrics = run_result.metrics
    assert 0.0 <= metrics.intent_accuracy <= 100.0
    assert 0.0 <= metrics.policy_accuracy <= 100.0
    assert 0.0 <= metrics.decision_accuracy <= 100.0
    assert 0.0 <= metrics.tool_execution_accuracy <= 100.0
    assert 0.0 <= metrics.verification_accuracy <= 100.0
    assert 0.0 <= metrics.escalation_accuracy <= 100.0
    assert 0.0 <= metrics.hallucination_rate <= 100.0
    assert metrics.avg_latency_ms > 0
    assert metrics.total_cost_usd > 0

    # Verify history retrieval
    runs = evaluation_engine.list_runs()
    assert len(runs) >= 1
    detail = evaluation_engine.get_run(run_result.run_id)
    assert detail is not None
    assert detail.run_id == run_result.run_id


# =========================================================================
# 3. TEST AGENT & TOOL PERFORMANCE & FAILURE ANALYSIS
# =========================================================================

def test_agent_and_tool_performance_metrics():
    db = SessionLocal()
    try:
        agent_metrics = observability_service.get_agent_performance(db)
        assert len(agent_metrics) >= 7
        for a in agent_metrics:
            assert a.total_runs > 0
            assert 0.0 <= a.success_rate <= 100.0
            assert a.avg_latency_ms > 0

        tool_metrics = observability_service.get_tool_performance(db)
        assert len(tool_metrics) >= 5
        for t in tool_metrics:
            assert t.total_calls > 0
            assert t.success_rate >= 0.0

        failures = observability_service.get_failure_analysis(db)
        assert failures.total_cases_analyzed >= 0
        assert isinstance(failures.common_errors, list)
    finally:
        db.close()


# =========================================================================
# 4. TEST AUDIT LOG EXPLORER (5W1H TRACEABILITY)
# =========================================================================

def test_audit_log_explorer_5w1h_traceability():
    db = SessionLocal()
    try:
        now = get_utc_now()
        case_id = f"CASE-AUDIT-{uuid.uuid4().hex[:6]}"
        
        # Log a sensitive action audit record
        audit_entry = AuditLog(
            case_id=case_id,
            entity_type="Refund",
            entity_id="REF-9090",
            action="REFUND_PROCESSED",
            actor_type="agent",
            actor_id="ActionGateway",
            details_json='{"amount": 89.99, "reason": "Damaged goods in transit", "result": "PROCESSED_SUCCESS", "justification": "Policy Clause 4.2 applied"}',
            created_at=now
        )
        db.add(audit_entry)
        db.commit()

        # Query via search filter
        logs = observability_service.search_audit_logs(
            db,
            AuditLogFilter(case_id=case_id, action="REFUND_PROCESSED")
        )
        assert len(logs) == 1
        log = logs[0]
        
        # 5W1H Verification
        assert "ActionGateway" in log["who"]  # WHO
        assert log["what"] == "REFUND_PROCESSED"  # WHAT
        assert log["when"] is not None  # WHEN
        assert "Policy Clause 4.2" in log["why"] or "Damaged goods" in log["why"]  # WHY
        assert log["result"] == "PROCESSED_SUCCESS"  # RESULT
    finally:
        db.close()


# =========================================================================
# 5. TEST FASTAPI API ENDPOINTS (OBSERVABILITY, EVALUATIONS, AUDIT)
# =========================================================================

def test_api_observability_endpoints(client):
    # Create test case for trace lookup
    db = SessionLocal()
    try:
        case = SupportCase(
            id=f"CASE-API-OBS-{uuid.uuid4().hex[:6]}",
            customer_id="CUST1002",
            channel="web_chat",
            subject="API Observability Test Case",
            priority="medium",
            status=CaseStatus.INVESTIGATING.value,
            created_at=get_utc_now()
        )
        db.add(case)
        db.commit()
        test_case_id = case.id
    finally:
        db.close()

    # Trace endpoint
    res_trace = client.get(f"/api/observability/cases/{test_case_id}/trace")
    assert res_trace.status_code == 200
    trace_json = res_trace.json()
    assert trace_json["case_id"] == test_case_id
    assert "tree_nodes" in trace_json

    # Agent performance endpoint
    res_agents = client.get("/api/observability/agents")
    assert res_agents.status_code == 200
    assert len(res_agents.json()) >= 7

    # Tool performance endpoint
    res_tools = client.get("/api/observability/tools")
    assert res_tools.status_code == 200
    assert len(res_tools.json()) >= 5

    # Failure analysis endpoint
    res_fail = client.get("/api/observability/failures")
    assert res_fail.status_code == 200
    assert "total_cases_analyzed" in res_fail.json()


def test_api_evaluation_endpoints(client):
    # Benchmark list
    b_res = client.get("/api/evaluations/benchmarks")
    assert b_res.status_code == 200
    assert len(b_res.json()) >= 8

    # Trigger evaluation run
    run_payload = {
        "name": "API Triggered Evaluation",
        "categories": ["delivery_issues"],
        "max_cases": 1
    }
    run_res = client.post("/api/evaluations/run", json=run_payload)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "completed"
    assert "metrics" in run_data
    run_id = run_data["run_id"]

    # Runs list
    runs_res = client.get("/api/evaluations/runs")
    assert runs_res.status_code == 200
    assert len(runs_res.json()) >= 1

    # Run detail
    detail_res = client.get(f"/api/evaluations/runs/{run_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["run_id"] == run_id


def test_api_audit_logs_endpoint(client):
    res = client.get("/api/audit/logs?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "total_returned" in data
