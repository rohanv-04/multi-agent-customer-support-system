# SupportOS AI — Support Case Engine Documentation

SupportOS AI transforms traditional conversational AI into an **Autonomous Customer Support Operations Platform**. Rather than treating conversations as ephemeral chat sessions, SupportOS AI positions the **`SupportCase`** as the primary, authoritative business entity.

---

## 1. System Architecture

```
                    INBOUND SUPPORT CHANNELS
      [ Web Chat ]     [ Email ]     [ REST API ]     [ Portal ]
           │               │              │               │
           └───────────────┼──────────────┴───────────────┘
                           ▼
          ┌────────────────────────────────────────────────┐
          │               CASE SERVICE LAYER               │
          │    • Normalizes multi-channel requests         │
          │    • Incepts SupportCase (Status: NEW)         │
          │    • Computes dynamic SLA deadlines            │
          │    • Records Inbound CaseMessages & Events     │
          └───────────────────────┬────────────────────────┘
                                  │
                                  ▼
          ┌────────────────────────────────────────────────┐
          │     COGNITIVE ENGINE (LangGraph Multi-Agent)   │
          │                                                │
          │   [ Supervisor Agent ]   (Status: TRIAGING)    │
          │            │                                   │
          │            ▼                                   │
          │   [ Intent Agent ]       (Status: INVESTIGATING)
          │            │                                   │
          │            ▼                                   │
          │   [ Planning Agent ]                           │
          │            │                                   │
          │            ▼                                   │
          │   [ Policy RAG Agent ]                         │
          │            │                                   │
          │            ▼                                   │
          │   [ Resolution Agent ]   (Status: ACTION_PENDING)
          │            │                                   │
          │            ▼                                   │
          │   [ Critic Agent ]       (Status: VERIFYING)   │
          └───────────┬──────────────────────┬─────────────┘
                      │                      │
       Valid (Confidence >= 0.75)   Escalate / Critical Low
                      │                      │
                      ▼                      ▼
             [ Status: RESOLVED ]   [ Status: ESCALATED ]
             • Final Outbound Msg   • Human Desk Ticket Dossier
             • Audit Ledger Logged  • Action Audit Ledger Logged
```

---

## 2. Database Models Explanation

All models are managed via SQLAlchemy ORM with automatic incremental migrations:

| Entity | Table Name | Purpose | Key Attributes |
|---|---|---|---|
| **`Organization`** | `organizations` | Multi-tenant boundary | `id`, `name`, `slug`, `plan_tier`, `created_at` |
| **`Customer`** | `customers` | Customer profile & tier | `customer_id`, `organization_id`, `name`, `email`, `tier`, `account_status` |
| **`SupportCase`** | `cases` | **The central business object** | `id`, `organization_id`, `customer_id`, `channel`, `subject`, `description`, `intent`, `sentiment`, `priority`, `status`, `sla_deadline`, `resolved_at` |
| **`CaseMessage`** | `case_messages` | Inbound & outbound communications | `case_id`, `direction`, `channel`, `sender_type`, `sender_id`, `body`, `metadata_json` |
| **`CaseEvent`** | `case_events` | Granular lifecycle & operational events | `case_id`, `event_type`, `from_status`, `to_status`, `actor`, `summary`, `details_json` |
| **`AgentRun`** | `agent_runs` | Individual specialist agent execution runs | `case_id`, `task_id`, `agent_name`, `started_at`, `ended_at`, `status`, `output_summary`, `confidence`, `error_info` |
| **`AgentAction`** | `agent_actions` | Business tool invocations and actions | `case_id`, `task_id`, `agent_name`, `action_type`, `requested_by`, `status`, `input_summary`, `output_summary`, `duration_ms` |
| **`EscalationTicket`** | `escalations` | Human triage desk handoff dossiers | `ticket_id`, `case_id`, `customer_id`, `reason`, `actions_attempted_json`, `priority`, `status` |
| **`AuditLog`** | `audit_logs` | Immutable enterprise compliance ledger | `case_id`, `entity_type`, `entity_id`, `action`, `actor_type`, `actor_id`, `details_json` |

---

## 3. Case Lifecycle State Machine

The case engine strictly enforces valid lifecycle state transitions. Any illegal transition raises an `InvalidStateTransitionError` (HTTP 400).

```
                      ┌─────────┐
                      │   NEW   │
                      └────┬────┘
                           │
                           ▼
                     ┌───────────┐
                     │ TRIAGING  │◄───────────────────┐
                     └─────┬─────┘                    │
                           │                          │
                           ▼                          │
                   ┌───────────────┐                  │
                   │ INVESTIGATING │                  │
                   └───────┬───────┘                  │
                           │                          │
             ┌─────────────┴─────────────┐            │
             ▼                           ▼            │
    ┌──────────────────┐       ┌────────────────┐     │
    │ DECISION_PENDING │       │ ACTION_PENDING │     │
    └────────┬─────────┘       └────────┬───────┘     │
             │                          │             │
             └─────────────┬────────────┘             │
                           │                          │
                           ▼                          │
                     ┌───────────┐                    │
                     │ VERIFYING │                    │
                     └─────┬─────┘                    │
                           │                          │
             ┌─────────────┴─────────────┐            │
             ▼                           ▼            │
       ┌───────────┐               ┌───────────┐      │
       │ RESOLVED  │               │ ESCALATED │──────┘ (Triage)
       └─────┬─────┘               └─────┬─────┘
             │                           │
             ▼                           ▼
       ┌───────────┐               ┌───────────┐
       │  CLOSED   │──────────────►│ TRIAGING  │ (Re-opened)
       └───────────┘               └───────────┘
```

### Transition Matrix
* **`NEW`** $\rightarrow$ `TRIAGING`, `ESCALATED`, `CLOSED`
* **`TRIAGING`** $\rightarrow$ `INVESTIGATING`, `ESCALATED`, `CLOSED`
* **`INVESTIGATING`** $\rightarrow$ `DECISION_PENDING`, `ACTION_PENDING`, `ESCALATED`, `CLOSED`
* **`DECISION_PENDING`** $\rightarrow$ `ACTION_PENDING`, `VERIFYING`, `RESOLVED`, `ESCALATED`, `CLOSED`
* **`ACTION_PENDING`** $\rightarrow$ `VERIFYING`, `RESOLVED`, `ESCALATED`, `CLOSED`
* **`VERIFYING`** $\rightarrow$ `RESOLVED`, `INVESTIGATING` (re-plan), `ESCALATED`, `CLOSED`
* **`RESOLVED`** $\rightarrow$ `CLOSED`, `TRIAGING` (re-opened)
* **`ESCALATED`** $\rightarrow$ `TRIAGING`, `INVESTIGATING`, `RESOLVED`, `CLOSED`
* **`CLOSED`** $\rightarrow$ `TRIAGING` (re-opened by customer/agent)

---

## 4. SLA Calculation Engine

SupportOS AI dynamically assigns SLA target deadlines at inception based on case priority:

| Priority | Target Response / Resolution SLA | Target Countdown |
|---|---|---|
| **`urgent`** | Critical Customer Issue (P1) | 1 hour |
| **`high`** | High Severity / Delayed Order (P2) | 4 hours |
| **`medium`** | Standard Inquiry / Return Request (P3) | 24 hours |
| **`low`** | General Policy / Informational (P4) | 48 hours |

The Case Detail API computes real-time `sla_minutes_remaining` and an `is_sla_breached` flag.

---

## 5. REST API Documentation

### Base URL: `/api/cases`

#### 1. `POST /api/cases`
Creates a new support case, sets initial status to `NEW`, calculates SLA, registers `case_created` event, and stores optional initial message.

* **Request Body**:
  ```json
  {
    "customer_id": "CUST1002",
    "subject": "Delayed shipment NV-992014",
    "description": "Package is 4 days overdue.",
    "channel": "email",
    "priority": "high",
    "initial_message": "Where is my package?"
  }
  ```
* **Response**: `201 Created` with `CaseResponse`.

#### 2. `GET /api/cases`
List support cases with multi-attribute filtering and pagination.

* **Query Parameters**:
  * `status`: e.g. `NEW`, `TRIAGING`, `RESOLVED`, `ESCALATED`
  * `priority`: e.g. `low`, `medium`, `high`, `urgent`
  * `customer_id`: e.g. `CUST1002`
  * `channel`: e.g. `web_chat`, `email`, `api`, `portal`
  * `search`: Keyword search in subject, description, or intent
  * `limit`: Page size (default 50)
  * `offset`: Pagination offset

#### 3. `GET /api/cases/{case_id}`
Returns rich case details including customer profile overview, message and event counts, and real-time SLA countdown.

* **Response**:
  ```json
  {
    "id": "CASE-10007",
    "organization_id": "ORG-NOVACART",
    "customer_id": "CUST1002",
    "customer_name": "Elena Rostova",
    "customer_tier": "Platinum",
    "channel": "web_chat",
    "subject": "My order ORD10002 is delayed. If I'm eligible, refund it.",
    "priority": "high",
    "status": "RESOLVED",
    "is_sla_breached": false,
    "sla_minutes_remaining": 1418.2,
    "message_count": 2,
    "event_count": 8,
    "agent_run_count": 5,
    "action_count": 3
  }
  ```

#### 4. `PATCH /api/cases/{case_id}`
Updates case priority, subject, description, or triggers an auditable state transition.

* **Request Body**:
  ```json
  {
    "status": "TRIAGING",
    "priority": "urgent",
    "reason": "Customer expressed high frustration."
  }
  ```

#### 5. `GET /api/cases/{case_id}/messages`
Retrieves chronological message thread (inbound customer requests and outbound agent responses).

#### 6. `POST /api/cases/{case_id}/messages`
Appends a message to the case thread from an agent, supervisor, or inbound channel.

#### 7. `GET /api/cases/{case_id}/events`
Retrieves granular audit trail of all lifecycle events and tool triggers.

#### 8. `GET /api/cases/{case_id}/timeline`
Returns an aggregated chronological activity feed combining messages, lifecycle state transitions, specialist agent runs, tool actions, and human escalations.
