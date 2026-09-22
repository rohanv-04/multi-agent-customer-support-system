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

    customers = relationship("Customer", back_populates="organization")
    cases = relationship("SupportCase", back_populates="organization")


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
    case_id = Column(String(50), ForeignKey("cases.id"), nullable=True)
    entity_type = Column(String(50), nullable=False)  # SupportCase, Refund, EscalationTicket, AgentAction, System
    entity_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)  # CASE_CREATED, STATUS_CHANGED, REFUND_PROCESSED, ESCALATED, etc.
    actor_type = Column(String(50), default="system")  # system, agent, supervisor, user
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
