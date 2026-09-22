from typing import List, Dict, Optional
from ..schemas.evaluation import EvaluationBenchmarkCase, EvaluationCategory


BENCHMARK_DATASET: List[EvaluationBenchmarkCase] = [
    # 1. Delivery Issues
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-DELIV-001",
        category=EvaluationCategory.DELIVERY_ISSUES,
        title="Delayed Package Tracking Inquiry",
        user_goal="Where is my order ORD10002? It was supposed to arrive yesterday and tracking shows a delay.",
        customer_id="CUST1002",
        expected_intent="order_status",
        expected_decision="resolve",
        expected_policy="Delivery Delay Policy",
        expected_escalation=False,
        expected_tools=["order_lookup"],
        description="Verify tracking lookup and delivery delay evaluation."
    ),
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-DELIV-002",
        category=EvaluationCategory.DELIVERY_ISSUES,
        title="Severely Delayed Shipment Autonomous Reshipment",
        user_goal="My order ORD10002 has been stuck in transit for over 6 days without movement. Can you reship it?",
        customer_id="CUST1002",
        expected_intent="shipping_delay",
        expected_decision="reship",
        expected_policy="Lost in Transit Policy",
        expected_escalation=False,
        expected_tools=["order_lookup"],
        description="Verify lost package identification and autonomous reshipment trigger."
    ),

    # 2. Refunds
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-REFUND-001",
        category=EvaluationCategory.REFUNDS,
        title="Damaged Item Autonomous Refund",
        user_goal="My order ORD10002 is delayed and damaged. If I am eligible under policy, refund it.",
        customer_id="CUST1002",
        expected_intent="refund",
        expected_decision="refund",
        expected_policy="Refund",
        expected_escalation=False,
        expected_tools=["order_lookup"],
        description="Check damaged goods verification and autonomous refund execution."
    ),
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-REFUND-002",
        category=EvaluationCategory.REFUNDS,
        title="Expired Window Refund Request Rejection/Human Review",
        user_goal="I want a full refund for an item purchased 8 months ago because I no longer need it.",
        customer_id="CUST1001",
        expected_intent="refund",
        expected_decision="escalation",
        expected_policy="Refund",
        expected_escalation=True,
        expected_tools=[],
        description="Verify expired return window policy enforcement and routing."
    ),

    # 3. Cancellations
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-CANCEL-001",
        category=EvaluationCategory.CANCELLATIONS,
        title="Processing Order Immediate Cancellation",
        user_goal="I accidentally ordered two units of ORD10003. It says Processing. Please cancel order ORD10003 immediately.",
        customer_id="CUST1002",
        expected_intent="cancel",
        expected_decision="cancellation",
        expected_policy="Cancellation",
        expected_escalation=False,
        expected_tools=["order_lookup"],
        description="Ensure processing order status allows instantaneous automated cancellation."
    ),
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-CANCEL-002",
        category=EvaluationCategory.CANCELLATIONS,
        title="Shipped Order Cancellation Redirection to Return",
        user_goal="Please cancel order ORD10001 right now. I don't want it anymore.",
        customer_id="CUST1001",
        expected_intent="cancel",
        expected_decision="resolve",
        expected_policy="Cancellation",
        expected_escalation=False,
        expected_tools=["order_lookup"],
        description="Verify policy check blocks cancellation for shipped goods and guides return upon arrival."
    ),

    # 4. Billing
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-BILLING-001",
        category=EvaluationCategory.BILLING,
        title="Duplicate Charge Dispute Investigation",
        user_goal="I was billed twice on my statement for my order ORD10001. Please investigate the double charge.",
        customer_id="CUST1001",
        expected_intent="billing",
        expected_decision="resolve",
        expected_policy="Billing",
        expected_escalation=False,
        expected_tools=["order_lookup"],
        description="Validate billing dispute analysis and ledger verification."
    ),

    # 5. Policy Questions
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-POLICY-001",
        category=EvaluationCategory.POLICY_QUESTIONS,
        title="Return Policy Window and Warranty Terms",
        user_goal="What is NovaCart's return policy window and warranty coverage terms?",
        customer_id="CUST1001",
        expected_intent="policy",
        expected_decision="resolve",
        expected_policy="Return",
        expected_escalation=False,
        expected_tools=[],
        description="Verify policy store RAG retrieval and citation grounding without hallucination."
    ),

    # 6. Escalation
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-ESC-001",
        category=EvaluationCategory.ESCALATION,
        title="Hostile Customer Legal Threat Handoff",
        user_goal="This is unacceptable! Your service is terrible and I demand to speak with a human supervisor immediately!",
        customer_id="CUST1001",
        expected_intent="escalation",
        expected_decision="escalation",
        expected_policy=None,
        expected_escalation=True,
        expected_tools=[],
        description="Verify negative sentiment immediately triggers human escalation."
    ),

    # 7. Tool Failures
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-TOOLFAIL-001",
        category=EvaluationCategory.TOOL_FAILURES,
        title="Graceful Handling of Non-Existent Order Lookup",
        user_goal="Check status for order number ORD-NONEXISTENT-999.",
        customer_id="CUST1001",
        expected_intent="order",
        expected_decision="resolve",
        expected_policy=None,
        expected_escalation=False,
        expected_tools=[],
        description="Verify tool failure handling prompts for correct order credentials gracefully."
    ),

    # 8. Ambiguous Requests
    EvaluationBenchmarkCase(
        benchmark_id="BENCH-AMBIG-001",
        category=EvaluationCategory.AMBIGUOUS_REQUESTS,
        title="Vague Problem Statement Probing",
        user_goal="Something went wrong with my account. Can you help?",
        customer_id="CUST1002",
        expected_intent="general",
        expected_decision="resolve",
        expected_policy=None,
        expected_escalation=False,
        expected_tools=[],
        description="Verify intake detects open inquiry and provides helpful assistance."
    ),
]


def get_benchmarks(category: Optional[str] = None) -> List[EvaluationBenchmarkCase]:
    """Retrieve benchmark cases with optional category filter."""
    if not category or category.lower() == "all":
        return list(BENCHMARK_DATASET)
    return [b for b in BENCHMARK_DATASET if b.category.value == category.lower()]
