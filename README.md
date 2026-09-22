# SupportOS AI — Autonomous Customer Support Operations Platform

SupportOS AI is an enterprise-grade autonomous customer support operations platform designed for **NovaCart**. Powered by a case-centric architecture where **Support Case** is the central operational unit, seamlessly integrating multi-channel ingestion, Customer 360 context, dynamic LangGraph multi-agent cognitive loops, controlled business action gateways, and immutable audit ledgers.

> 📘 **Full Architecture & API Guide**: See [docs/case_engine.md](file:///c:/Users/kavin/OneDrive/Desktop/Multi-Agent%20Customer%20Support%20System/multi-agent-customer-support-system/docs/case_engine.md)

---

## Key Highlights

- **Support Case-Centric Paradigm**: Support requests from web chat, email, or APIs are normalized into first-class `SupportCase` entities with strict lifecycle state machines (`NEW` → `TRIAGING` → `INVESTIGATING` → `DECISION_PENDING` → `ACTION_PENDING` → `VERIFYING` → `RESOLVED` / `ESCALATED`).
- **Dynamic SLA Management**: Real-time SLA target tracking (P1-P4 countdowns) with automatic breach detection and priority routing.
- **Unified Chronological Activity Feeds**: Unified case timeline aggregating messages, state transitions, agent execution runs, tool actions, and human escalations.
- **LangGraph Multi-Agent Orchestration**: Real dynamic state transitions between 7 specialist nodes: `Supervisor`, `Intent & Goal`, `Planning`, `Knowledge Retrieval (RAG)`, `Resolution (Tools)`, `Critic / Validator`, and `Human Escalation`.
- **Controlled Real Database Tools**: Safe transactional execution of live order tracking diagnostics, eligibility evaluation, and financial refunds written directly to SQLite (`novacart.db`).
- **Policy RAG Grounding**: Semantic retrieval engine over corporate policy documents (Refund, Return, Shipping, Cancellation, Warranty, Escalation) with citations and confidence metrics.
- **Cognitive Quality Gate & Replanning**: Critic Agent strictly audits tool outcomes and policy compliance; triggers up to 5 loop-guarded re-planning cycles or initiates human escalation with complete handoff dossiers.
- **Zero-Configuration Autonomous Mode**: Universal OpenAI-compatible client with a built-in deterministic reasoning fallback engine so the system runs 100% out-of-the-box without requiring paid API keys.
- **Premium Liquid Glass UI**: Dark charcoal aesthetic (`#08090C`) with reactive ambient glow, 3-column chat workspace, live step-by-step checklist, spatial agent routing graph, and human escalation triage desk.

---

## System Architecture

```
                                  USER REQUEST
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │         SUPERVISOR AGENT          │
                     │  (Orchestrator & State Evaluator) │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │        INTENT & GOAL AGENT        │
                     │  (Entity extraction, urgency,     │
                     │   intent classification)          │
                     └─────────────────┬─────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │          PLANNING AGENT           │
                     │  (Dynamic step decomposition,     │
                     │   dependency tracking)            │
                     └─────────────────┬─────────────────┘
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ▼                                           ▼
   ┌───────────────────────────┐               ┌───────────────────────────┐
   │ KNOWLEDGE RETRIEVAL (RAG) │               │    RESOLUTION / TOOLS     │
   │ Policies: Refund, Return, │               │ Order Status, Eligibility,│
   │ Shipping, Warranty        │               │ Customer Info, Refund Run │
   └─────────────┬─────────────┘               └─────────────┬─────────────┘
                 │                                           │
                 └─────────────────────┬─────────────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │      CRITIC / VALIDATOR AGENT     │
                     │ (Policy compliance, tool outcome  │
                     │  grounding, confidence scoring)   │
                     └─────────────────┬─────────────────┘
                                       │
                       Is Valid & Confident (>= 0.75)?
                       ├── YES ──────────────┐
                       ├── NO (Retry/Replan) ┼────────► [REPLAN LOOP (Max 5)]
                       └── NO (Critical/Low) ┼────────► [ESCALATION AGENT]
                                             │                   │
                                             ▼                   ▼
                                       FINAL RESPONSE     HUMAN TICKET DESK
                                     + MEMORY PERSISTED   + DETAILED HANDOFF
```

---

## 5 Demo Scenarios (One-Click in UI)

| Scenario | Input Prompt | Expected Multi-Agent Behavior |
|---|---|---|
| **Scenario 1: RAG Knowledge** | `"What is your refund policy?"` | `Intent` → `RAG Retrieval` → Grounds against section headers → `Critic` audits → Direct response with policy citations. |
| **Scenario 2: Multi-Step Reasoning** | `"Check order ORD10001 and tell me if I'm eligible for a refund."` | `Intent` → `Planner` → `Order Tool` → `Eligibility Tool` → Explains condition without premature refund. |
| **Scenario 3: Autonomous Refund (Primary)** | `"My order ORD10002 is delayed. If I'm eligible, refund it."` | `Intent` → `Planner` → `Order Tool` (`Delayed` >3 days) → `Eligibility Tool` (Approved) → `Refund Tool` (Executes transaction `$499.00`, updates order to `Refunded`) → `Critic` validates → Generates `REF-ORD10002-XXXX` receipt. |
| **Scenario 4: Re-Planning Loop** | `"Check order ORD99999 and refund it."` | `Order Tool` fails on missing order → `Critic` catches failure → `Supervisor` triggers Re-Planning Loop (Iteration 1/5) → Corrective step executed. |
| **Scenario 5: Human Escalation** | `"I want to speak to a human."` | `Intent` detects human request → `Escalation Agent` generates `#TICK-XXXX` with full AI handoff dossier (actions attempted, reason, recommended next steps) in Human Support Desk. |

---

## Quickstart & Installation

### Prerequisites
- Python 3.11+
- Node.js v18+ & npm

### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server (runs on http://localhost:8000)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Accessible at http://localhost:5173
```

### 3. Run Automated Tests
```bash
.\venv\Scripts\python -m pytest backend/tests/
```
All 11 unit & end-to-end tests verify tools, RAG search, database transactions, replanning recovery, and human ticket handoffs.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/          # 7 Specialist Agents + LLM client
│   │   ├── api/             # FastAPI REST & SSE Streaming Routes
│   │   ├── database/        # SQLAlchemy Models & SQLite Seeder
│   │   ├── graph/           # LangGraph StateGraph & Workflow DAG
│   │   ├── memory/          # Persistent Customer Memory Manager
│   │   ├── rag/             # Policy Vector Store & Retrieval Pipeline
│   │   ├── tools/           # Real NovaCart Executable Tools
│   │   └── main.py          # FastAPI Application Entrypoint
│   ├── tests/               # Pytest Unit & End-to-End Suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Glass Navbar, Sidebar, Execution Panel, Spatial Graph
│   │   ├── pages/           # 9 Dedicated Liquid Glass Views
│   │   ├── services/        # API Client & SSE Stream Consumer
│   │   ├── types/           # TypeScript Domain Interfaces
│   │   └── App.tsx
│   └── package.json
└── knowledge_base/          # Markdown Corporate Policies
```
