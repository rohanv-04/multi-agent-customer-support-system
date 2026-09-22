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

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    tier = Column(String(50), default="Standard")  # Standard, Silver, Gold, Platinum
    account_status = Column(String(50), default="Active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    orders = relationship("Order", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")
    escalations = relationship("EscalationTicket", back_populates="customer")


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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    refunds = relationship("Refund", back_populates="order")


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String(100), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    status = Column(String(50), default="active")
    title = Column(String(200), default="Customer Support Inquiry")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON with task_id, tool_calls, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="steps")


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False)
    agent_name = Column(String(100), nullable=False)
    action_type = Column(String(100), nullable=False)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="refunds")


class EscalationTicket(Base):
    __tablename__ = "escalations"

    ticket_id = Column(String(50), primary_key=True)
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="escalations")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    doc_id = Column(String(100), primary_key=True)
    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    filename = Column(String(200), nullable=False)
    chunk_count = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    last_indexed_at = Column(DateTime, default=datetime.datetime.utcnow)


class CustomerMemory(Base):
    __tablename__ = "customer_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), nullable=False)
    memory_type = Column(String(50), default="preference")  # preference, order_issue, note, fact
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
