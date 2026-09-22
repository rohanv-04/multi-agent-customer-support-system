import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def get_utc_now():
    """Return timezone-naive UTC timestamp for standard database persistence."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class Organization(Base):
    """Multi-tenant organization boundary for enterprise support operations."""
    __tablename__ = "organizations"

    id = Column(String(50), primary_key=True)  # e.g. ORG-NOVACART
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    plan_tier = Column(String(50), default="Enterprise")
    created_at = Column(DateTime, default=get_utc_now)

    users = relationship("User", back_populates="organization")
    customers = relationship("Customer", back_populates="organization")
    cases = relationship("SupportCase", back_populates="organization")


class User(Base):
    """Enterprise user account with role-based access control and tenant assignment."""
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)  # e.g. USR-ADMIN-01
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=False, default="ORG-NOVACART")
    email = Column(String(100), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="SUPPORT_AGENT")  # CUSTOMER, SUPPORT_AGENT, SUPERVISOR, MANAGER, ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    organization = relationship("Organization", back_populates="users")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    tier = Column(String(50), default="Standard")  # Standard, Silver, Gold, Platinum
    account_status = Column(String(50), default="Active")
    created_at = Column(DateTime, default=get_utc_now)

    organization = relationship("Organization", back_populates="customers")
    orders = relationship("Order", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")
    escalations = relationship("EscalationTicket", back_populates="customer")
    cases = relationship("SupportCase", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    status = Column(String(50), nullable=False)  # Processing, Shipped, Delivered, Delayed, Cancelled, Refunded
    items_json = Column(Text, nullable=False)  # JSON array of items
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    tracking_number = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)  # FedEx, UPS, NovaExpress
    order_date = Column(DateTime, nullable=False)
    expected_delivery = Column(DateTime, nullable=False)
    actual_delivery = Column(DateTime, nullable=True)
    delay_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    customer = relationship("Customer", back_populates="orders")
    refunds = relationship("Refund", back_populates="order")


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String(100), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    status = Column(String(50), default="active")
    title = Column(String(200), default="Customer Support Inquiry")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON with task_id, tool_calls, etc.
    created_at = Column(DateTime, default=get_utc_now)

    conversation = relationship("Conversation", back_populates="messages")


class SupportCase(Base):
    """SupportCase: The primary business entity in SupportOS AI."""
    __tablename__ = "cases"

    id = Column(String(50), primary_key=True)  # CASE-XXXX or UUID
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=False, default="ORG-NOVACART")
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    conversation_id = Column(String(100), nullable=True)
    channel = Column(String(50), default="web_chat")  # web_chat, email, api, portal
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    intent = Column(String(100), nullable=True)
    sentiment = Column(String(50), default="neutral")  # neutral, positive, negative, frustrated
    priority = Column(String(50), default="medium")  # low, medium, high, urgent
    status = Column(String(50), default="NEW")  # NEW, TRIAGING, INVESTIGATING, DECISION_PENDING, ACTION_PENDING, VERIFYING, RESOLVED, CLOSED, ESCALATED
    sla_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    resolved_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="cases")
    customer = relationship("Customer", back_populates="cases")
    messages = relationship("CaseMessage", back_populates="case", cascade="all, delete-orphan", order_by="CaseMessage.created_at")
    events = relationship("CaseEvent", back_populates="case", cascade="all, delete-orphan", order_by="CaseEvent.created_at")
    agent_runs = relationship("AgentRun", back_populates="case", cascade="all, delete-orphan", order_by="AgentRun.started_at")
    actions = relationship("AgentAction", back_populates="case", cascade="all, delete-orphan")
    escalations = relationship("EscalationTicket", back_populates="case")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan", order_by="AuditLog.created_at")


class CaseMessage(Base):
    """CaseMessage: Multi-channel communication record linked to a Support Case."""
    __tablename__ = "case_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    direction = Column(String(20), default="inbound")  # inbound, outbound
    channel = Column(String(50), default="web_chat")  # web_chat, email, api, portal
    sender_type = Column(String(50), default="customer")  # customer, agent, supervisor, system
    sender_id = Column(String(100), nullable=True)
    body = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    case = relationship("SupportCase", back_populates="messages")


class CaseEvent(Base):
    """CaseEvent: Lifecycle and state transition telemetry for a Support Case."""
    __tablename__ = "case_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # case_created, status_changed, agent_started, agent_completed, tool_executed, escalation, approval, resolution, failure
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    actor = Column(String(100), default="System")
    summary = Column(Text, nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    case = relationship("SupportCase", back_populates="events")


class AgentRun(Base):
    """AgentRun: Execution record for an individual specialist agent during case resolution."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    task_id = Column(String(100), nullable=True)
    agent_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=get_utc_now)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    output_summary = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    error_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    case = relationship("SupportCase", back_populates="agent_runs")


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(String(100), primary_key=True)
    conversation_id = Column(String(100), nullable=True)
    customer_id = Column(String(50), nullable=True)
    user_goal = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    confidence = Column(Float, default=0.0)
    status = Column(String(50), default="in_progress")  # in_progress, completed, escalated, failed
    replan_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)
    completed_at = Column(DateTime, nullable=True)

    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), ForeignKey("tasks.task_id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    description = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    agent_assigned = Column(String(100), nullable=True)
    result_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    task = relationship("Task", back_populates="steps")


class AgentAction(Base):
    """AgentAction: Structured business action executed on behalf of a case/task."""
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=True)
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=True)
    agent_name = Column(String(100), nullable=False)
    action_type = Column(String(100), nullable=False)
    requested_by = Column(String(100), nullable=True)
    status = Column(String(50), default="completed")  # pending, completed, failed, approved
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    input_metadata = Column(Text, nullable=True)
    result_metadata = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

    case = relationship("SupportCase", back_populates="actions")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    input_params_json = Column(Text, nullable=False)
    output_result_json = Column(Text, nullable=False)
    status = Column(String(50), default="success")  # success, failure
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    customer_id = Column(String(50), nullable=False)
    refund_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="processed")  # processed, pending, rejected
    reason = Column(String(255), nullable=False)
    refund_method = Column(String(100), default="Original Payment Method")
    processed_at = Column(DateTime, default=get_utc_now)

    order = relationship("Order", back_populates="refunds")


class EscalationTicket(Base):
    """EscalationTicket / Escalation: Human agent triage and handoff dossier."""
    __tablename__ = "escalations"

    ticket_id = Column(String(50), primary_key=True)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    task_id = Column(String(100), nullable=True)
    summary = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    actions_attempted_json = Column(Text, nullable=True)
    tools_used_json = Column(Text, nullable=True)
    results_json = Column(Text, nullable=True)
    status = Column(String(50), default="open")  # open, in_progress, resolved
    priority = Column(String(50), default="high")  # low, medium, high, urgent
    recommended_action = Column(Text, nullable=True)
    assigned_to = Column(String(100), default="Unassigned")
    created_at = Column(DateTime, default=get_utc_now)
    resolved_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="escalations")
    case = relationship("SupportCase", back_populates="escalations")


class AuditLog(Base):
    """AuditLog: Immutable enterprise ledger recording sensitive operations and compliance events."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=True)
    entity_type = Column(String(50), nullable=False)  # SupportCase, Refund, EscalationTicket, AgentAction, System, User, Policy
    entity_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)  # CASE_CREATED, STATUS_CHANGED, REFUND_PROCESSED, ESCALATED, LOGIN, USER_CREATED, etc.
    actor_type = Column(String(50), default="system")  # system, agent, supervisor, user, admin
    actor_id = Column(String(100), default="system")
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    case = relationship("SupportCase", back_populates="audit_logs")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    doc_id = Column(String(100), primary_key=True)
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    filename = Column(String(200), nullable=False)
    chunk_count = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    last_indexed_at = Column(DateTime, default=get_utc_now)


class CustomerMemory(Base):
    __tablename__ = "customer_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), nullable=False)
    memory_type = Column(String(50), default="preference")  # preference, order_issue, note, fact
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)


# ==============================================================================
# SUPPORTOS AI V2 DIFFERENTIATION MODELS
# ==============================================================================

class CustomerFrictionRecord(Base):
    """Historical snapshot and profile of customer friction."""
    __tablename__ = "customer_friction_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    score = Column(Float, nullable=False)  # 0.0 to 100.0
    level = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    contributing_factors_json = Column(Text, nullable=False)
    recent_trend = Column(String(50), default="stable")  # improving, stable, escalating
    affected_cases_json = Column(Text, nullable=True)
    calculated_at = Column(DateTime, default=get_utc_now)


class CaseDNARecord(Base):
    """Case DNA: Multidimensional fingerprint of a SupportCase."""
    __tablename__ = "case_dna_records"

    case_id = Column(String(50), ForeignKey("cases.id"), primary_key=True)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    intent = Column(String(100), nullable=False)
    sub_intent = Column(String(100), nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    urgency = Column(String(20), default="medium")
    customer_value = Column(String(50), default="Standard")
    operational_risk = Column(String(20), default="low")
    policy_complexity = Column(String(20), default="standard")  # simple, standard, complex, ambiguous
    sla_risk = Column(String(20), default="low")
    fraud_risk_score = Column(Float, default=0.0)
    channel = Column(String(50), default="web_chat")
    affected_business_area = Column(String(100), default="logistics")
    required_capabilities_json = Column(Text, nullable=False)
    fingerprint_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class RootCause(Base):
    """Root Cause Intelligence: Cluster of systemic operational issues."""
    __tablename__ = "root_causes"

    id = Column(String(50), primary_key=True)  # RC-XXXX
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    category = Column(String(100), nullable=False)  # warehouse, carrier, product, payment, policy, technical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)
    status = Column(String(50), default="DETECTED_PATTERN")  # DETECTED_PATTERN, CONFIRMED_ROOT_CAUSE, MITIGATED, RESOLVED
    first_detected = Column(DateTime, default=get_utc_now)
    last_detected = Column(DateTime, default=get_utc_now)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    evidence_items = relationship("RootCauseEvidence", back_populates="root_cause", cascade="all, delete-orphan")
    case_links = relationship("RootCauseCaseLink", back_populates="root_cause", cascade="all, delete-orphan")


class RootCauseEvidence(Base):
    __tablename__ = "root_cause_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    root_cause_id = Column(String(50), ForeignKey("root_causes.id"), nullable=False)
    evidence_type = Column(String(50), nullable=False)  # telemetry, delay_cluster, payment_failure, policy_dispute
    description = Column(Text, nullable=False)
    raw_data_json = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=get_utc_now)

    root_cause = relationship("RootCause", back_populates="evidence_items")


class RootCauseCaseLink(Base):
    __tablename__ = "root_cause_case_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    root_cause_id = Column(String(50), ForeignKey("root_causes.id"), nullable=False)
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    customer_id = Column(String(50), nullable=False)
    linked_at = Column(DateTime, default=get_utc_now)

    root_cause = relationship("RootCause", back_populates="case_links")


class KnowledgeGap(Base):
    """Knowledge Gap: Missing, ambiguous, or contradictory policy clusters."""
    __tablename__ = "knowledge_gaps"

    id = Column(String(50), primary_key=True)  # KG-XXXX
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    topic = Column(String(200), nullable=False)
    occurrences = Column(Integer, default=1)
    affected_cases_json = Column(Text, nullable=False)
    evidence_json = Column(Text, nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    status = Column(String(50), default="OPEN")  # OPEN, IN_REVIEW, RESOLVED
    suggested_documentation_topic = Column(String(255), nullable=True)
    detected_at = Column(DateTime, default=get_utc_now)
    resolved_at = Column(DateTime, nullable=True)


class SimulationScenario(Base):
    """AI Simulation Lab Scenario definition."""
    __tablename__ = "simulation_scenarios"

    id = Column(String(50), primary_key=True)  # SIM-SCEN-XXXX
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    customer_profile_json = Column(Text, nullable=False)
    issue_description = Column(Text, nullable=False)
    system_conditions_json = Column(Text, nullable=False)  # e.g. {"carrier_api_down": true, "refund_limit": 300}
    created_at = Column(DateTime, default=get_utc_now)


class SimulationRun(Base):
    """Execution record for a sandboxed AI Simulation run."""
    __tablename__ = "simulation_runs"

    id = Column(String(50), primary_key=True)  # SIM-RUN-XXXX
    scenario_id = Column(String(50), ForeignKey("simulation_scenarios.id"), nullable=True)
    status = Column(String(50), default="running")  # running, completed, failed
    started_at = Column(DateTime, default=get_utc_now)
    completed_at = Column(DateTime, nullable=True)
    total_duration_ms = Column(Integer, default=0)
    result_summary_json = Column(Text, nullable=True)
    execution_trace_json = Column(Text, nullable=True)
    agent_outputs_json = Column(Text, nullable=True)
    simulated_tool_calls_json = Column(Text, nullable=True)
    case_dna_json = Column(Text, nullable=True)
    friction_json = Column(Text, nullable=True)
    safety_verified = Column(Boolean, default=True)  # Guarantees zero real DB writes occurred


class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), ForeignKey("simulation_runs.id"), nullable=False)
    timestamp = Column(DateTime, default=get_utc_now)
    phase = Column(String(50), nullable=False)
    agent = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    details_json = Column(Text, nullable=True)


class AgentConflict(Base):
    """Structured record of specialist agent disagreements and arbitrated resolutions."""
    __tablename__ = "agent_conflicts"

    id = Column(String(50), primary_key=True)  # CONF-XXXX
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=True, default="ORG-NOVACART")
    agent_positions_json = Column(Text, nullable=False)  # Positions from Investigation, Policy, Risk, etc.
    conflicting_points_json = Column(Text, nullable=False)
    resolution_rationale = Column(Text, nullable=False)
    final_action_chosen = Column(String(100), nullable=False)
    resolved_by = Column(String(100), default="Decision Agent")
    created_at = Column(DateTime, default=get_utc_now)


class WorkflowHealingRecord(Base):
    """Telemetry for self-healing workflow recovery and retry attempts."""
    __tablename__ = "workflow_healing_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=True)
    task_id = Column(String(100), nullable=True)
    failure_type = Column(String(100), nullable=False)  # timeout, tool_failure, api_outage, policy_ambiguity
    error_message = Column(Text, nullable=False)
    recovery_attempted = Column(String(100), nullable=False)  # replan, tool_retry, state_reset, escalate
    retry_count = Column(Integer, default=1)
    recovery_successful = Column(Boolean, default=False)
    final_disposition = Column(String(100), default="resolved")  # recovered, escalated, terminated
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)


class OperationalInsight(Base):
    """OperationalInsight: Grounded systemic observations on throughput, bottlenecks, and automation."""
    __tablename__ = "operational_insights"

    id = Column(String(50), primary_key=True)
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=False, default="ORG-NOVACART")
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    observation = Column(Text, nullable=False)
    severity = Column(String(20), default="info")
    metrics_json = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=get_utc_now)


class HumanSupportAssignment(Base):
    """HumanSupportAssignment: Record of human support representative assigned to a customer/case."""
    __tablename__ = "human_support_assignments"

    id = Column(String(50), primary_key=True)  # HSA-XXXX or UUID
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    representative_id = Column(String(50), nullable=False)
    representative_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=False)
    assignment_method = Column(String(50), default="RANDOM")  # RANDOM, AVAILABILITY, ROUND_ROBIN
    assigned_at = Column(DateTime, default=get_utc_now)
    status = Column(String(50), default="ASSIGNED")  # ASSIGNED, CALL_AVAILABLE, CALL_INITIATED, COMPLETED
    organization_id = Column(String(50), ForeignKey("organizations.id"), nullable=False, default="ORG-NOVACART")
    notes = Column(Text, nullable=True)

    case = relationship("SupportCase")
    customer = relationship("Customer")
